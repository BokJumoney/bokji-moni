"""
인증 서비스 (회원가입·로그인 오케스트레이션).

회원가입:
- 이메일 정규화 → 중복 확인 → Argon2id 해시 → 사용자 생성
- 동시 중복 가입 unique violation → 409

로그인:
- 이메일 정규화 → 사용자 조회
- 사용자 미존재 시 dummy hash 검증 (타이밍 부채널 방어)
- 비밀번호 검증 → is_active 확인 → 세션 토큰 생성/해시
- auth_sessions INSERT → 쿠키용 원본 토큰 반환
- 로그인 시도 제한 (이메일+IP 기준 인메모리, 5회/5분)
- 공통 실패 메시지, 비밀번호 미노출 로깅

가입 성공 후 자동 로그인하지 않는다.
로그인 성공 시 항상 새 세션을 발급한다.
"""
import logging
import time
from datetime import datetime, timedelta

from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from app.common.exceptions import (
    AccountDisabledError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    TooManyLoginAttemptsError,
)
from app.common.security import (
    generate_session_token,
    hash_session_token,
    normalize_email,
)
from app.common.timezone import now_kst
from app.domain.user.dto.request import LoginRequest, SignupRequest
from app.domain.user.dto.response import AuthUserResponse, LoginResponse
from app.domain.user.entity.models import AuthSession, User, UserRole
from app.domain.user.repository.repository import UserRepository, AuthSessionRepository
from app.domain.user.service import password_service
from app.infrastructure.config import settings

logger = logging.getLogger(__name__)

_DUMMY_HASH = password_service.hash_password(
    "dummy_placeholder_7f1a8b3c_used_for_timing_defense_only"
)

_LOGIN_ATTEMPTS: dict[str, list[float]] = {}

_MAX_LOGIN_ATTEMPTS = 5
_LOGIN_ATTEMPT_WINDOW_SECONDS = 300


def _check_login_rate_limit(email: str, client_ip: str) -> None:
    key = f"{email}:{client_ip}"
    now = time.time()
    attempts = _LOGIN_ATTEMPTS.get(key, [])
    attempts = [t for t in attempts if now - t < _LOGIN_ATTEMPT_WINDOW_SECONDS]
    _LOGIN_ATTEMPTS[key] = attempts
    if len(attempts) >= _MAX_LOGIN_ATTEMPTS:
        raise TooManyLoginAttemptsError()


def _record_login_failure(email: str, client_ip: str) -> None:
    key = f"{email}:{client_ip}"
    now = time.time()
    _LOGIN_ATTEMPTS.setdefault(key, []).append(now)


def _clear_login_attempts(email: str, client_ip: str) -> None:
    key = f"{email}:{client_ip}"
    _LOGIN_ATTEMPTS.pop(key, None)


class AuthService:
    """회원가입/로그인 규칙과 transaction 경계."""

    def __init__(self, session: Session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.session_repo = AuthSessionRepository(session)

    def signup(self, request: SignupRequest) -> AuthUserResponse:
        email = normalize_email(str(request.email))
        name = request.name.strip()

        existing = self.user_repo.get_by_email(email)
        if existing is not None:
            raise EmailAlreadyExistsError()

        password_hash = password_service.hash_password(request.password)
        now = now_kst()
        user = User(
            email=email,
            password_hash=password_hash,
            name=name,
            role=UserRole.USER.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        try:
            user = self.user_repo.create(user)
        except IntegrityError:
            self.session.rollback()
            raise EmailAlreadyExistsError()

        logger.info("사용자 가입 완료: user_id=%s", user.id)

        return AuthUserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
        )

    def login(
        self,
        request: LoginRequest,
        client_ip: str,
    ) -> tuple[LoginResponse, str]:
        email = normalize_email(str(request.email))

        _check_login_rate_limit(email, client_ip)

        user = self.user_repo.get_by_email(email)

        if user is None:
            password_service.verify_password(request.password, _DUMMY_HASH)
            _record_login_failure(email, client_ip)
            raise InvalidCredentialsError()

        is_valid, updated_hash = password_service.verify_and_update(
            request.password, user.password_hash
        )

        if not is_valid:
            _record_login_failure(email, client_ip)
            raise InvalidCredentialsError()

        if not user.is_active:
            raise AccountDisabledError()

        if updated_hash is not None:
            user.password_hash = updated_hash
            user.updated_at = now_kst()
            self.session.add(user)
            self.session.commit()

        token = generate_session_token()
        token_hash = hash_session_token(token)

        now = now_kst()
        auth_session = AuthSession(
            token_hash=token_hash,
            user_id=user.id,
            created_at=now,
            last_seen_at=now,
            idle_expires_at=now + timedelta(minutes=settings.SESSION_IDLE_MINUTES),
            absolute_expires_at=now + timedelta(hours=settings.SESSION_ABSOLUTE_HOURS),
        )
        self.session_repo.create(auth_session)

        _clear_login_attempts(email, client_ip)
        logger.info("로그인 성공: user_id=%s", user.id)

        login_response = LoginResponse(
            user=AuthUserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
            ),
            expires_at=auth_session.absolute_expires_at,
        )

        return login_response, token
