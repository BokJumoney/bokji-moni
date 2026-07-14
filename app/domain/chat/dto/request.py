"""
채팅 요청 DTO.

- message: 공백-only 거부, 최소/최대 길이 검사
- session_id: UUID | None (빈 문자열은 None 으로 정규화)
"""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: Optional[UUID] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("message")
    @classmethod
    def _reject_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("메시지는 공백만으로 구성될 수 없습니다.")
        return v