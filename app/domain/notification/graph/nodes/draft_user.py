from app.domain.notification.graph.state import NotiState
from app.domain.user.repository.repository import UserRepository
from app.infrastructure.db.connection import get_session


def draft_user(state: NotiState):
    session = next(get_session())
    try:
        repo = UserRepository(session)
        users = repo.get_noti_agreed_users()
        names = [u.name for u in users]
        emails = [u.email for u in users]
    finally:
        session.close()

    print(f"신규 정책 알림 동의 구독자 {len(emails)}명 조회 완료")

    return {"user_names": names, "user_emails": emails}
