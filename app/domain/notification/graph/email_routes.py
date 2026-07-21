from enum import Enum

from langgraph.graph import END

from app.domain.notification.graph.state import NotiState

def email_confirm_route(state: NotiState):
    confirmed = state["confirmed"]
    iter_count = state["iter_count"]

    if confirmed:
        print("이메일 작성이 완료되었습니다. 이메일을 전송합니다.")
        return "send_email_node"

    if iter_count >= 3:
        print("이메일 재작성 횟수가 3회를 초과했습니다.")
        return "send_email_node"

    return "write_email_node"

def no_agreed_users_route(state: NotiState):
    if state["user_emails"]:
        return "write_email_node"
    print("알림 동의 구독자가 없어서 이메일 작성을 건너뜁니다.")
    return END