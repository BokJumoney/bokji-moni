"""
사용자·인증 세션·사용자 복지 정보 SQLModel 엔티티.

- User: 가입 사용자 계정
- AuthSession: 서버 측 인증 세션 저장소
- UserBackground: 사용자별 1:1 복지 맞춤 정보 (마이페이지 대상)
"""
import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional
from sqlalchemy import BigInteger, CheckConstraint, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, SQLModel
from app.common.timezone import now_kst


def _utcnow() -> datetime:
    return now_kst()


class UserRole(str, Enum):
    """서비스에서 지원하는 사용자 역할."""

    USER = "user"
    ADMIN = "admin"


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
    role: str = Field(default=UserRole.USER.value, max_length=20, nullable=False)
    noti_agreed: bool = Field(default=False, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(
        default_factory=_utcnow,
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=_utcnow,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'admin')",
            name="users_role_allowed",
        ),
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

class UserBackground(SQLModel, table=True):
    __tablename__ = "user_background"

    user_id: uuid.UUID = Field(
        primary_key=True,
        foreign_key="users.id",  # 실제 유저 테이블명에 맞게 수정
    )

    income: int | None = Field(default=None, ge=0)
    age: int | None = Field(default=None, ge=0)
    family_size: int | None = Field(default=None, ge=1)

    disability: bool | None = Field(default=None)
    assets: int | None = Field(default=None, ge=0)

    employment_stat: str | None = Field(
        default=None,
        max_length=30,
    )

    updated_at: datetime = Field(
        default_factory=datetime.now,
    )