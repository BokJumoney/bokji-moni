"""
사용자·세션 리포지토리 (SQLModel 기반).

- UserRepository: 사용자 생성·이메일/ID 조회
- AuthSessionRepository: 세션 생성·토큰 해시 조회·폐기·touch
"""
from datetime import timedelta
from typing import Optional

from sqlmodel import Session, select

from app.common.timezone import now_kst
from app.domain.user.entity.models import AuthSession, User


class UserRepository:
    """users 테이블 DB 접근."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        return self.session.exec(stmt).first()

    def get_by_id(self, user_id) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        return self.session.exec(stmt).first()

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user


class AuthSessionRepository:
    """auth_sessions 테이블 DB 접근."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, auth_session: AuthSession) -> AuthSession:
        self.session.add(auth_session)
        self.session.commit()
        self.session.refresh(auth_session)
        return auth_session

    def get_by_token_hash(self, token_hash: str) -> Optional[AuthSession]:
        stmt = select(AuthSession).where(AuthSession.token_hash == token_hash)
        return self.session.exec(stmt).first()

    def revoke(self, auth_session: AuthSession) -> AuthSession:
        auth_session.revoked_at = now_kst()
        self.session.add(auth_session)
        self.session.commit()
        self.session.refresh(auth_session)
        return auth_session

    def touch(
        self,
        auth_session: AuthSession,
        idle_minutes: int,
    ) -> AuthSession:
        """last_seen_at과 idle 만료 시각을 갱신하고 commit 한다."""
        from app.infrastructure.config import settings

        now = now_kst()
        auth_session.last_seen_at = now
        auth_session.idle_expires_at = now + timedelta(minutes=idle_minutes)
        self.session.add(auth_session)
        self.session.commit()
        self.session.refresh(auth_session)
        return auth_session