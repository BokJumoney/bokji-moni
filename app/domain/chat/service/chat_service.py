import uuid
from typing import Optional

from app.domain.chat.dto.response import ChatMessageResponse
from app.domain.chat.graph.chat_graph import graph


# 인메모리 세션 저장소 (임시)
# {
#   session_id: {
#       "history": [],
#       "conversation_mode": "",
#       "current_step": "",
#       "application_info": {}
#   }
# }
sessions_db = {}


class ChatService:

    async def process_message(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str]
    ) -> ChatMessageResponse:

        # 1. 세션 생성
        if not session_id or session_id not in sessions_db:

            session_id = str(uuid.uuid4())

            sessions_db[session_id] = {
                "history": [],
                "conversation_mode": "",
                "current_step": "",
                "application_info": {}
            }


        session = sessions_db[session_id]


        # 2. 사용자 메시지 저장
        session["history"].append(
            {
                "role": "user",
                "content": message
            }
        )


        # 현재 질문 제외한 이전 대화
        chat_history = session["history"][:-1]


        try:

            # 3. LangGraph 실행
            result = await graph.ainvoke(
                {
                    "question": message,
                    "chat_history": chat_history,

                    # RAG
                    "documents": [],
                    "generation": "",

                    # 상태 전달
                    "conversation_mode": session["conversation_mode"],
                    "current_step": session["current_step"],
                    "application_info": session["application_info"],
                }
            )


            ai_content = result.get("generation", "")


            # 4. LangGraph 상태 업데이트
            session["conversation_mode"] = result.get(
                "conversation_mode",
                session["conversation_mode"]
            )

            session["current_step"] = result.get(
                "current_step",
                session["current_step"]
            )

            session["application_info"] = result.get(
                "application_info",
                session["application_info"]
            )


            # 5. AI 응답 저장
            session["history"].append(
                {
                    "role": "assistant",
                    "content": ai_content
                }
            )


            return ChatMessageResponse(
                response=ai_content,
                session_id=session_id,
                intent="General"
            )


        except Exception as e:

            error_msg = f"AI 모델 오류: {str(e)}"


            session["history"].append(
                {
                    "role": "assistant",
                    "content": error_msg
                }
            )


            return ChatMessageResponse(
                response=error_msg,
                session_id=session_id,
            )