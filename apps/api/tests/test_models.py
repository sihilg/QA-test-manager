from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from qa_test_manager.models import Base, Project
from qa_test_manager.models import TestCase as CaseModel
from qa_test_manager.models import TestOrigin as Origin
from qa_test_manager.models import TestPriority as Priority
from qa_test_manager.models import TestResult as Result
from qa_test_manager.models import TestStep as StepModel
from qa_test_manager.models import TestType as CaseType
from qa_test_manager.repositories import list_active_project_cases


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        yield database_session


def make_case(project: Project, number: str, order: int) -> CaseModel:
    return CaseModel(
        project=project,
        case_number=number,
        execution_order=order,
        priority=Priority.HIGH,
        requirement="RF-001",
        test_type=CaseType.FUNCTIONAL_POSITIVE,
        title=f"Caso {number}",
        test_data="Dados fictícios",
        description="Valida o comportamento esperado",
        preconditions="Projeto ativo",
        expected_result="Operação concluída",
        origin=Origin.MANUAL,
    )


def test_new_case_defaults_to_not_executed(session: Session) -> None:
    project = Project(name="Portal")
    test_case = make_case(project, "CT001", 1)
    session.add(test_case)
    session.commit()

    assert test_case.final_result is Result.NOT_EXECUTED
    assert test_case.version == 1


def test_case_number_is_unique_inside_project(session: Session) -> None:
    project = Project(name="Portal")
    session.add_all([make_case(project, "CT001", 1), make_case(project, "CT001", 2)])

    with pytest.raises(IntegrityError):
        session.commit()


def test_step_position_is_positive_and_unique_inside_case(session: Session) -> None:
    project = Project(name="Portal")
    test_case = make_case(project, "CT001", 1)
    test_case.steps = [
        StepModel(position=1, action="Abrir a página"),
        StepModel(position=1, action="Repetir posição"),
    ]
    session.add(test_case)

    with pytest.raises(IntegrityError):
        session.commit()


def test_step_position_must_be_positive(session: Session) -> None:
    project = Project(name="Portal")
    test_case = make_case(project, "CT001", 1)
    test_case.steps = [StepModel(position=0, action="Posição inválida")]
    session.add(test_case)

    with pytest.raises(IntegrityError):
        session.commit()


def test_project_listing_never_mixes_cases(session: Session) -> None:
    first = Project(name="Portal")
    second = Project(name="Aplicação móvel")
    first_case = make_case(first, "CT001", 1)
    second_case = make_case(second, "CT001", 1)
    session.add_all([first_case, second_case])
    session.commit()

    cases = list_active_project_cases(session, first.id)

    assert [case.id for case in cases] == [first_case.id]
    assert second_case.id not in {case.id for case in cases}


def test_archived_projects_and_cases_are_excluded(session: Session) -> None:
    active_project = Project(name="Ativo")
    archived_project = Project(name="Arquivado", archived_at=datetime.now(UTC))
    active_case = make_case(active_project, "CT001", 1)
    archived_case = make_case(active_project, "CT002", 2)
    archived_case.archived_at = datetime.now(UTC)
    hidden_case = make_case(archived_project, "CT001", 1)
    session.add_all([active_case, archived_case, hidden_case])
    session.commit()

    assert list_active_project_cases(session, active_project.id) == [active_case]
    assert list_active_project_cases(session, archived_project.id) == []
