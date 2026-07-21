from datetime import timedelta

from sqlmodel import Session

from app.common.timezone import now_kst
from app.domain.notification.graph.new_noti_graph import noti_app
from app.domain.notification.graph.indv_noti_graph import indv_noti_app
from app.domain.notification.graph.state import EmailPromptRoute
from app.domain.subscription.repository import SubscriptionRepository
from app.domain.user.repository.repository import UserRepository
from app.infrastructure.config import settings
from app.infrastructure.db.connection import get_session
from app.domain.welfare.repository import WelfareRepository


async def send_new_policy_email(policies: list[dict]):
    print("새로운 정책 추가 확인.\n신규 정책 알림 이메일을 발송합니다.")

    await noti_app.ainvoke({
        "new_policies":policies,
        "noti_type":EmailPromptRoute.NEW_POLICY,
    })


def _load_policies_by_ids(session: Session, service_ids: set[str]) -> dict[str, dict]:
    policies = WelfareRepository(session).get_by_service_ids(service_ids)
    return {p.service_id: p.model_dump() for p in policies}


async def send_subscription_reminder():
    #원래코드
    # target_date = now_kst().date() - timedelta(days=settings.REMINDER_AFTER_DAYS)

    #시연용
    target_date = now_kst().date() - timedelta(days=0)

    # DB에서 필요한 데이터 가져오고 세션을 닫기(LLM 호출 동안 커넥션 점유 방지)
    session = next(get_session())
    try:
        subs = SubscriptionRepository(session).find_subscription_by_created_on(target_date)
        if not subs:
            print(f"[구독 리마인더] {target_date} 생성된 구독 없음. 발송 스킵")
            return

        # 같은 정책 구독자를 묶어 정책당 그래프 1회만 호출
        groups: dict[str, list] = {}
        for sub in subs:
            groups.setdefault(sub.service_id, []).append(sub.user_id)

        policies = _load_policies_by_ids(session, set(groups))

        user_repo = UserRepository(session)
        jobs = []  # (정책 dict, 이름들, 이메일들)
        for service_id, user_ids in groups.items():
            policy = policies.get(service_id)
            if policy is None:
                print(f"[구독 리마인더] {service_id} 정책 상세 정보 없음. 스킵")
                continue
            users = user_repo.get_user_by_ids(user_ids)
            if not users:
                print(f"[구독 리마인더] {service_id} 정책 구독 이용자 없음.(탈퇴)")
                continue
            jobs.append((
                policy,
                [u.name for u in users],
                [u.email for u in users],
            ))
    finally:
        session.close()

    # 그래프 호출
    print(f"[구독 리마인더] 정책 {len(jobs)}종 / 구독 {len(subs)}건 발송 시작")
    for policy, names, emails in jobs:
        await indv_noti_app.ainvoke({
            "new_policies": [policy],
            "noti_type": EmailPromptRoute.REMIND_POLICY,
            "user_names": names,
            "user_emails": emails,
        })
