"""
채팅/인증 공통 의존성.

- get_current_auth_session: 쿠키 → AuthSession 검증 (revoked/만료)
- get_current_user: AuthSession → User 주입 (is_active 확인, touch)
- 인증 실패는 일관된 401 응답으로 처리한다.
"""
import logging
from datetime import datetime

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from app.common.exceptions import (
    AuthenticationRequiredError,
    ForbiddenError,
    SessionExpiredError,
)
from app.common.security import hash_session_token
from app.common.timezone import as_kst, now_kst
from app.domain.user.entity.models import User, UserRole
from app.domain.user.repository.repository import AuthSessionRepository, UserRepository
from app.infrastructure.config import settings
from app.infrastructure.db.connection import get_session

logger = logging.getLogger(__name__)


def _cookie_name() -> str:
    name = settings.SESSION_COOKIE_NAME
    if settings.APP_ENV == "production":
        name = f"__Host-{name}"
    return name


def _unauthorized(exc, request: Request) -> HTTPException:
    custom_auth = "BokjiAuthSession" in request.headers.get("vary", "")
    del custom_auth  # 참고용: vary 헤더 처리는 router 단에서 수행
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": exc.code, "message": exc.message},
        headers={"WWW-Authenticate": 'Cookie realm="bokji"'},
    )


_MISSING = object()


def _resolve_auth_session(request: Request, session: Session):
    """쿠키에서 토큰을 읽어 AuthSession 을 반환한다.

    반환값:
      - AuthSession: 유효한 세션
      - _MISSING: 쿠키 없음 또는 토큰 미일치
      - SessionExpiredError: 폐기/만료된 세션
    """
    token = request.cookies.get(_cookie_name())
    if not token:
        return _MISSING

    token_hash = hash_session_token(token)
    auth_session = AuthSessionRepository(session).get_by_token_hash(token_hash)
    if auth_session is None:
        return _MISSING

    now = now_kst()
    if auth_session.revoked_at is not None:
        return SessionExpiredError()
    if as_kst(auth_session.idle_expires_at) <= now:
        return SessionExpiredError()
    if as_kst(auth_session.absolute_expires_at) <= now:
        return SessionExpiredError()

    return auth_session


def get_current_auth_session(
    request: Request,
    session: Session = Depends(get_session),
):
    """쿠키에서 토큰을 읽어 유효한 AuthSession 을 반환한다."""
    result = _resolve_auth_session(request, session)
    if isinstance(result, SessionExpiredError):
        raise _unauthorized(result, request)
    if result is _MISSING:
        raise _unauthorized(AuthenticationRequiredError(), request)
    return result


def get_optional_auth_session(
    request: Request,
    session: Session = Depends(get_session),
):
    """로그아웃 등에서 쓰는 선택적 세션. 유효 세션이 없으면 None."""
    result = _resolve_auth_session(request, session)
    if result is _MISSING or isinstance(result, SessionExpiredError):
        return None
    return result


def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
    auth_session=Depends(get_current_auth_session),
) -> User:
    """유효한 AuthSession 에 연결된 활성 User 를 반환하고 touch 한다."""
    user = UserRepository(session).get_by_id(auth_session.user_id)
    if user is None or not user.is_active:
        raise _unauthorized(AuthenticationRequiredError(), request)

    # touch interval 이 지난 경우에만 last_seen_at 갱신
    now = now_kst()
    touch_interval = settings.SESSION_TOUCH_INTERVAL_SECONDS
    last_seen = as_kst(auth_session.last_seen_at)
    if (now - last_seen).total_seconds() >= touch_interval:
        AuthSessionRepository(session).touch(
            auth_session, settings.SESSION_IDLE_MINUTES
        )

    return user


def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    """현재 사용자가 관리자인지 확인하고, 아니면 접근을 거부한다."""
    if user.role != UserRole.ADMIN.value:
        exc = ForbiddenError()
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        )
    return user
