from langgraph.graph import START, StateGraph, END
from app.domain.chat.graph.nodes.generate import generate
from app.domain.chat.graph.nodes.comming_soon import comming_soon
from app.domain.chat.graph.nodes.intent_router import intent_router   # ← 추가: LLM 부르고 intent 채우는 진짜 노드
from app.domain.chat.graph.router.intent_router import route_by_intent
from app.domain.chat.graph.state2 import ChatState
from app.domain.chat.graph.nodes.information_agent import information_agent
from app.domain.chat.graph.nodes.tool_executor import tool_executor
from app.domain.chat.graph.router.tool_router import tool_router
from app.domain.chat.graph.router.post_tool_router import post_tool_router

# 이 그래프는 ChatState 사용
graph = StateGraph(ChatState)

graph.add_node("intent_router", intent_router)   # ← 수정: route_by_intent가 아니라 intent_router
graph.add_node("information_agent", information_agent)
graph.add_node("comming_soon", comming_soon)
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
        "subscription_agent": "comming_soon",
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
graph.add_edge("generate", END)

graph = graph.compile()