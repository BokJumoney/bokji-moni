"""
인증 API 라우터.

- POST /api/v1/auth/signup → 201 Created
- POST /api/v1/auth/login  → 200 + Set-Cookie
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session

from app.common.exceptions import AuthError
from app.common.security import build_session_cookie
from app.domain.user.dto.request import LoginRequest, SignupRequest
from app.domain.user.dto.response import AuthUserResponse, LoginResponse
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