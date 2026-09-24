from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.exc import StaleDataError

from qa_test_manager.auth import AuthContext, ensure_roles, get_auth_context, require_csrf
from qa_test_manager.database import get_session
from qa_test_manager.models import (
    AuditEvent,
    Project,
    ProjectMember,
    TestCase,
    TestOrigin,
    TestPriority,
    TestResult,
    TestStep,
    TestType,
    UserRole,
    utc_now,
)

router = APIRouter(tags=["test-cases"])


class StepInput(BaseModel):
    position: int = Field(ge=1)
    action: str = Field(min_length=1, max_length=4000)
    expected_result: str | None = Field(default=None, max_length=4000)


class StepResponse(StepInput):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TestCaseInput(BaseModel):
    execution_order: int = Field(ge=1)
    priority: TestPriority
    executor_id: int | None = None
    execution_date: date | None = None
    requirement: str = Field(min_length=1, max_length=4000)
    browser: str | None = Field(default=None, max_length=120)
    test_type: TestType
    title: str = Field(min_length=2, max_length=240)
    test_data: str = Field(min_length=1, max_length=8000)
    description: str = Field(min_length=1, max_length=8000)
    preconditions: str = Field(min_length=1, max_length=8000)
    expected_result: str = Field(min_length=1, max_length=8000)
    final_result: TestResult = TestResult.NOT_EXECUTED
    origin: Literal[TestOrigin.MANUAL] = TestOrigin.MANUAL
    steps: list[StepInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_step_positions(self) -> "TestCaseInput":
        positions = [step.position for step in self.steps]
        if len(positions) != len(set(positions)):
            raise ValueError("As posições dos passos devem ser únicas.")
        return self


class TestCaseUpdate(TestCaseInput):
    version: int = Field(ge=1)


class TestCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    case_number: str
    execution_order: int
    priority: TestPriority
    executor_id: int | None
    execution_date: date | None
    requirement: str
    browser: str | None
    test_type: TestType
    title: str
    test_data: str
    description: str
    preconditions: str
    expected_result: str
    final_result: TestResult
    origin: TestOrigin
    is_archived: bool
    version: int
    steps: list[StepResponse]
    created_at: datetime
    updated_at: datetime


class TestCaseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_number: str
    title: str
    priority: TestPriority
    test_type: TestType
    final_result: TestResult
    version: int


class TestCasePage(BaseModel):
    items: list[TestCaseListItem]
    total: int
    offset: int
    limit: int


@router.get("/projects/{project_id}/test-cases", response_model=TestCasePage)
def list_test_cases(
    project_id: int,
    context: Annotated[AuthContext, Depends(get_auth_context)],
    database: Annotated[Session, Depends(get_session)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    result: TestResult | None = None,
    priority: TestPriority | None = None,
    test_type: TestType | None = None,
) -> TestCasePage:
    _accessible_project(database, context, project_id)
    statement = select(TestCase).where(
        TestCase.project_id == project_id, TestCase.archived_at.is_(None)
    )
    if result is not None:
        statement = statement.where(TestCase.final_result == result)
    if priority is not None:
        statement = statement.where(TestCase.priority == priority)
    if test_type is not None:
        statement = statement.where(TestCase.test_type == test_type)
    statement = statement.order_by(TestCase.execution_order, TestCase.id)
    total = database.scalar(select(func.count()).select_from(statement.subquery())) or 0
    cases = list(database.scalars(statement.offset(offset).limit(limit)))
    return TestCasePage(
        items=[TestCaseListItem.model_validate(case) for case in cases],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/projects/{project_id}/test-cases",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_test_case(
    project_id: int,
    payload: TestCaseInput,
    context: Annotated[AuthContext, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_session)],
) -> TestCaseResponse:
    ensure_roles(context.user, UserRole.ADMIN, UserRole.TESTER)
    project = _accessible_project(database, context, project_id)
    if project.is_archived:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Projetos arquivados não aceitam novos casos.",
        )
    case_number = reserve_case_number(database, project_id)
    test_case = TestCase(
        project_id=project_id,
        case_number=case_number,
        **payload.model_dump(exclude={"steps"}),
        steps=[TestStep(**step.model_dump()) for step in payload.steps],
    )
    database.add(test_case)
    try:
        database.flush()
        _audit(database, context, test_case, "TEST_CASE_CREATED")
        database.commit()
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A ordem de execução já está em uso neste projeto.",
        ) from error
    return _case_response(database, test_case.id)


def reserve_case_number(database: Session, project_id: int) -> str:
    sequence = database.scalar(
        update(Project)
        .where(Project.id == project_id, Project.archived_at.is_(None))
        .values(next_case_sequence=Project.next_case_sequence + 1)
        .returning(Project.next_case_sequence - 1)
    )
    if sequence is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Projeto indisponível.")
    return f"CT{sequence:03d}"


@router.get("/test-cases/{case_id}", response_model=TestCaseResponse)
def get_test_case(
    case_id: int,
    context: Annotated[AuthContext, Depends(get_auth_context)],
    database: Annotated[Session, Depends(get_session)],
) -> TestCaseResponse:
    test_case = _case_or_404(database, case_id)
    _accessible_project(database, context, test_case.project_id)
    return _case_response(database, case_id)


@router.put("/test-cases/{case_id}", response_model=TestCaseResponse)
def update_test_case(
    case_id: int,
    payload: TestCaseUpdate,
    context: Annotated[AuthContext, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_session)],
) -> TestCaseResponse:
    ensure_roles(context.user, UserRole.ADMIN, UserRole.TESTER)
    test_case = _case_or_404(database, case_id)
    _accessible_project(database, context, test_case.project_id)
    if test_case.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Casos arquivados permanecem somente para consulta.",
        )
    if test_case.version != payload.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O caso foi alterado por outra operação.",
        )
    old_result = test_case.final_result
    for field, value in payload.model_dump(exclude={"steps", "version"}).items():
        setattr(test_case, field, value)
    replacement_steps = [TestStep(**step.model_dump()) for step in payload.steps]
    try:
        test_case.steps.clear()
        database.flush()
        test_case.steps = replacement_steps
        _audit(database, context, test_case, "TEST_CASE_UPDATED")
        if old_result is not test_case.final_result:
            _audit(database, context, test_case, "TEST_RESULT_CHANGED")
        database.commit()
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A ordem de execução já está em uso neste projeto.",
        ) from error
    except StaleDataError as error:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O caso foi alterado por outra operação.",
        ) from error
    return _case_response(database, case_id)


@router.post("/test-cases/{case_id}/archive", response_model=TestCaseResponse)
def archive_test_case(
    case_id: int,
    context: Annotated[AuthContext, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_session)],
) -> TestCaseResponse:
    ensure_roles(context.user, UserRole.ADMIN, UserRole.TESTER)
    test_case = _case_or_404(database, case_id)
    _accessible_project(database, context, test_case.project_id)
    if test_case.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="O caso já está arquivado."
        )
    test_case.archived_at = utc_now()
    _audit(database, context, test_case, "TEST_CASE_ARCHIVED")
    database.commit()
    return _case_response(database, case_id)


def _accessible_project(database: Session, context: AuthContext, project_id: int) -> Project:
    project = database.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")
    if context.user.role is not UserRole.ADMIN:
        membership = database.get(ProjectMember, (project_id, context.user.id))
        if membership is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso proibido.")
    return project


def _case_or_404(database: Session, case_id: int) -> TestCase:
    test_case = database.get(TestCase, case_id)
    if test_case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso não encontrado.")
    return test_case


def _case_response(database: Session, case_id: int) -> TestCaseResponse:
    test_case = database.scalar(
        select(TestCase).options(selectinload(TestCase.steps)).where(TestCase.id == case_id)
    )
    if test_case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso não encontrado.")
    return TestCaseResponse.model_validate(test_case)


def _audit(database: Session, context: AuthContext, test_case: TestCase, action: str) -> None:
    database.add(
        AuditEvent(
            actor_user_id=context.user.id,
            project_id=test_case.project_id,
            action=action,
            entity_type="TestCase",
            entity_id=str(test_case.id),
            details={"case_number": test_case.case_number},
        )
    )
