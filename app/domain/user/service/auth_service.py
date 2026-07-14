"""
인증 서비스 (회원가입 오케스트레이션).

회원가입:
- 이메일 정규화
- 중복 이메일 확인 (최종 보장은 DB unique constraint)
- Argon2id 비밀번호 해시
- 사용자 생성 transaction
- 동시 중복 가입 unique violation 을 409 로 변환

가입 성공 후 자동 로그인하지 않는다.
"""
import logging
from datetime import datetime, timezone

from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from app.domain.user.dto.request import SignupRequest
from app.domain.user.dto.response import AuthUserResponse
from app.domain.user.entity.models import User
from app.domain.user.repository import UserRepository
from app.domain.user.service import password_service
from app.common.exceptions import EmailAlreadyExistsError
from app.common.security import normalize_email

logger = logging.getLogger(__name__)


class AuthService:
    """회원가입/로그인 규칙과 transaction 경계."""

    def __init__(self, session: Session):
        self.session = session
        self.user_repo = UserRepository(session)

    def signup(self, request: SignupRequest) -> AuthUserResponse:
        # 입력 정규화
        email = normalize_email(str(request.email))
        name = request.name.strip()

        # 애플리케이션 단 중복 확인
        existing = self.user_repo.get_by_email(email)
        if existing is not None:
            raise EmailAlreadyExistsError()

        # 비밀번호 해싱
        password_hash = password_service.hash_password(request.password)

        now = datetime.now(timezone.utc)
        user = User(
            email=email,
            password_hash=password_hash,
            name=name,
            role="user",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        try:
            user = self.user_repo.create(user)
        except IntegrityError:
            self.session.rollback()
            # 동시 가입으로 인한 unique violation → 409
            raise EmailAlreadyExistsError()

        logger.info("사용자 가입 완료: user_id=%s", user.id)

        return AuthUserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
        )