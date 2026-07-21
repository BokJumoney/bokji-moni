from langgraph.graph import StateGraph, START, END

from app.domain.notification.graph.email_routes import email_confirm_route
from app.domain.notification.graph.nodes.write_email import write_email
from app.domain.notification.graph.nodes.review_email import review_email
from app.domain.notification.graph.nodes.send_email import send_email
from app.domain.notification.graph.state import NotiState


graph = StateGraph(NotiState)

graph.add_node("write_email_node", write_email)
graph.add_node("review_email_node", review_email)
graph.add_node("send_email_node", send_email)

graph.add_edge(START, "write_email_node")
graph.add_edge("write_email_node", "review_email_node")
graph.add_edge("send_email_node", END)

graph.add_conditional_edges(
    "review_email_node",
    email_confirm_route,
    {"write_email_node": "write_email_node", "send_email_node": "send_email_node"},
)

indv_noti_app = graph.compile()
