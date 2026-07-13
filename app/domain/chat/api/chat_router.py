from fastapi import APIRouter
from app.domain.chat.dto.request import ChatMessageRequest
from app.domain.chat.dto.response import ChatMessageResponse
from app.domain.chat.service.chat_service import ChatService, sessions_db

router = APIRouter()
chat_service = ChatService()

@router.post("/message", response_model=ChatMessageResponse)
async def send_message(request: ChatMessageRequest):
    # 현재 인증이 없으므로 임시 user_id 사용
    user_id = "test_user_id"
    response = await chat_service.process_message(
        user_id=user_id,
        message=request.message,
        session_id=request.session_id
    )
    return response

@router.get("/sessions")
async def get_sessions():
    return {"items": []}

@router.get("/sessions/{session_id}/history")
async def get_history(session_id: str):
    messages = sessions_db.get(session_id, [])
    return {"items": messages}

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id in sessions_db:
        del sessions_db[session_id]
    return {"message": "Session deleted"}