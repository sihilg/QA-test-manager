from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from qa_test_manager.database import get_session
from qa_test_manager.main import app
from qa_test_manager.models import AuditEvent, Base, Project, ProjectMember, User, UserRole
from qa_test_manager.security import hash_password
from qa_test_manager.test_cases import reserve_case_number


@pytest.fixture
def case_context() -> Iterator[tuple[TestClient, sessionmaker[Session], int]]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    with testing_session() as database:
        admin = User(
            name="Admin",
            email="admin@example.com",
            password_hash=hash_password("admin-password-123"),
            role=UserRole.ADMIN,
        )
        project = Project(name="Portal")
        database.add_all([admin, project])
        database.commit()
        project_id = project.id

    def override_session() -> Iterator[Session]:
        with testing_session() as database:
            yield database

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        yield client, testing_session, project_id
    app.dependency_overrides.clear()


def login(client: TestClient, email = "admin@example.com", password = "admin-password-123") -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return str(response.json()["csrf_token"])


def case_payload(order: int = 1, title: str = "Login válido") -> dict[str, object]:
    return {
        "execution_order": order,
        "priority": "HIGH",
        "requirement": "RF-001",
        "test_type": "FUNCTIONAL_POSITIVE",
        "title": title,
        "test_data": "admin@example.com / senha fictícia",
        "description": "Validar entrada com credenciais válidas",
        "preconditions": "Admin ativo",
        "expected_result": "A sessão é iniciada",
        "final_result": "NOT_EXECUTED",
        "origin": "MANUAL",
        "steps": [
            {"position": 1, "action": "Abrir o login", "expected_result": "Formulário visível"},
            {"position": 2, "action": "Enviar credenciais", "expected_result": "Sessão iniciada"},
        ],
    }


def test_admin_can_create_list_filter_update_and_archive_case(
    case_context: tuple[TestClient, sessionmaker[Session], int],
) -> None:
    client, testing_session, project_id = case_context
    headers = {"X-CSRF-Token": login(client)}
    created = client.post(
        f"/projects/{project_id}/test-cases", json=case_payload(), headers=headers
    )
    assert created.status_code == 201
    test_case = created.json()
    assert test_case["case_number"] == "CT001"
    assert len(test_case["steps"]) == 2

    listed = client.get(f"/projects/{project_id}/test-cases?priority=HIGH")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["title"] == "Login válido"
    assert client.get(f"/projects/{project_id}/test-cases?priority=LOW").json()["total"] == 0

    update_payload = case_payload(title="Login válido atualizado")
    update_payload["final_result"] = "PASSED"
    update_payload["version"] = test_case["version"]
    updated = client.put(f"/test-cases/{test_case['id']}", json=update_payload, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["case_number"] == "CT001"
    assert updated.json()["final_result"] == "PASSED"

    archived = client.post(f"/test-cases/{test_case['id']}/archive", headers=headers)
    assert archived.status_code == 200
    assert client.get(f"/projects/{project_id}/test-cases").json()["total"] == 0

    with testing_session() as database:
        actions = list(
            database.scalars(
                select(AuditEvent.action)
                .where(AuditEvent.entity_type == "TestCase")
                .order_by(AuditEvent.id)
            )
        )
    assert actions == [
        "TEST_CASE_CREATED",
        "TEST_CASE_UPDATED",
        "TEST_RESULT_CHANGED",
        "TEST_CASE_ARCHIVED",
    ]


def test_validation_rejects_duplicate_steps_and_duplicate_order(
    case_context: tuple[TestClient, sessionmaker[Session], int],
) -> None:
    client, _, project_id = case_context
    headers = {"X-CSRF-Token": login(client)}
    assert client.post(
        f"/projects/{project_id}/test-cases", json=case_payload(), headers=headers
    ).status_code == 201

    duplicate_order = client.post(
        f"/projects/{project_id}/test-cases",
        json=case_payload(title="Outro caso"),
        headers=headers,
    )
    invalid_steps = case_payload(order=2)
    invalid_steps["steps"] = [
        {"position": 1, "action": "Primeiro"},
        {"position": 1, "action": "Duplicado"},
    ]

    assert duplicate_order.status_code == 409
    assert client.post(
        f"/projects/{project_id}/test-cases", json=invalid_steps, headers=headers
    ).status_code == 422


def test_dev_can_read_assigned_project_but_cannot_create_case(
    case_context: tuple[TestClient, sessionmaker[Session], int],
) -> None:
    client, testing_session, project_id = case_context
    with testing_session() as database:
        dev = User(
            name="Dev",
            email="dev@example.com",
            password_hash=hash_password("developer-password-123"),
            role=UserRole.DEV,
        )
        database.add(dev)
        database.flush()
        database.add(ProjectMember(project_id=project_id, user_id=dev.id))
        database.commit()
    headers = {"X-CSRF-Token": login(client, "dev@example.com", "developer-password-123")}

    assert client.get(f"/projects/{project_id}/test-cases").status_code == 200
    assert client.post(
        f"/projects/{project_id}/test-cases", json=case_payload(), headers=headers
    ).status_code == 403


def test_archived_project_rejects_new_case(
    case_context: tuple[TestClient, sessionmaker[Session], int],
) -> None:
    client, testing_session, project_id = case_context
    with testing_session() as database:
        project = database.get(Project, project_id)
        assert project is not None
        from qa_test_manager.models import utc_now

        project.archived_at = utc_now()
        database.commit()
    headers = {"X-CSRF-Token": login(client)}

    assert client.post(
        f"/projects/{project_id}/test-cases", json=case_payload(), headers=headers
    ).status_code == 409


def test_case_number_reservation_is_atomic(tmp_path: Path) -> None:
    database_path = tmp_path / "concurrency.db"
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}", connect_args={"timeout": 10}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as database:
        project = Project(name="Concorrência")
        database.add(project)
        database.commit()
        project_id = project.id

    def reserve() -> str:
        with factory() as database:
            number = reserve_case_number(database, project_id)
            database.commit()
            return number

    with ThreadPoolExecutor(max_workers=2) as executor:
        numbers = list(executor.map(lambda _: reserve(), range(2)))

    assert sorted(numbers) == ["CT001", "CT002"]
