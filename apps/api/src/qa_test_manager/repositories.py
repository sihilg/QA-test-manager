from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from qa_test_manager.models import Project, TestCase


def active_project_cases_statement(project_id: int) -> Select[tuple[TestCase]]:
    return (
        select(TestCase)
        .join(Project)
        .where(
            TestCase.project_id == project_id,
            TestCase.archived_at.is_(None),
            Project.archived_at.is_(None),
        )
        .order_by(TestCase.execution_order)
    )


def list_active_project_cases(session: Session, project_id: int) -> list[TestCase]:
    return list(session.scalars(active_project_cases_statement(project_id)))
