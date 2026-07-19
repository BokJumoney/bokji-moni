"""기존 채팅 흐름에 구독 전용 Tool Calling 노드를 연결한 LangGraph 정의.

정보 조회 흐름과 자격 확인의 coming_soon 흐름은 그대로 두고, 기존에
coming_soon으로 향하던 구독 의도만 ``subscription_agent``로 연결한다.
"""

from langgraph.graph import START, StateGraph, END
from app.domain.chat.graph.nodes.generate import generate
from app.domain.chat.graph.nodes.comming_soon import comming_soon
from app.domain.chat.graph.nodes.subscription_agent import subscription_agent
from app.domain.chat.graph.nodes.intent_router import intent_router
from app.domain.chat.graph.router.intent_router import route_by_intent
from app.domain.chat.graph.state2 import ChatState
from app.domain.chat.graph.nodes.information_agent import information_agent
from app.domain.chat.graph.nodes.tool_executor import tool_executor
from app.domain.chat.graph.router.tool_router import tool_router
from app.domain.chat.graph.router.post_tool_router import post_tool_router

# 모든 기존 노드가 공유하던 ChatState 구조는 변경하지 않는다.
graph = StateGraph(ChatState)

graph.add_node("intent_router", intent_router)
graph.add_node("information_agent", information_agent)
graph.add_node("comming_soon", comming_soon)
graph.add_node("subscription_agent", subscription_agent)
graph.add_node("tool_executor", tool_executor)
graph.add_node("generate", generate)
graph.add_edge(START, "intent_router")

# route_by_intent: intent_router 노드가 state["intent"]에 저장해둔 값을
# 그대로 읽어서 반환하는 conditional edge 함수 (LLM 재호출 없음).
graph.add_conditional_edges(
    "intent_router",
    route_by_intent,
    {
        "information_agent": "information_agent",
        # 구독 분기만 실제 에이전트로 교체하고 자격 확인은 기존 placeholder를 유지한다.
        "subscription_agent": "subscription_agent",
        "eligibility_agent": "comming_soon",
    },
)
# --- 여기부터가 "Agent(Tool 선택)" 배선 ---
graph.add_conditional_edges(
    "information_agent",
    tool_router,
    {
        "tool_executor": "tool_executor",
        "generate": "generate",
    },
)
# tool_executor 다음: general_response_tool만 실행됐으면 generate 없이 바로 끝,
# 그 외엔 generate에서 최종 답변을 만든다.
graph.add_conditional_edges(
    "tool_executor",
    post_tool_router,
    {
        "generate": "generate",
        "end": END,
    },
)
# -----------------------------------------------------
graph.add_edge("comming_soon", END)
# 구독 Tool이 최종 사용자 문구까지 반환하므로 generate 노드를 다시 거치지 않는다.
graph.add_edge("subscription_agent", END)
graph.add_edge("generate", END)

graph = graph.compile()
