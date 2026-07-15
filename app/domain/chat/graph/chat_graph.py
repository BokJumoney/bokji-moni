from langgraph.graph import START, StateGraph, END
from app.domain.chat.graph.state import ChatGraphState
from app.domain.chat.graph.subgraph.application_graph import application_graph
from app.domain.chat.graph.nodes.retrieve import retrieve
from app.domain.chat.graph.nodes.generate import generate
from app.domain.chat.graph.nodes.casual_talk import casual_talk
from app.domain.chat.graph.router.conversatioin_router import check_conversation_mode
from app.domain.chat.graph.nodes.application_entry import application_entry
from app.domain.chat.graph.nodes.intent_router import intent_router
#====메인 그래프. 일반대화와 신청보조를 연결하는 교차로====


# 이 그래프는 ChatGraphState 사용
workflow = StateGraph(ChatGraphState)
#노드 등록 
workflow.add_node("retrieve", retrieve)
workflow.add_node("generate", generate)
workflow.add_node("casual_talk", casual_talk)
workflow.add_node("application_graph", application_graph)
workflow.add_node("application_entry", application_entry)
workflow.add_node("intent_router",intent_router)
#조건 분기 
workflow.add_conditional_edges(
    START,
    check_conversation_mode,
    {
        "general":"intent_router",
        "application":"application_entry"
    }
)
workflow.add_conditional_edges(
    "intent_router",
    lambda state: state["route"],
    {
        "vectorstore":"retrieve",
        "casual_talk":"casual_talk",
        "application":"application_entry"
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

graph = workflow.compile()