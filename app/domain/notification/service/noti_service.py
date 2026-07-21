from sqlmodel import Session

from app.domain.notification.graph.new_noti_graph import noti_app
from app.domain.notification.graph.state import EmailPromptRoute


async def send_new_policy_email(session: Session, policies: list[dict]):
    print("새로운 정책 추가 확인.\n신규 정책 알림 이메일을 발송합니다.")

    await noti_app.ainvoke({
        "new_policies":policies,
        "noti_type":EmailPromptRoute.NEW_POLICY,
    })