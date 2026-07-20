import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.infrastructure.config import settings

class EmailSender(Protocol):
    def send(self, to: str, subject: str, body: str) -> None:...

class SmtpEmailSender:
    def send(self, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"] = settings.SMTP_SENDER
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_SENDER, settings.SMTP_APP_PASSWORD)
            server.send_message(msg)
        print(f"[SMTP] {to} 에게 발송 완료")

class ConsoleEmailSender:
    def send(self, to: str, subject: str, body: str) -> None:
        print("========== [이메일 발송] ==========")
        print(f"To: {to}")
        print(f"Subject: {subject}")
        print("-" * 40)
        print(body)
        print("=" * 40)


def get_email_sender() -> EmailSender:
    if settings.EMAIL_BACKEND == "smtp":
        return SmtpEmailSender()
    else:
        return ConsoleEmailSender()