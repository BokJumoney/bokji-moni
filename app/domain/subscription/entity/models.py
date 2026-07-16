"""정책 구독, 알림 설정, 채팅 구독 진행 상태 SQLModel 엔티티."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.common.timezone import now_kst


class PolicySubscription(SQLModel, table=True):
    """사용자가 특정 정책의 마감 알림을 받겠다는 선택을 저장한다.

    행을 삭제하지 않고 status를 바꾸는 이유는 사용자 해지(cancelled)와
    정책 폐지(ended)를 구분하고, 이후 재구독 시 기존 행을 재활성화하기 위해서다.
    """

    __tablename__ = "policy_subscriptions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, index=True, ondelete="CASCADE"
    )
    policy_id: int = Field(
        foreign_key="welfare_policies.id", nullable=False, index=True
    )
    status: str = Field(default="active", max_length=20, nullable=False, index=True)
    created_at: datetime = Field(default_factory=now_kst, nullable=False)
    updated_at: datetime = Field(default_factory=now_kst, nullable=False)
    cancelled_at: Optional[datetime] = Field(default=None)

    __table_args__ = (
        UniqueConstraint("user_id", "policy_id", name="uq_subscription_user_policy"),
    )


class NotificationSettings(SQLModel, table=True):
    """사용자별 공통 알림 설정.

    개별 정책 구독과 전체 정책 소식 수신 여부는 성격이 다르므로 사용자
    테이블에 컬럼을 계속 추가하지 않고 별도 1:1 테이블로 관리한다.
    """

    __tablename__ = "notification_settings"

    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        primary_key=True,
        ondelete="CASCADE",
    )
    policy_news_enabled: bool = Field(default=False, nullable=False)
    is_paused: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=now_kst, nullable=False)
    updated_at: datetime = Field(default_factory=now_kst, nullable=False)


class SubscriptionDialog(SQLModel, table=True):
    """여러 채팅 요청에 걸친 구독 선택/확인 상태를 저장한다.

    사용자가 다음 메시지에서 단순히 "2번" 또는 "네"라고 답하더라도 이전
    후보와 단계가 보존되어야 한다. LLM이 채팅 기록만 보고 상태를 추측하지
    않도록 서버가 명시적인 상태를 저장한다.
    """

    __tablename__ = "subscription_dialogs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_id: uuid.UUID = Field(
        foreign_key="conversations.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, index=True, ondelete="CASCADE"
    )
    action: str = Field(max_length=30, nullable=False)
    stage: str = Field(max_length=30, nullable=False, index=True)
    policy_query: Optional[str] = Field(default=None, max_length=300)
    candidate_policy_ids: list[int] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    selected_policy_id: Optional[int] = Field(
        default=None, foreign_key="welfare_policies.id"
    )
    expires_at: datetime = Field(nullable=False, index=True)
    created_at: datetime = Field(default_factory=now_kst, nullable=False)
    updated_at: datetime = Field(default_factory=now_kst, nullable=False)
