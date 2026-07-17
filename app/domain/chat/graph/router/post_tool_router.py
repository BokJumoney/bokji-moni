"""
tool_executor 다음의 conditional edge.

general_response_tool만 호출된 경우 tool_executor가 이미 state["answer"]를
채워둔다(고정 안내 문구를 그대로 최종 답변으로 씀). 이 경우 generate(LLM
재작성)를 건너뛰고 바로 끝낸다.

그 외(policy_search_tool, web_search_tool 등 실제 검색이 필요했던 경우)는
generate에서 검색 결과를 바탕으로 자연어 답변을 새로 만든다.
"""

from app.domain.chat.graph.state2 import ChatState


def post_tool_router(state: ChatState) -> str:
    if state.get("answer"):
        return "end"

    return "generate"
