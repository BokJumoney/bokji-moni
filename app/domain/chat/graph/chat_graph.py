from langgraph.graph import START, StateGraph, END
from app.domain.chat.graph.state import ChatGraphState
from app.domain.chat.graph.subgraph.application_graph import application_graph
from app.domain.chat.graph.nodes.retrieve import retrieve
from app.domain.chat.graph.nodes.generate import generate
from app.domain.chat.graph.nodes.casual_talk import casual_talk
from app.domain.chat.graph.nodes.application_entry import application_entry
from app.domain.chat.graph.subgraph.subscription_graph import subscription_graph
from app.domain.chat.graph.router.unified_router import unified_router
#====메인 그래프. 일반대화와 신청보조를 연결하는 교차로====

# 이 그래프는 ChatGraphState 사용
workflow = StateGraph(ChatGraphState)

# 노드 등록
workflow.add_node("retrieve", retrieve)
workflow.add_node("generate", generate)
workflow.add_node("casual_talk", casual_talk)
workflow.add_node("application_graph", application_graph)
workflow.add_node("application_entry", application_entry)
workflow.add_node("unified_router", unified_router)
workflow.add_node("subscription_graph", subscription_graph)

# 모든 메인 경로는 통합 라우터를 한 번만 거친다. 진행 중인 업무 상태와
# 신규 메시지 의도를 별도 조건 분기로 나누지 않아 라우팅 우선순위를 명확히 한다.
workflow.add_edge(START, "unified_router")
workflow.add_conditional_edges(
    "unified_router",
    lambda state: state["route"],
    {
        "vectorstore":"retrieve",
        "casual_talk":"casual_talk",
        "application":"application_entry",
        "subscription":"subscription_graph",
    }
)
# 추가
workflow.add_edge(
    "application_entry",
    "application_graph"
)

workflow.add_edge("retrieve","generate")
workflow.add_edge("generate",END)
workflow.add_edge("casual_talk",END)
workflow.add_edge("subscription_graph", END)

graph = workflow.compile()
