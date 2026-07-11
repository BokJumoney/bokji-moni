import uuid
from typing import Optional
from app.domain.chat.dto.response import ChatMessageResponse
from app.domain.chat.graph.chat_graph import graph

# 인메모리 세션 저장소 (임시)
sessions_db = {}

class ChatService:
    async def process_message(self, user_id: str, message: str, session_id: Optional[str]) -> ChatMessageResponse:
        # 1. 세션 처리
        if not session_id or session_id not in sessions_db:
            session_id = str(uuid.uuid4())
            sessions_db[session_id] = []

        # 2. 대화 기록에 추가
        sessions_db[session_id].append({"role": "user", "content": message})

        chat_history = sessions_db[session_id][:-1]

        # 3. LangGraph 호출
        try:
            result = await graph.ainvoke({
                "question": message,
                "chat_history": chat_history,
                "documents": [],
                "generation": "",
            })

            ai_content = result.get("generation", "")

            # 4. AI 응답 추가
            sessions_db[session_id].append({"role": "assistant", "content": ai_content})

            return ChatMessageResponse(
                response=ai_content,
                session_id=session_id,
                intent="General"
            )
        except Exception as e:
            error_msg = f"AI 모델 오류: {str(e)}"
            sessions_db[session_id].append({"role": "assistant", "content": error_msg})
            return ChatMessageResponse(
                response=error_msg,
                session_id=session_id,
            )