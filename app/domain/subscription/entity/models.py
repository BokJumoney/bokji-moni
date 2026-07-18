"""기존 사용자·정책 엔티티를 변경하지 않는 구독 전용 SQLModel.

구독 기능은 기존 테이블에 컬럼이나 relationship을 추가하지 않고, 아래 두
신규 테이블만으로 사용자 설정과 정책 구독을 관리한다. 기존 도메인과의 연결은
신규 테이블 쪽의 FK(`users.id`) 선언만 사용하므로 기존 엔티티 소스는
수정할 필요가 없다.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Column, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, SQLModel

from app.common.timezone import now_kst


class SubscriptionSettings(SQLModel, table=True):
    """사용자별 정책 소식과 전체 알림 설정.

    ``user_id`` 자체를 PK로 사용해 사용자당 설정 행이 최대 한 개라는 규칙을
    DB에서도 보장한다. 설정 행은 최초 조회 또는 변경 시 지연 생성된다.
    """

    __tablename__ = "subscription_settings"

    # users 테이블을 수정하지 않고 FK만 연결한다. 사용자 삭제 시 개인 설정도
    # 남지 않도록 DB의 ON DELETE CASCADE에 정리를 위임한다.
    user_id: uuid.UUID = Field(
        sa_column=Column(
            "user_id",
            UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    # 두 값은 독립적이다. is_paused는 저장된 수신 동의를 바꾸지 않고 실제
    # 알림 전달만 잠시 막는 상위 스위치로 사용한다.
    # 이 기본값은 SQLModel 객체 생성 기본값이며 DB server_default는 아니다.
    policy_news_enabled: bool = Field(default=True, nullable=False)
    is_paused: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=now_kst, nullable=False)
    updated_at: datetime = Field(default_factory=now_kst, nullable=False)


class PolicySubscription(SQLModel, table=True):
    """사용자가 마감 알림을 구독한 정책의 스냅샷.

    기존 ``welfare_policies``는 정책 하나가 여러 청크 행으로 저장되어
    ``service_id``가 유일하지 않다. 따라서 그 행을 FK로 참조하지 않고,
    프런트 표시에 필요한 정책 ID·이름·마감일을 구독 시점에 복사해 보존한다.
    """

    __tablename__ = "policy_subscriptions"

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
            name="uq_policy_subscriptions_user_service",
        ),
        # 사용자별 목록의 created_at DESC, id DESC 조회를 지원한다.
        Index(
            "ix_policy_subscriptions_user_created",
            "user_id",
            "created_at",
            "id",
        ),
    )
