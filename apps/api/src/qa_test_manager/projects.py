from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from qa_test_manager.auth import AuthContext, ensure_roles, get_auth_context, require_csrf
from qa_test_manager.database import get_session
from qa_test_manager.models import AuditEvent, Project, ProjectMember, UserRole

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=4000)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    version: int = Field(ge=1)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    is_archived: bool
    version: int
    created_at: datetime
    updated_at: datetime


class ProjectPage(BaseModel):
    items: list[ProjectResponse]
    total: int
    offset: int
    limit: int


@router.get("", response_model=ProjectPage)
def list_projects(
    context: Annotated[AuthContext, Depends(get_auth_context)],
    database: Annotated[Session, Depends(get_session)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    include_archived: bool = False,
) -> ProjectPage:
    statement = select(Project)
    if context.user.role is not UserRole.ADMIN:
        statement = statement.join(ProjectMember).where(ProjectMember.user_id == context.user.id)
    if not include_archived:
        statement = statement.where(Project.archived_at.is_(None))
    statement = statement.order_by(Project.name)
    total = database.scalar(select(func.count()).select_from(statement.subquery())) or 0
    projects = list(database.scalars(statement.offset(offset).limit(limit)))
    return ProjectPage(
        items=[ProjectResponse.model_validate(project) for project in projects],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    context: Annotated[AuthContext, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_session)],
) -> ProjectResponse:
    ensure_roles(context.user, UserRole.ADMIN)
    project = Project(name=payload.name.strip(), description=payload.description.strip())
    database.add(project)
    try:
        database.flush()
        _audit(database, context, project, "PROJECT_CREATED")
        database.commit()
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um projeto com este nome.",
        ) from error
    database.refresh(project)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    context: Annotated[AuthContext, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_session)],
) -> ProjectResponse:
    ensure_roles(context.user, UserRole.ADMIN)
    project = _project_or_404(database, project_id)
    if project.version != payload.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O projeto foi alterado por outra operação.",
        )
    if payload.name is not None:
        project.name = payload.name.strip()
    if payload.description is not None:
        project.description = payload.description.strip()
    try:
        _audit(database, context, project, "PROJECT_UPDATED")
        database.commit()
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um projeto com este nome.",
        ) from error
    except StaleDataError as error:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O projeto foi alterado por outra operação.",
        ) from error
    database.refresh(project)
    return ProjectResponse.model_validate(project)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
def archive_project(
    project_id: int,
    context: Annotated[AuthContext, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_session)],
) -> ProjectResponse:
    ensure_roles(context.user, UserRole.ADMIN)
    project = _project_or_404(database, project_id)
    if project.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="O projeto já está arquivado."
        )
    project.archived_at = datetime.now(UTC)
    _audit(database, context, project, "PROJECT_ARCHIVED")
    database.commit()
    database.refresh(project)
    return ProjectResponse.model_validate(project)


def _project_or_404(database: Session, project_id: int) -> Project:
    project = database.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado."
        )
    return project


def _audit(database: Session, context: AuthContext, project: Project, action: str) -> None:
    database.add(
        AuditEvent(
            actor_user_id=context.user.id,
            project_id=project.id,
            action=action,
            entity_type="Project",
            entity_id=str(project.id),
            details={"name": project.name},
        )
    )
