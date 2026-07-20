"""
information_agent 다음의 conditional edge.

information_agent가 만든 AIMessage에 tool_calls가 있으면 tool_executor로,
(모델이 도구 호출을 만들지 못한 예외 상황이면) generate로 바로 보낸다.
"""
from app.domain.chat.graph.state2 import ChatState


def tool_router(state: ChatState) -> str:
    last_message = state["messages"][-1]

    if not getattr(last_message, "tool_calls", None):
        return "generate"

    return "tool_executor"
