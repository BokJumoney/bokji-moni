from langgraph.graph import START, END, StateGraph
from app.domain.chat.graph.router.application_router import application_router
from app.domain.chat.graph.state import ChatGraphState
from app.domain.chat.graph.subgraph.nodes.apply_retrieve import application_retrieve
from app.domain.chat.graph.nodes.retrieve import retrieve
from app.domain.chat.graph.nodes.generate import generate
from .nodes.qualification import qualification
from .nodes.document import document
from .nodes.form_help import form_help


builder = StateGraph(ChatGraphState)

builder.add_node("qualification", qualification)
builder.add_node("document",document)
builder.add_node("form_help", form_help)
builder.add_node(
    "application_retrieve",
    application_retrieve
)
builder.add_node(
    "retrieve",
    retrieve
)
builder.add_node("generate",generate)

builder.add_conditional_edges(
    START,
    application_router,
    {
        "qualification": "qualification",
        "document": "document",
        "form": "form_help",
        "vectorstore": "application_retrieve",   
    }
)

builder.add_edge("qualification", "application_retrieve") # 자격증명은 따로 
builder.add_edge("document", "application_retrieve")
builder.add_edge("form_help", "application_retrieve")
builder.add_edge(
    "application_retrieve",
    "generate"
)
builder.add_edge("generate",END)
application_graph = builder.compile()