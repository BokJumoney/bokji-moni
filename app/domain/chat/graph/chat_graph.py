from langgraph.graph import START, StateGraph, END

from app.domain.chat.graph.state import GraphState
from app.domain.chat.graph.router import route_question
from app.domain.chat.graph.nodes import retrieve, grade_documents, generate, casual_talk

workflow = StateGraph(GraphState)

workflow.add_node("retrieve", retrieve)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("generate", generate)
workflow.add_node("casual_talk", casual_talk)

workflow.add_conditional_edges(
    START,
    route_question,
    {
        "vectorstore": "retrieve",
        "casual_talk": "casual_talk",
    },
)
workflow.add_edge("casual_talk", END)
workflow.add_edge("retrieve", "grade_documents")
workflow.add_edge("grade_documents", "generate")
workflow.add_edge("generate", END)

graph = workflow.compile()