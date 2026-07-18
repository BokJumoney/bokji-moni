from langgraph.graph import StateGraph, START, END

from app.domain.notification.graph.nodes.draft_user import draft_user
from app.domain.notification.graph.nodes.write_email import write_email
from app.domain.notification.graph.nodes.review_email import review_email
from app.domain.notification.graph.nodes.send_email import send_email
from app.domain.notification.graph.state import NotiState


def email_confirm_route(state: NotiState):
    confirmed = state["confirmed"]
    iter_count = state["iter_count"]
    
    if confirmed:
        print("이메일 작성이 완료되었습니다. 이메일을 전송합니다.")
        return "send_email_node"

    if iter_count >= 3:
        print(f"이메일 재작성 횟수가 3회를 초과했습니다.")
        return "send_email_node"

    return "write_email_node"

graph = StateGraph(NotiState)

# graph.add_node("draft_user", draft_user)
graph.add_node("write_email_node", write_email)
graph.add_node("review_email_node", review_email)
graph.add_node("send_email_node", send_email)

# graph.add_edge(START, "draft_user")
# graph.add_edge("draft_user", "write_email_node")
graph.add_edge(START, "write_email_node")# test용
graph.add_edge("write_email_node", "review_email_node")
graph.add_edge("send_email_node", END)

graph.add_conditional_edges(
    "review_email_node",
    email_confirm_route,
    {"write_email_node" : "write_email_node", "send_email_node" : "send_email_node"},
)

noti_app = graph.compile()
