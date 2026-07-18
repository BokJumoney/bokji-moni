from typing import Protocol


class EmailSender(Protocol):
    """이메일 발송 인터페이스. send()만 맞추면 어떤 구현이든 교체 가능."""
    def send(self, to: str, subject: str, body: str) -> None: ...


class ConsoleEmailSender:
    """개발용: 실제 발송 대신 터미널에 출력."""
    def send(self, to: str, subject: str, body: str) -> None:
        print("========== [이메일 발송 (콘솔 모킹)] ==========")
        print(f"To: {to}")
        print(f"Subject: {subject}")
        print("-" * 40)
        print(body)
        print("=" * 46)


def get_email_sender() -> EmailSender:
    # 나중에 settings.EMAIL_BACKEND == "smtp" 분기로 SmtpEmailSender 리턴
    return ConsoleEmailSender()