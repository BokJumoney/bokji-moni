from app.domain.notification.graph.state import NotiState
from app.infrastructure.email.email_sender import get_email_sender

def send_email(state:NotiState):
    names= state["user_names"]
    emails = state["user_emails"]
    email_title = state["title"]
    email_content = state["content"]

    sender = get_email_sender()


    for email, name in zip(emails, names):
        try:
            personal_email = name + "님, " + email_content
            sender.send(email, email_title, personal_email)
        except Exception as e:
            print(f"{email} 발송 실패. {e}")


