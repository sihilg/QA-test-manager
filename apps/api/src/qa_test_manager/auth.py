from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from qa_test_manager.database import get_session
from qa_test_manager.models import AuthSession, User, UserRole
from qa_test_manager.security import digest_token, new_token, verify_password

SESSION_COOKIE = "qatm_session"
SESSION_DURATION = timedelta(hours=12)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: UserRole


class SessionResponse(BaseModel):
    user: UserResponse
    csrf_token: str


class AuthContext:
    def __init__(self, user: User, auth_session: AuthSession) -> None:
        self.user = user
        self.session = auth_session


def login_user(payload: LoginRequest, response: Response, database: Session) -> SessionResponse:
    email = payload.email.lower().strip()
    user = database.scalar(select(User).where(User.email == email))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou palavra-passe inválidos.",
        )

    session_token = new_token()
    csrf_token = new_token()
    auth_session = AuthSession(
        user=user,
        token_hash=digest_token(session_token),
        csrf_token_hash=digest_token(csrf_token),
        expires_at=datetime.now(UTC) + SESSION_DURATION,
    )
    database.add(auth_session)
    database.commit()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )
    return SessionResponse(user=UserResponse.model_validate(user), csrf_token=csrf_token)


def get_auth_context(
    database: Annotated[Session, Depends(get_session)],
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> AuthContext:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão necessária.")

    auth_session = database.scalar(
        select(AuthSession).where(AuthSession.token_hash == digest_token(session_token))
    )
    now = datetime.now(UTC)
    if (
        auth_session is None
        or auth_session.revoked_at is not None
        or _as_utc(auth_session.expires_at) <= now
        or not auth_session.user.is_active
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida.")
    return AuthContext(auth_session.user, auth_session)


def require_csrf(
    context: Annotated[AuthContext, Depends(get_auth_context)],
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> AuthContext:
    if not csrf_token or digest_token(csrf_token) != context.session.csrf_token_hash:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token CSRF inválido.")
    return context


def require_roles(*roles: UserRole) -> Callable[[AuthContext], User]:
    def dependency(context: Annotated[AuthContext, Depends(get_auth_context)]) -> User:
        if context.user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso proibido.")
        return context.user

    return dependency


def ensure_roles(user: User, *roles: UserRole) -> None:
    if user.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso proibido.")


def refresh_session(context: AuthContext, database: Session) -> SessionResponse:
    csrf_token = new_token()
    context.session.csrf_token_hash = digest_token(csrf_token)
    database.commit()
    return SessionResponse(user=UserResponse.model_validate(context.user), csrf_token=csrf_token)


def logout_user(response: Response, context: AuthContext, database: Session) -> None:
    context.session.revoked_at = datetime.now(UTC)
    database.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
