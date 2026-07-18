"""
Chat Graph State.

기존 state.py에 messages / context 필드가 없다면 아래처럼 병합하세요.
messages는 add_messages 리듀서를 사용해 매 노드 호출마다 리스트에
누적(append)되도록 한다 (information_agent의 AIMessage,
tool_executor의 ToolMessage들이 여기 쌓인다).
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    question: str                       # 사용자 원문 질문
    intent: str                         # intent_router 결과
    messages: Annotated[list, add_messages]  # Agent/Tool 메시지 누적
    context: list[str]                  # tool_executor가 채우는 근거 텍스트
    answer: str                         # generate.py 최종 응답
    files: list[dict[str, str]]         # 신청서 다운로드 메타데이터
    user_id: int
