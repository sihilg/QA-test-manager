from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from qa_test_manager.auth import AuthContext, require_roles
from qa_test_manager.database import get_session
from qa_test_manager.main import app
from qa_test_manager.models import AuthSession, Base, User, UserRole
from qa_test_manager.security import hash_password


@pytest.fixture
def auth_client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    with testing_session() as database:
        database.add(
            User(
                name="Admin Local",
                email="admin@example.com",
                password_hash=hash_password("correct-horse-battery-staple"),
                role=UserRole.ADMIN,
            )
        )
        database.commit()

    def override_session() -> Iterator[Session]:
        with testing_session() as database:
            yield database

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_login_sets_http_only_session_cookie(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/auth/login",
        json={"email": "ADMIN@example.com", "password": "correct-horse-battery-staple"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "ADMIN"
    cookie = response.headers["set-cookie"]
    assert "qatm_session=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "correct-horse" not in response.text


def test_invalid_login_does_not_reveal_account_state(auth_client: TestClient) -> None:
    wrong_password = auth_client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "wrong-password"}
    )
    unknown_user = auth_client.post(
        "/auth/login", json={"email": "unknown@example.com", "password": "wrong-password"}
    )

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()


def test_inactive_user_cannot_login(auth_client: TestClient) -> None:
    override = app.dependency_overrides[get_session]
    database = next(override())
    user = database.scalar(select(User).where(User.email == "admin@example.com"))
    assert user is not None
    user.is_active = False
    database.commit()
    database.close()

    response = auth_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "correct-horse-battery-staple"},
    )

    assert response.status_code == 401


def test_me_requires_valid_session(auth_client: TestClient) -> None:
    assert auth_client.get("/auth/me").status_code == 401
    auth_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "correct-horse-battery-staple"},
    )
    authenticated = auth_client.get("/auth/me")
    assert authenticated.status_code == 200
    assert authenticated.json()["email"] == "admin@example.com"


def test_session_can_be_restored_with_a_new_csrf_token(auth_client: TestClient) -> None:
    login = auth_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "correct-horse-battery-staple"},
    )

    restored = auth_client.get("/auth/session")

    assert restored.status_code == 200
    assert restored.json()["user"]["email"] == "admin@example.com"
    assert restored.json()["csrf_token"] != login.json()["csrf_token"]


def test_logout_requires_csrf_and_revokes_session(auth_client: TestClient) -> None:
    login = auth_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "correct-horse-battery-staple"},
    )
    csrf_token = login.json()["csrf_token"]

    assert auth_client.post("/auth/logout").status_code == 403
    logout = auth_client.post("/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout.status_code == 204
    assert auth_client.get("/auth/me").status_code == 401


def test_role_guard_rejects_a_different_profile() -> None:
    user = User(
        name="Tester", email="tester@example.com", password_hash="not-used", role=UserRole.TESTER
    )
    auth_session = AuthSession(
        user=user,
        token_hash="a" * 64,
        csrf_token_hash="b" * 64,
        expires_at=datetime.now(UTC),
    )
    guard = require_roles(UserRole.ADMIN)

    with pytest.raises(HTTPException) as error:
        guard(AuthContext(user, auth_session))

    assert error.value.status_code == 403
