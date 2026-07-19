"""
사용자·인증 세션·사용자 복지 정보 SQLModel 엔티티.

- User: 가입 사용자 계정
- AuthSession: 서버 측 인증 세션 저장소
- UserWelfare: 사용자별 1:1 복지 맞춤 정보 (마이페이지 대상)
"""
import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, ForeignKey, true
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
    is_active: bool = Field(default=True, nullable=False)
    # 알림 수신 여부는 개별 정책 구독 행과 분리해 사용자 계정에 한 번만 저장한다.
    # ORM을 거치지 않는 INSERT에도 같은 기본값이 적용되도록 DB 기본값도 둔다.
    notification_enabled: bool = Field(
        default=True,
        sa_column=Column(
            "notification_enabled",
            Boolean,
            nullable=False,
            server_default=true(),
        ),
    )
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


class UserWelfare(SQLModel, table=True):
    """사용자별 복지 맞춤 정보.

    `users(1) : user_welfare(0..1)` 관계로 사용자당 최대 한 행을 갖는다.
    아직 입력하지 않은 사용자는 행이 존재하지 않아도 된다.
    모든 선택 필드는 미입력(null)·명시적 false/0 을 구분하기 위해 nullable 이다.
    """

    __tablename__ = "user_detail"

    user_id: uuid.UUID = Field(
        sa_column=Column(
            "user_id",
            UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    birth_date: Optional[date] = Field(default=None, description="생년월일(나이 대신 저장)")
    monthly_income: Optional[int] = Field(
        default=None,
        sa_column=Column("monthly_income", BigInteger, nullable=True),
        description="월 가구 소득(원 단위 정수)",
    )
    family_size: Optional[int] = Field(
        default=None,
        description="가구원 수",
    )
    household_type: Optional[str] = Field(
        default=None,
        max_length=50,
        description="가구 유형(1인, 한부모, 다문화 등)",
    )
    region: Optional[str] = Field(
        default=None,
        max_length=100,
        description="시·도",
    )
    district: Optional[str] = Field(
        default=None,
        max_length=100,
        description="시·군·구",
    )
    has_disability: Optional[bool] = Field(
        default=None,
        description="장애 여부(미응답 null 과 false 구분)",
    )
    assets: Optional[int] = Field(
        default=None,
        sa_column=Column("assets", BigInteger, nullable=True),
        description="가구 자산(원 단위 정수)",
    )
    employment_status: Optional[str] = Field(
        default=None,
        max_length=50,
        description="고용 상태(재직, 구직, 실업, 학생 등)",
    )
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
            "monthly_income IS NULL OR monthly_income >= 0",
            name="user_welfare_monthly_income_non_negative",
        ),
        CheckConstraint(
            "assets IS NULL OR assets >= 0",
            name="user_welfare_assets_non_negative",
        ),
        CheckConstraint(
            "family_size IS NULL OR (family_size >= 1 AND family_size <= 30)",
            name="user_welfare_family_size_range",
        ),
    )
