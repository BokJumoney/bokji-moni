"""
인증 API 라우터.

회원가입 엔드포인트만 구현한다.
- POST /api/v1/auth/signup → 201 Created
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.common.exceptions import AuthError
from app.domain.user.dto.request import SignupRequest
from app.domain.user.dto.response import AuthUserResponse
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
    request: SignupRequest,
    session: Session = Depends(get_session),
) -> AuthUserResponse:
    service = AuthService(session)
    try:
        return service.signup(request)
    except AuthError as exc:
        raise _auth_error_to_http(exc) from exc