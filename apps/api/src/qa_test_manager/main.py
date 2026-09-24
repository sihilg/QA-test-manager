from typing import Annotated, Literal, TypedDict

from fastapi import Depends, FastAPI, Response, status
from sqlalchemy.orm import Session

from qa_test_manager.auth import (
    AuthContext,
    LoginRequest,
    SessionResponse,
    UserResponse,
    get_auth_context,
    login_user,
    logout_user,
    refresh_session,
    require_csrf,
)
from qa_test_manager.database import get_session
from qa_test_manager.projects import router as projects_router
from qa_test_manager.test_cases import router as test_cases_router
from qa_test_manager.users import router as users_router


class HealthResponse(TypedDict):
    status: Literal["ok"]
    service: str


app = FastAPI(title="QA Test Manager API", version="0.1.0")
app.include_router(projects_router)
app.include_router(test_cases_router)
app.include_router(users_router)


@app.get("/health", tags=["system"])
def health() -> HealthResponse:
    return {"status": "ok", "service": "qa-test-manager-api"}


@app.post("/auth/login", response_model=SessionResponse, tags=["authentication"])
def login(
    payload: LoginRequest,
    response: Response,
    database: Annotated[Session, Depends(get_session)],
) -> SessionResponse:
    return login_user(payload, response, database)


@app.get("/auth/me", response_model=UserResponse, tags=["authentication"])
def current_user(context: Annotated[AuthContext, Depends(get_auth_context)]) -> UserResponse:
    return UserResponse.model_validate(context.user)


@app.get("/auth/session", response_model=SessionResponse, tags=["authentication"])
def current_session(
    context: Annotated[AuthContext, Depends(get_auth_context)],
    database: Annotated[Session, Depends(get_session)],
) -> SessionResponse:
    return refresh_session(context, database)


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["authentication"])
def logout(
    response: Response,
    context: Annotated[AuthContext, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_session)],
) -> None:
    logout_user(response, context, database)
