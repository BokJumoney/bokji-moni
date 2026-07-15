"""
채팅 영속 모델.

- Conversation: 사용자 소유 채팅방. 목록 조회용 요약 필드 포함.
- Message: 채팅방 메시지. (conversation_id, created_at, id) 인덱스로 순서 안정화.

설계 규칙(설계명세서 5장 참고):
- session_id 는 conversations.id 의 문자열 직렬화 값이다.
- user_id 는 서버가 설정하며 요청 body에서 받지 않는다.
- message_count >= 0 check 제약.
- conversation 삭제 시 message cascade delete.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Index
from sqlmodel import Field, SQLModel

from app.common.timezone import now_kst


def _utcnow() -> datetime:
    return now_kst()


class Conversation(SQLModel, table=True):
    """사용자 소유 채팅방."""

    __tablename__ = "conversations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    title: str = Field(max_length=80, nullable=False)
    last_message_preview: str = Field(
        nullable=False, default=""
    )
    message_count: int = Field(default=0, nullable=False)
    created_at: datetime = Field(default_factory=_utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=_utcnow, nullable=False)
    last_message_at: datetime = Field(default_factory=_utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("message_count >= 0", name="ck_conversations_message_count"),
        Index(
            "ix_conversations_user_activity",
            "user_id",
            "last_message_at",
            "id",
            postgresql_using="btree",
        ),
    )


class Message(SQLModel, table=True):
    """채팅방 메시지."""

    __tablename__ = "messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_id: uuid.UUID = Field(
        foreign_key="conversations.id",
        nullable=False,
        ondelete="CASCADE",
        index=True,
    )
    role: str = Field(max_length=20, nullable=False)
    content: str = Field(nullable=False)
    intent: Optional[str] = Field(default=None, max_length=50)
    created_at: datetime = Field(default_factory=_utcnow, nullable=False)

    __table_args__ = (
        Index(
            "ix_messages_conversation_created",
            "conversation_id",
            "created_at",
            "id",
        ),
    )