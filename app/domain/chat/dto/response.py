"""
채팅 응답 DTO.

- ChatMessageResponse: 메시지 전송 응답
- ConversationMessage: 이력 조회 항목
- ChatSessionListItem / ChatSessionListResponse: 채팅방 목록 (cursor pagination)
"""
from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatFileResponse(BaseModel):
    fileId: str
    originalFilename: str
    downloadUrl: str


class ChatMessageResponse(BaseModel):
    response: str
    session_id: str
    intent: str = ""
    user_info_updated: bool = False
    needs_followup: bool = False
    sources: Optional[List[Dict]] = None
    files: List[ChatFileResponse] = Field(default_factory=list)


class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime
    intent: Optional[str] = None


class ChatSessionListItem(BaseModel):
    session_id: UUID
    title: str
    last_message_preview: str
    message_count: int
    created_at: datetime
    last_message_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionListResponse(BaseModel):
    items: List[ChatSessionListItem]
    next_cursor: Optional[str]
    has_more: bool


# 하위 호환용 alias (기존 SessionSummary 참조용)
class SessionSummary(ChatSessionListItem):
    pass
