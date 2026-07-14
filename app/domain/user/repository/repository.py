"""
사용자·세션 리포지토리 (SQLModel 기반).

- UserRepository: 사용자 생성·이메일 조회
- AuthSessionRepository: 세션 생성·토큰 해시 조회·폐기
"""
from typing import Optional

from sqlmodel import Session, select

from app.domain.user.entity.models import AuthSession, User

class UserRepository:
    """users 테이블 DB 접근."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
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
        from datetime import datetime, timezone

        auth_session.revoked_at = datetime.now(timezone.utc)
        self.session.add(auth_session)
        self.session.commit()
        self.session.refresh(auth_session)
        return auth_session