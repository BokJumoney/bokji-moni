from sqlmodel import Session

from app.domain.notification.graph.noti_graph import noti_app
from app.domain.user.repository.repository import UserRepository

async def send_new_policy_email(session: Session, policies: list[dict]):
    print("새로운 정책 추가 확인.\n신규 정책 알림 이메일을 발송합니다.")

    test_repo = UserRepository(session)

    # 테스트용) 신규 정책 알림 동의 유저 선택 코드
    testuser = test_repo.get_by_email("kimdoo@gmail.com")

    await noti_app.ainvoke({
        "new_policies":policies,
        "user_names":[testuser.name],
        "user_emails" : [testuser.email]
    })