"""information_agent가 profile_required_guard로 조기 종료했으면 tool_router를 건너뛰고 바로 끝낸다."""
from app.domain.chat.graph.router.tool_router import tool_router
from app.domain.chat.graph.state2 import ChatState


def tool_router_with_guard(state: ChatState) -> str:
    if state.get("answer"):
        return "end"
    return tool_router(state)