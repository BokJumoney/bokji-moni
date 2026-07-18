"""
참고용 배선(wiring) 예시.

기존 chat_graph.py에 이미 intent_router / casual_talk / generate 노드가
연결되어 있을 것이므로, 이 파일을 통째로 덮어쓰지 말고 아래 "추가되는
부분"만 기존 그래프에 병합하세요.

핵심 흐름:
  intent_router
      ├─ (일반 대화)      -> casual_talk -> END
      └─ (정책/자격 문의)  -> information_agent (Tool 선택 Agent)
                                  -> tool_router (conditional)
                                       ├─ tool_executor
                                       │      -> post_tool_router (conditional)
                                       │           ├─ generate -> END
                                       │           │   (policy_search_tool / web_search_tool)
                                       │           └─ END
                                       │               (general_response_tool: 이미 answer 확정됨)
                                       └─ generate -> END   (예외: tool_call 없음)
"""

from langgraph.graph import StateGraph, START, END

from app.domain.chat.graph.state2 import ChatState
from app.domain.chat.graph.nodes.intent_router import intent_router
from app.domain.chat.graph.nodes.casual_talk import casual_talk
from app.domain.chat.graph.nodes.information_agent import information_agent
from app.domain.chat.graph.nodes.tool_executor import tool_executor
from app.domain.chat.graph.nodes.generate import generate
from app.domain.chat.graph.router.intent_router import route_by_intent
from app.domain.chat.graph.router.tool_router import tool_router
from app.domain.chat.graph.router.post_tool_router import post_tool_router


def build_chat_graph():
    graph = StateGraph(ChatState)

    graph.add_node("intent_router", intent_router)
    graph.add_node("casual_talk", casual_talk)
    graph.add_node("information_agent", information_agent)
    graph.add_node("tool_executor", tool_executor)
    graph.add_node("generate", generate)

    graph.add_edge(START, "intent_router")

    # route_by_intent: intent_router.py의 결과("casual_talk" | "information_agent")를
    # 그대로 반환하는 기존 conditional edge 함수라고 가정.
    graph.add_conditional_edges(
        "intent_router",
        route_by_intent,
        {
            "casual_talk": "casual_talk",
            "information_agent": "information_agent",
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
    graph.add_edge("generate", END)

    return graph.compile()
