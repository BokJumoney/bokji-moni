"""
채팅 API 라우터.

- POST /api/v1/chat/message        : 메시지 전송 (async, LangGraph 호출)
- GET  /api/v1/chat/sessions       : 채팅방 목록 (cursor pagination)
- GET  /api/v1/chat/sessions/{id}/history : 이력 조회
- DELETE /api/v1/chat/sessions/{id}        : 채팅방 삭제

목록/이력/삭제 endpoint 는 동기 def 로 두어 FastAPI threadpool 에서
동기 DB I/O 를 실행한다.
"""
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlmodel import Session

from app.common.exceptions import AuthError, ChatError
from app.domain.chat.dto.request import ChatMessageRequest
from app.domain.chat.dto.response import (
    ChatMessageResponse,
    ChatSessionListResponse,
    ConversationMessage,
)
from app.domain.chat.service.chat_service import ChatService
from app.domain.user.dependencies import get_current_user
from app.domain.user.entity.models import User
from app.infrastructure.db.connection import get_session

router = APIRouter()


def _chat_error_to_http(exc: ChatError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


def _auth_error_to_http(exc: AuthError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatMessageResponse:
    service = ChatService(session)
    try:
        return await service.process_message(
            user_id=current_user.id,
            message=request.message,
            session_id=request.session_id,
        )
    except ChatError as exc:
        raise _chat_error_to_http(exc) from exc
    except AuthError as exc:
        raise _auth_error_to_http(exc) from exc


@router.get(
    "/sessions",
    response_model=ChatSessionListResponse,
    summary="채팅방 목록 조회",
)
def get_sessions(
    response: Response,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Optional[str] = Query(default=None, description="opaque cursor"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatSessionListResponse:
    response.headers["Cache-Control"] = "private, no-store"
    service = ChatService(session)
    try:
        return service.list_sessions(
            user_id=current_user.id, cursor=cursor, limit=limit
        )
    except ChatError as exc:
        raise _chat_error_to_http(exc) from exc


@router.get(
    "/sessions/{session_id}/history",
    summary="채팅방 이력 조회",
)
def get_history(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = ChatService(session)
    try:
        items = service.get_history(session_id, current_user.id)
    except ChatError as exc:
        raise _chat_error_to_http(exc) from exc
    return {"items": items}


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="채팅방 삭제",
)
def delete_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = ChatService(session)
    try:
        service.delete_session(session_id, current_user.id)
    except ChatError as exc:
        raise _chat_error_to_http(exc) from exc
    return None