from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from qa_test_manager.database import get_session
from qa_test_manager.main import app
from qa_test_manager.models import AuditEvent, Base, Project, ProjectMember, User, UserRole
from qa_test_manager.security import hash_password


@pytest.fixture
def project_context() -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    with testing_session() as database:
        database.add_all(
            [
                User(
                    name="Admin",
                    email="admin@example.com",
                    password_hash=hash_password("admin-password-123"),
                    role=UserRole.ADMIN,
                ),
                User(
                    name="Tester",
                    email="tester@example.com",
                    password_hash=hash_password("tester-password-123"),
                    role=UserRole.TESTER,
                ),
            ]
        )
        database.commit()

    def override_session() -> Iterator[Session]:
        with testing_session() as database:
            yield database

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        yield client, testing_session
    app.dependency_overrides.clear()


def login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return str(response.json()["csrf_token"])


def test_admin_can_create_list_update_and_archive_project(
    project_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session = project_context
    csrf = login(client, "admin@example.com", "admin-password-123")
    headers = {"X-CSRF-Token": csrf}

    created = client.post(
        "/projects", json={"name": "Portal", "description": "Aplicação web"}, headers=headers
    )
    assert created.status_code == 201
    project = created.json()
    assert project["version"] == 1

    listed = client.get("/projects")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["name"] == "Portal"

    updated = client.patch(
        f"/projects/{project['id']}",
        json={"name": "Portal QA", "description": "Revisto", "version": project["version"]},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2

    archived = client.post(f"/projects/{project['id']}/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True
    assert client.get("/projects").json()["total"] == 0

    with testing_session() as database:
        actions = list(database.scalars(select(AuditEvent.action).order_by(AuditEvent.id)))
    assert actions == ["PROJECT_CREATED", "PROJECT_UPDATED", "PROJECT_ARCHIVED"]


def test_duplicate_name_and_stale_version_return_conflict(
    project_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = project_context
    csrf = login(client, "admin@example.com", "admin-password-123")
    headers = {"X-CSRF-Token": csrf}
    created = client.post("/projects", json={"name": "Portal"}, headers=headers).json()

    duplicate = client.post("/projects", json={"name": "Portal"}, headers=headers)
    stale = client.patch(
        f"/projects/{created['id']}",
        json={"name": "Outro nome", "version": 99},
        headers=headers,
    )

    assert duplicate.status_code == 409
    assert stale.status_code == 409


def test_tester_only_lists_assigned_projects_and_cannot_mutate(
    project_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session = project_context
    with testing_session() as database:
        tester = database.scalar(select(User).where(User.email == "tester@example.com"))
        assert tester is not None
        assigned = Project(name="Atribuído")
        hidden = Project(name="Não atribuído")
        database.add_all([assigned, hidden])
        database.flush()
        database.add(ProjectMember(project_id=assigned.id, user_id=tester.id))
        database.commit()

    csrf = login(client, "tester@example.com", "tester-password-123")
    page = client.get("/projects")
    forbidden = client.post(
        "/projects",
        json={"name": "Sem permissão"},
        headers={"X-CSRF-Token": csrf},
    )

    assert [item["name"] for item in page.json()["items"]] == ["Atribuído"]
    assert forbidden.status_code == 403


def test_project_mutation_requires_csrf(
    project_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = project_context
    login(client, "admin@example.com", "admin-password-123")

    assert client.post("/projects", json={"name": "Portal"}).status_code == 403
