from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from qa_test_manager.database import get_session
from qa_test_manager.main import app
from qa_test_manager.models import (
    AuditEvent,
    Base,
    Project,
    ProjectMember,
    TestCase,
    TestOrigin,
    User,
    UserRole,
)
from qa_test_manager.security import hash_password


@pytest.fixture
def eva_context() -> Iterator[tuple[TestClient, sessionmaker[Session], int]]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as database:
        admin = User(
            name="Admin",
            email="admin@example.com",
            password_hash=hash_password("admin-password-123"),
            role=UserRole.ADMIN,
        )
        tester = User(
            name="Tester",
            email="tester@example.com",
            password_hash=hash_password("tester-password-123"),
            role=UserRole.TESTER,
        )
        dev = User(
            name="Dev",
            email="dev@example.com",
            password_hash=hash_password("developer-password-123"),
            role=UserRole.DEV,
        )
        project = Project(name="Portal")
        database.add_all([admin, tester, dev, project])
        database.flush()
        database.add_all(
            [
                ProjectMember(project_id=project.id, user_id=tester.id),
                ProjectMember(project_id=project.id, user_id=dev.id),
            ]
        )
        database.commit()
        project_id = project.id

    def override() -> Iterator[Session]:
        with factory() as database:
            yield database

    app.dependency_overrides[get_session] = override
    with TestClient(app) as client:
        yield client, factory, project_id
    app.dependency_overrides.clear()


def login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return str(response.json()["csrf_token"])


def create_exchange(client: TestClient, project_id: int, csrf: str) -> dict[str, object]:
    response = client.post(
        f"/projects/{project_id}/eva/exchanges",
        json={"title": "Login", "content": "O utilizador deve conseguir entrar."},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201
    return response.json()


def response_package(exchange_id: str, title: str = "Login válido") -> dict[str, object]:
    def proposal(key: str, category: str, proposal_title: str) -> dict[str, object]:
        return {
            "proposal_key": key,
            "category": category,
            "title": proposal_title,
            "requirement": "RF-001",
            "priority": "MEDIUM",
            "test_type": "FUNCTIONAL_POSITIVE",
            "test_data": "Dados fictícios",
            "description": "Validar comportamento",
            "preconditions": "Utilizador ativo",
            "expected_result": "Resultado esperado",
            "steps": [{"position": 1, "action": "Executar", "expected_result": "Concluído"}],
            "assumptions": [],
        }

    return {
        "schema_version": "1.0",
        "exchange_id": exchange_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "proposals": [
            proposal("positivo", "POSITIVE", title),
            proposal("negativo", "NEGATIVE", "Login inválido"),
            proposal("limite", "BOUNDARY", "Limite de tentativas"),
        ],
        "warnings": [],
    }


def test_export_import_is_idempotent_and_audited(eva_context) -> None:
    client, factory, project_id = eva_context
    csrf = login(client, "admin@example.com", "admin-password-123")
    exchange = create_exchange(client, project_id, csrf)
    public_id = str(exchange["public_id"])

    downloaded = client.get(str(exchange["json_url"]))
    assert downloaded.status_code == 200
    assert downloaded.json()["exchange_id"] == public_id
    payload = response_package(public_id)
    first = client.post(
        f"/eva/exchanges/{public_id}/import",
        json=payload,
        headers={"X-CSRF-Token": csrf},
    )
    second = client.post(
        f"/eva/exchanges/{public_id}/import",
        json=payload,
        headers={"X-CSRF-Token": csrf},
    )
    assert first.status_code == second.status_code == 200
    assert [item["id"] for item in first.json()] == [item["id"] for item in second.json()]
    with factory() as database:
        actions = list(database.scalars(select(AuditEvent.action).order_by(AuditEvent.id)))
        assert actions == ["EVA_EXCHANGE_EXPORTED", "EVA_RESPONSE_IMPORTED"]
        assert all("content" not in event.details for event in database.scalars(select(AuditEvent)))


def test_permissions_validation_duplicate_and_conversion(eva_context) -> None:
    client, factory, project_id = eva_context
    csrf = login(client, "tester@example.com", "tester-password-123")
    exchange = create_exchange(client, project_id, csrf)
    public_id = str(exchange["public_id"])
    invalid = response_package(public_id)
    invalid["schema_version"] = "2.0"
    assert (
        client.post(
            f"/eva/exchanges/{public_id}/import",
            json=invalid,
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 422
    )
    imported = client.post(
        f"/eva/exchanges/{public_id}/import",
        json=response_package(public_id),
        headers={"X-CSRF-Token": csrf},
    ).json()
    proposal_id = imported[0]["id"]
    duplicate_id = imported[1]["id"]
    assert (
        client.patch(
            f"/eva/proposals/{duplicate_id}",
            json={"title": "  Lógin   válido "},
            headers={"X-CSRF-Token": csrf},
        ).json()["duplicate"]
        is True
    )
    assert (
        client.post(
            f"/eva/proposals/{proposal_id}/approve", headers={"X-CSRF-Token": csrf}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/eva/proposals/{duplicate_id}/reject", headers={"X-CSRF-Token": csrf}
        ).status_code
        == 200
    )
    converted = client.post(f"/eva/proposals/{proposal_id}/approve", headers={"X-CSRF-Token": csrf})
    assert converted.status_code == 200
    assert converted.json()["status"] == "CONVERTED"
    assert (
        client.post(
            f"/eva/proposals/{proposal_id}/approve", headers={"X-CSRF-Token": csrf}
        ).status_code
        == 409
    )
    with factory() as database:
        test_case = database.scalar(select(TestCase))
        assert test_case is not None
        assert test_case.origin is TestOrigin.EVA

    dev_csrf = login(client, "dev@example.com", "developer-password-123")
    assert client.get(f"/projects/{project_id}/eva/proposals").status_code == 200
    assert (
        client.post(
            f"/projects/{project_id}/eva/exchanges",
            json={"title": "X", "content": "Y"},
            headers={"X-CSRF-Token": dev_csrf},
        ).status_code
        == 403
    )
