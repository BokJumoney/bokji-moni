"""
Chat Graph State.

기존 state.py에 messages / context 필드가 없다면 아래처럼 병합하세요.
messages는 add_messages 리듀서를 사용해 매 노드 호출마다 리스트에
누적(append)되도록 한다 (information_agent의 AIMessage,
tool_executor의 ToolMessage들이 여기 쌓인다).
"""

from typing import Annotated, TypedDict, NotRequired

from langgraph.graph.message import add_messages

class ChatState(TypedDict):
    question: str                       # 사용자 원문 질문
    intent: str                         # intent_router 결과
    messages: Annotated[list, add_messages]  # Agent/Tool 메시지 누적
    context: list[str]                  # tool_executor가 채우는 근거 텍스트
    answer: str                         # generate.py 최종 응답
    user_id: NotRequired[str]
    user_background: NotRequired[dict]  # UserBackground 테이블 정보
    # 인증된 사용자 식별자다.
    # 요청 body나 LLM 출력이 아니라 ChatService가 직접 주입한다.

    conversation_id: NotRequired[str]
    # 현재 대화방 식별자다.
    # 사용자와 대화방에 종속된 구독 확인 상태를 조회할 때 사용한다.

    chat_history: NotRequired[list[dict[str, str]]]
    # 현재 질문 이전의 대화 이력이다.
    # 각 항목은 {"role": "user|assistant", "content": "..."} 형태다.

