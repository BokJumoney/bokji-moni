"""
채팅 서비스 (DB 영속화 기반).

- process_message: 새 채팅방 생성 / 기존 채팅방 소유권 확인, 메시지 저장, LangGraph 호출
- list_sessions: cursor pagination, DTO 변환
- get_history / delete_session: 소유권 기반 DB 조회/삭제

DB는 동기 SQLModel 이며 message endpoint는 async 이므로
DB 호출은 starlette run_in_threadpool 경계에서 실행한다.
"""
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session

from app.common.exceptions import ChatSessionNotFoundError
from app.domain.chat.dto.response import (
    ChatMessageResponse,
    ChatSessionListItem,
    ChatSessionListResponse,
    ConversationMessage,
)
from app.domain.chat.entity.models import Message
from app.domain.chat.graph.chat_graph import graph
from app.domain.chat.repository import ConversationRepository
from app.domain.chat.utils import (
    decode_cursor,
    encode_cursor,
    normalize_title,
)
from app.domain.user.repository import UserRepository
logger = logging.getLogger(__name__)


class ChatService:
    """채팅 비즈니스 로직 오케스트레이션."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = ConversationRepository(session)
        self.user_repo = UserRepository(session)

    # -- message ------------------------------------------------------------
    async def process_message(
        self,
        user_id,
        message: str,
        session_id: Optional[uuid.UUID] = None,
    ) -> ChatMessageResponse:
        """사용자 메시지 → 채팅방 확보 → 저장 → LangGraph → AI 응답 저장."""

        # 3.5. 유저 정보 + 백그라운드 조회 (같은 user_id, 다른 테이블)
        user, user_background = await run_in_threadpool(
            self._load_user_context, user_id
        )
        # 1. 채팅방 확보 (동기 DB 호출은 threadpool 에서)
        if session_id is None:
            conversation = await run_in_threadpool(
                self.repo.create_conversation,
                user_id,
                normalize_title(message),
            )
        else:
            conversation = await run_in_threadpool(
                self.repo.get_conversation, session_id, user_id
            )
            if conversation is None:
                raise ChatSessionNotFoundError()

        # 2. 사용자 메시지 저장 (commit)
        await run_in_threadpool(
            self.repo.add_message, conversation, "user", message
        )

        # 3. DB에서 최근 이력 조회 (방금 저장한 메시지 제외 최근 N)
        history = await run_in_threadpool(
            self._load_history_for_graph, conversation.id, user_id
        )
        # 방금 저장한 user message 는 마지막 항목이므로 제외
        chat_history = [
            {"role": m.role, "content": m.content} for m in history[:-1]
        ]

        user_info = {"name": user.name, "email": user.email} if user else None
        background = (
            {
                "income": user_background.income,
                "age": user_background.age,
                "family_size": user_background.family_size,
                "disability": user_background.disability,
                "assets": user_background.assets,
                "employment_stat": user_background.employment_stat,
            }
            if user_background
            else None
        )

        # 4. LangGraph 호출 (DB transaction 밖에서)
        try:
            result = await graph.ainvoke(
                {
                    "question": message,
                    "user_info": user_info,
                    "user_id": user_id,
                    "user_background": background,
                    "chat_history": chat_history,
                },
                config={
                    "configurable": {
                    "user_id": str(user_id),
                    }
                },
            )
            ai_content = result.get("answer", "")
            intent = result.get("intent", "General")
            files = result.get("files", [])
        except Exception as exc:  # noqa: BLE001
            logger.exception("LangGraph 호출 실패: conversation_id=%s", conversation.id)
            # 안전한 오류 메시지 저장 (원문 노출 금지)
            ai_content = "죄송합니다. 답변을 생성하는 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."
            intent = "Error"
            files = []

        # 5. AI 응답 저장 (별도 짧은 transaction)
        await run_in_threadpool(
            self.repo.add_message, conversation, "assistant", ai_content, intent
        )

        return ChatMessageResponse(
            response=ai_content,
            session_id=str(conversation.id),
            intent=intent,
            files=files,
        )

    def _load_user_context(self, user_id):
        user = self.user_repo.get_by_id(user_id)
        background = self.user_repo.get_user_background(user_id)
        return user, background

    def _load_history_for_graph(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[Message]:
        return self.repo.list_messages(conversation_id, user_id)

    # -- list ---------------------------------------------------------------
    def list_sessions(
        self,
        user_id,
        cursor: Optional[str] = None,
        limit: int = 20,
    ) -> ChatSessionListResponse:
        """cursor 기반 목록 조회 (limit+1 규칙)."""
        cursor_time: Optional[datetime] = None
        cursor_id: Optional[uuid.UUID] = None
        if cursor:
            cursor_time, cursor_id = decode_cursor(cursor)

        # limit+1 로 조회해 has_more 판단
        rows = self.repo.list_conversations(
            user_id,
            limit_plus_one=limit + 1,
            cursor_time=cursor_time,
            cursor_id=cursor_id,
        )
        has_more = len(rows) > limit
        page = rows[:limit]

        next_cursor: Optional[str] = None
        if has_more and page:
            last = page[-1]
            next_cursor = encode_cursor(last.last_message_at, last.id)

        items = [
            ChatSessionListItem(
                session_id=c.id,
                title=c.title,
                last_message_preview=c.last_message_preview,
                message_count=c.message_count,
                created_at=c.created_at,
                last_message_at=c.last_message_at,
            )
            for c in page
        ]
        return ChatSessionListResponse(
            items=items, next_cursor=next_cursor, has_more=has_more
        )

    # -- history / delete (기존 endpoint 통합) ------------------------------
    def get_history(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[ConversationMessage]:
        messages = self.repo.list_messages(conversation_id, user_id)
        if not messages:
            # 소유권 위반 또는 빈 방 → 404 (빈 방이더라도 존재 확인)
            convo = self.repo.get_conversation(conversation_id, user_id)
            if convo is None:
                raise ChatSessionNotFoundError()
        return [
            ConversationMessage(
                role=m.role,
                content=m.content,
                timestamp=m.created_at,
                intent=m.intent,
            )
            for m in messages
        ]

    def delete_session(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        deleted = self.repo.delete_conversation(conversation_id, user_id)
        if not deleted:
            raise ChatSessionNotFoundError()
