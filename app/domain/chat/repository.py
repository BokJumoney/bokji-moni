"""
채팅 리포지토리 (SQLModel 기반).

책임:
- 사용자 소유 채팅방 생성/조회/삭제
- 메시지 저장 + conversation summary 갱신 (동일 transaction)
- cursor 조건 기반 목록 조회 (limit+1 규칙)
- history 조회용 소유권 조건 message 조회

모든 conversation 관련 메서드는 user_id 를 필수 인자로 받아
DB query 자체에 소유권 조건을 넣는다.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlmodel import Session, select

from app.common.timezone import now_kst
from app.domain.chat.entity.models import Conversation, Message


class ConversationRepository:
    """conversations + messages DB 접근."""

    def __init__(self, session: Session):
        self.session = session

    # -- conversation -------------------------------------------------------
    def create_conversation(
        self,
        user_id: uuid.UUID,
        title: str,
        now: Optional[datetime] = None,
    ) -> Conversation:
        now = now or now_kst()
        conversation = Conversation(
            user_id=user_id,
            title=title,
            created_at=now,
            updated_at=now,
            last_message_at=now,
        )
        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)
        return conversation

    def get_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Conversation]:
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        return self.session.exec(stmt).first()

    def list_conversations(
        self,
        user_id: uuid.UUID,
        limit_plus_one: int,
        cursor_time: Optional[datetime] = None,
        cursor_id: Optional[uuid.UUID] = None,
    ) -> list[Conversation]:
        """(user_id, last_message_at DESC, id DESC) 정렬의 커서 기반 목록."""
        stmt = select(Conversation).where(Conversation.user_id == user_id)
        if cursor_time is not None and cursor_id is not None:
            stmt = stmt.where(
                text(
                    "(conversations.last_message_at, conversations.id) "
                    "< (:cursor_time, :cursor_id)"
                )
            ).params(cursor_time=cursor_time, cursor_id=cursor_id)
        stmt = stmt.order_by(
            Conversation.last_message_at.desc(),
            Conversation.id.desc(),
        ).limit(limit_plus_one)
        return list(self.session.exec(stmt).all())

    def delete_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        convo = self.get_conversation(conversation_id, user_id)
        if convo is None:
            return False
        self.session.delete(convo)
        self.session.commit()
        return True

    # -- message ------------------------------------------------------------
    def add_message(
        self,
        conversation: Conversation,
        role: str,
        content: str,
        intent: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> Message:
        """메시지 저장 + conversation summary 갱신을 한 transaction으로 수행."""
        now = now or now_kst()
        message = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
            intent=intent,
            created_at=now,
        )
        self.session.add(message)

        from app.domain.chat.utils import normalize_preview

        # atomic increment + summary 갱신
        conversation.message_count = conversation.message_count + 1
        conversation.last_message_preview = normalize_preview(content)
        conversation.last_message_at = now
        conversation.updated_at = now
        self.session.add(conversation)

        self.session.commit()
        self.session.refresh(conversation)
        self.session.refresh(message)
        return message

    def list_messages(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[Message]:
        """소유권 조건으로 message 목록을 (created_at, id) ASC 순으로."""
        # conversation 소유권 먼저 확인
        convo = self.get_conversation(conversation_id, user_id)
        if convo is None:
            return []
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        return list(self.session.exec(stmt).all())