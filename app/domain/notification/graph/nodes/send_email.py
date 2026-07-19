from app.domain.notification.graph.state import NotiState
from app.domain.notification.temp.sender import get_email_sender

def send_email(state:NotiState):
    names= state["user_names"]
    emails = state["user_emails"]
    email_content = state["content"]

    sender = get_email_sender()

    sender.send(emails[0], "[복지모니]이메일 보내짐", email_content)
