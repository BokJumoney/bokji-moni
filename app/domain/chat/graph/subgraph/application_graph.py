from langgraph.graph import START, END, StateGraph
from app.domain.chat.graph.state import ChatGraphState
from app.domain.chat.graph.nodes.retrieve import retrieve
from app.domain.chat.graph.nodes.generate import generate
from .nodes.qualification import qualification
from .nodes.document import document
from .nodes.form_help import form_help
from .nodes.progress import progress
from app.domain.chat.graph.router.application_router import application_router

builder = StateGraph(ChatGraphState)

builder.add_node("qualification", qualification)
builder.add_node("document",document)
builder.add_node("form_help", form_help)
builder.add_node("progress",progress)
builder.add_node("retrieve",retrieve)
builder.add_node("generate",generate)

builder.add_conditional_edges(
    START,
    application_router,
    {
        "qualification": "qualification",
        "document": "document",
        "form": "form_help",
        "vectorstore": "retrieve",   # 수정
    }
)

builder.add_edge("qualification",END)
builder.add_edge("document",END)
builder.add_edge("form_help",END)
builder.add_edge("progress",END)
builder.add_edge("retrieve","generate")
builder.add_edge("generate",END)
application_graph = builder.compile()