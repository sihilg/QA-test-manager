from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from qa_test_manager.database import get_session
from qa_test_manager.main import app
from qa_test_manager.models import AuditEvent, Base, User, UserRole
from qa_test_manager.security import hash_password


@pytest.fixture
def user_context() -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    with testing_session() as database:
        database.add(
            User(
                name="Admin",
                email="admin@example.com",
                password_hash=hash_password("admin-password-123"),
                role=UserRole.ADMIN,
            )
        )
        database.commit()

    def override_session() -> Iterator[Session]:
        with testing_session() as database:
            yield database

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        yield client, testing_session
    app.dependency_overrides.clear()


def login(client: TestClient, email = "admin@example.com", password = "admin-password-123") -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return str(response.json()["csrf_token"])


def test_admin_can_create_edit_deactivate_and_activate_user(
    user_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session = user_context
    headers = {"X-CSRF-Token": login(client)}
    created = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Tester",
            "email": "tester@example.com",
            "password": "tester-password-123",
            "role": "TESTER",
        },
    )
    assert created.status_code == 201
    user = created.json()
    assert "password_hash" not in user

    updated = client.patch(
        f"/users/{user['id']}",
        headers=headers,
        json={"name": "Tester QA", "role": "DEV", "version": user["version"]},
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "DEV"

    deactivated = client.post(f"/users/{user['id']}/deactivate", headers=headers)
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert client.post(
        "/auth/login",
        json={"email": "tester@example.com", "password": "tester-password-123"},
    ).status_code == 401

    activated = client.post(f"/users/{user['id']}/activate", headers=headers)
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True

    with testing_session() as database:
        actions = list(
            database.scalars(
                select(AuditEvent.action)
                .where(AuditEvent.entity_type == "User")
                .order_by(AuditEvent.id)
            )
        )
    assert actions == ["USER_CREATED", "USER_UPDATED", "USER_DEACTIVATED", "USER_ACTIVATED"]


def test_last_active_admin_cannot_be_deactivated_or_demoted(
    user_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = user_context
    headers = {"X-CSRF-Token": login(client)}
    admin = client.get("/users", headers=headers).json()["items"][0]

    deactivated = client.post(f"/users/{admin['id']}/deactivate", headers=headers)
    demoted = client.patch(
        f"/users/{admin['id']}",
        headers=headers,
        json={"role": "TESTER", "version": admin["version"]},
    )

    assert deactivated.status_code == 409
    assert demoted.status_code == 409


def test_duplicate_email_and_stale_version_return_conflict(
    user_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = user_context
    headers = {"X-CSRF-Token": login(client)}
    duplicate = client.post(
        "/users",
        headers=headers,
        json={
            "name": "Outro Admin",
            "email": "ADMIN@example.com",
            "password": "another-password-123",
            "role": "ADMIN",
        },
    )
    admin = client.get("/users", headers=headers).json()["items"][0]
    stale = client.patch(
        f"/users/{admin['id']}",
        headers=headers,
        json={"name": "Nome novo", "version": 99},
    )

    assert duplicate.status_code == 409
    assert stale.status_code == 409


def test_non_admin_cannot_list_or_create_users(
    user_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session = user_context
    with testing_session() as database:
        database.add(
            User(
                name="Tester",
                email="tester@example.com",
                password_hash=hash_password("tester-password-123"),
                role=UserRole.TESTER,
            )
        )
        database.commit()
    headers = {"X-CSRF-Token": login(client, "tester@example.com", "tester-password-123")}

    assert client.get("/users", headers=headers).status_code == 403
    assert client.post(
        "/users",
        headers=headers,
        json={
            "name": "Dev",
            "email": "dev@example.com",
            "password": "developer-password-123",
            "role": "DEV",
        },
    ).status_code == 403
