"""
채팅 도메인 순수 함수.

- 제목/미리보기 정규화 (설계명세서 6장)
- cursor encode/decode (설계명세서 7.3)

이 모듈은 DB/네트워크에 의존하지 않는 순수 함수만 포함한다.
"""
from __future__ import annotations

import base64
import re
import uuid
from datetime import datetime

from app.common.exceptions import InvalidCursorError
from app.common.timezone import KST

_TITLE_MAX = 40
_PREVIEW_MAX = 200

_WS_RE = re.compile(r"\s+")


def normalize_title(first_message: str) -> str:
    """첫 사용자 메시지를 채팅방 제목으로 변환한다.

    1. 앞뒤 공백 제거
    2. 연속된 공백/줄바꿈을 한 칸으로
    3. 40자 이내로 자르고 초과 시 '…' 추가
    """
    trimmed = _WS_RE.sub(" ", first_message.strip())
    if len(trimmed) <= _TITLE_MAX:
        return trimmed
    return trimmed[:_TITLE_MAX].rstrip() + "…"


def normalize_preview(content: str) -> str:
    """메시지 본문을 목록 미리보기(200자 이내)로 정규화한다."""
    trimmed = _WS_RE.sub(" ", content.strip())
    if len(trimmed) <= _PREVIEW_MAX:
        return trimmed
    return trimmed[:_PREVIEW_MAX].rstrip() + "…"


def encode_cursor(last_message_at: datetime, conversation_id: uuid.UUID) -> str:
    """커서 = base64url('ISO8601|uuid') opaque string."""
    # KST ISO 8601 (+09:00 접미사 보장)
    ts = last_message_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=KST)
    ts_iso = ts.astimezone(KST).strftime("%Y-%m-%dT%H:%M:%S.%f+09:00")
    raw = f"{ts_iso}|{conversation_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """커서를 (last_message_at, id) 로 디코딩한다. 실패 시 InvalidCursorError."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        raise InvalidCursorError() from exc
    if "|" not in raw:
        raise InvalidCursorError()
    ts_part, id_part = raw.rsplit("|", 1)
    try:
        ts = datetime.fromisoformat(ts_part)
    except ValueError as exc:
        raise InvalidCursorError() from exc
    # DB 컬럼이 naive KST 이므로 cursor 도 naive 로 통일
    if ts.tzinfo is not None:
        ts = ts.astimezone(KST).replace(tzinfo=None)
    try:
        cid = uuid.UUID(id_part)
    except ValueError as exc:
        raise InvalidCursorError() from exc
    return ts, cid