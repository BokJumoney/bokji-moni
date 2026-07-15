"""
사용자·인증 세션 SQLModel 엔티티.

회원가입 구현을 위해 User 모델을 포함한다.
AuthSession 모델은 로그인 단계에서 사용되지만 스키마를 함께 정의하여
create_all() 시 테이블이 생성되도록 한다.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.common.timezone import now_kst


def _utcnow() -> datetime:
    return now_kst()


class User(SQLModel, table=True):
    """가입 사용자 계정."""

    __tablename__ = "users"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    email: str = Field(max_length=320, unique=True, index=True, nullable=False)
    password_hash: str = Field(nullable=False)
    name: str = Field(max_length=100, nullable=False)
    role: str = Field(default="user", max_length=20, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(
        default_factory=_utcnow,
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=_utcnow,
        nullable=False,
    )


class AuthSession(SQLModel, table=True):
    """서버 측 인증 세션 저장소. 로그인 단계에서 사용."""

    __tablename__ = "auth_sessions"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    token_hash: str = Field(max_length=64, unique=True, index=True, nullable=False)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    created_at: datetime = Field(default_factory=_utcnow, nullable=False)
    last_seen_at: datetime = Field(default_factory=_utcnow, nullable=False)
    idle_expires_at: datetime = Field(nullable=False)
    absolute_expires_at: datetime = Field(nullable=False)
    revoked_at: Optional[datetime] = Field(default=None)
    user_agent_hash: Optional[str] = Field(default=None, max_length=64)