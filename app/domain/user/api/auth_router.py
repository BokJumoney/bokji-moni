"""
인증 API 라우터.

- POST /api/v1/auth/signup → 201 Created
- POST /api/v1/auth/login  → 200 + Set-Cookie
- GET  /api/v1/auth/session → 200 SessionResponse (세션 필요)
- POST /api/v1/auth/logout  → 204 (선택적 세션)
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session

from app.common.exceptions import AuthError
from app.common.security import build_session_cookie, build_session_delete_cookie
from app.domain.user.dependencies import (
    get_current_auth_session,
    get_current_user,
    get_optional_auth_session,
)
from app.domain.user.dto.request import LoginRequest, SignupRequest
from app.domain.user.dto.response import (
    AuthUserResponse,
    LoginResponse,
    SessionResponse,
)
from app.domain.user.entity.models import AuthSession, User
from app.domain.user.repository.repository import AuthSessionRepository
from app.domain.user.service.auth_service import AuthService
from app.infrastructure.db.connection import get_session

router = APIRouter()


def _auth_error_to_http(exc: AuthError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


@router.post(
    "/signup",
    response_model=AuthUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
)
def signup(
    body: SignupRequest,
    session: Session = Depends(get_session),
) -> AuthUserResponse:
    service = AuthService(session)
    try:
        return service.signup(body)
    except AuthError as exc:
        raise _auth_error_to_http(exc) from exc


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="로그인",
)
def login(
    body: LoginRequest,
    http_response: Response,
    http_request: Request,
    session: Session = Depends(get_session),
) -> LoginResponse:
    client_ip = (
        http_request.client.host if http_request and http_request.client else "unknown"
    )
    service = AuthService(session)
    try:
        login_response, token = service.login(body, client_ip)
    except AuthError as exc:
        raise _auth_error_to_http(exc) from exc

    http_response.set_cookie(**build_session_cookie(token))
    http_response.headers["Cache-Control"] = "no-store"
    return login_response


@router.get(
    "/session",
    response_model=SessionResponse,
    summary="세션 확인",
)
def check_session(
    http_response: Response,
    user: User = Depends(get_current_user),
    auth_session: AuthSession = Depends(get_current_auth_session),
) -> SessionResponse:
    """현재 로그인 사용자와 세션 만료 정보를 반환한다."""
    http_response.headers["Cache-Control"] = "no-store"
    return SessionResponse(
        user=AuthUserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
        ),
        idle_expires_at=auth_session.idle_expires_at,
        absolute_expires_at=auth_session.absolute_expires_at,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="로그아웃",
)
def logout(
    http_response: Response,
    session: Session = Depends(get_session),
    auth_session: AuthSession | None = Depends(get_optional_auth_session),
):
    """현재 세션을 폐기하고 세션 쿠키를 삭제한다.

    로그인 상태가 아니어도 호출할 수 있으며, 이 경우 쿠키만 정리한다.
    """
    http_response.headers["Cache-Control"] = "no-store"
    if auth_session is not None:
        AuthSessionRepository(session).revoke(auth_session)
    http_response.set_cookie(**build_session_delete_cookie())