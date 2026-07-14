"""
사용자 리포지토리 (SQLModel 기반).

- UserRepository: 사용자 생성·이메일 조회
"""
from typing import Optional

from sqlmodel import Session, select

from app.domain.user.entity.models import User

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