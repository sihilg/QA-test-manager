from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from qa_test_manager.auth import AuthContext, ensure_roles, require_csrf
from qa_test_manager.database import get_session
from qa_test_manager.models import AuditEvent, User, UserRole
from qa_test_manager.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=1024)
    role: UserRole


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    role: UserRole | None = None
    password: str | None = Field(default=None, min_length=12, max_length=1024)
    version: int = Field(ge=1)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class UserPage(BaseModel):
    items: list[UserResponse]
    total: int
    offset: int
    limit: int


@router.get("", response_model=UserPage)
def list_users(
    context: Annotated[AuthContext, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_session)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> UserPage:
    ensure_roles(context.user, UserRole.ADMIN)
    statement = select(User).order_by(User.name, User.id)
    total = database.scalar(select(func.count()).select_from(User)) or 0
    users = list(database.scalars(statement.offset(offset).limit(limit)))
    return UserPage(
        items=[UserResponse.model_validate(user) for user in users],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    context: Annotated[AuthContext, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_session)],
) -> UserResponse:
    ensure_roles(context.user, UserRole.ADMIN)
    user = User(
        name=payload.name.strip(),
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    database.add(user)
    return _commit_user(database, context, user, "USER_CREATED")


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    context: Annotated[AuthContext, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_session)],
) -> UserResponse:
    ensure_roles(context.user, UserRole.ADMIN)
    user = _user_or_404(database, user_id)
    if user.version != payload.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O utilizador foi alterado por outra operação.",
        )
    next_role = payload.role or user.role
    if user.is_active and user.role is UserRole.ADMIN and next_role is not UserRole.ADMIN:
        _ensure_another_active_admin(database, user.id)
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.email is not None:
        user.email = str(payload.email).lower()
    if payload.role is not None:
        user.role = payload.role
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    return _commit_user(database, context, user, "USER_UPDATED")


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    context: Annotated[AuthContext, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_session)],
) -> UserResponse:
    ensure_roles(context.user, UserRole.ADMIN)
    user = _user_or_404(database, user_id)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="O utilizador já está inativo."
        )
    if user.role is UserRole.ADMIN:
        _ensure_another_active_admin(database, user.id)
    user.is_active = False
    return _commit_user(database, context, user, "USER_DEACTIVATED")


@router.post("/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: int,
    context: Annotated[AuthContext, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_session)],
) -> UserResponse:
    ensure_roles(context.user, UserRole.ADMIN)
    user = _user_or_404(database, user_id)
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="O utilizador já está ativo."
        )
    user.is_active = True
    return _commit_user(database, context, user, "USER_ACTIVATED")


def _ensure_another_active_admin(database: Session, excluded_user_id: int) -> None:
    count = database.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
            User.id != excluded_user_id,
        )
    ) or 0
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O último Admin ativo não pode ser desativado nem perder o perfil Admin.",
        )


def _user_or_404(database: Session, user_id: int) -> User:
    user = database.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado."
        )
    return user


def _commit_user(
    database: Session, context: AuthContext, user: User, action: str
) -> UserResponse:
    try:
        database.flush()
        database.add(
            AuditEvent(
                actor_user_id=context.user.id,
                action=action,
                entity_type="User",
                entity_id=str(user.id),
                details={"role": user.role.value, "is_active": user.is_active},
            )
        )
        database.commit()
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um utilizador com este email.",
        ) from error
    except StaleDataError as error:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O utilizador foi alterado por outra operação.",
        ) from error
    database.refresh(user)
    return UserResponse.model_validate(user)
