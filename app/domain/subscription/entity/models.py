"""사용자별 개별 정책 구독을 저장하는 SQLModel."""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Column, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, SQLModel

from app.common.timezone import now_kst


class PolicySubscription(SQLModel, table=True):
    """사용자가 마감 알림을 구독한 정책의 스냅샷.

    기존 ``welfare_policies``는 정책 하나가 여러 청크 행으로 저장되어
    ``service_id``가 유일하지 않다. 따라서 그 행을 FK로 참조하지 않고,
    프런트 표시에 필요한 정책 ID·이름·마감일을 구독 시점에 복사해 보존한다.
    """

    __tablename__ = "subscription_settings"

    # 프런트가 안정적인 숫자 key로 사용할 수 있도록 자동 증가 PK를 둔다.
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column(
            "user_id",
            UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    # 정책 원본이 갱신되거나 청크가 재적재되어도 구독 목록을 표시할 수 있는
    # 최소 스냅샷이다.
    service_id: str = Field(max_length=100, nullable=False)
    service_name: str = Field(max_length=255, nullable=False)
    # 현재 정책 원본에 구조화된 마감일이 없을 수 있으므로 nullable이다.
    # 값이 있으면 API에서 YYYY-MM-DD로 직렬화된다.
    application_deadline: Optional[date] = Field(default=None)
    created_at: datetime = Field(default_factory=now_kst, nullable=False)

    __table_args__ = (
        # 같은 사용자가 같은 정책을 중복 구독하지 못하게 한다. 서로 다른
        # 사용자는 동일 service_id를 각각 구독할 수 있다.
        UniqueConstraint(
            "user_id",
            "service_id",
            name="uq_subscription_settings_user_service",
        ),
        # 사용자별 목록의 created_at DESC, id DESC 조회를 지원한다.
        Index(
            "ix_subscription_settings_user_created",
            "user_id",
            "created_at",
            "id",
        ),
    )
