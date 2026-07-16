"""외부 LLM 없이 실행 가능한 구독 도메인 규칙 테스트."""

import unittest
from datetime import timedelta

from sqlmodel import Session, create_engine

from app.common.exceptions import PolicyNotSubscribableError
from app.common.timezone import now_kst
from app.domain.chat.entity.models import Conversation
from app.domain.subscription.entity.models import (
    NotificationSettings,
    PolicySubscription,
    SubscriptionDialog,
)
from app.domain.subscription.service.subscription_service import (
    PolicySubscriptionService,
)
from app.domain.user.entity.models import User
from app.domain.welfare.entity.models import WelfarePolicy


class PolicySubscriptionServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        # 전체 메타데이터 대신 이 테스트에 필요한 테이블만 생성해 테스트가
        # 다른 도메인의 DB 기능이나 PostgreSQL 확장에 의존하지 않게 한다.
        for table in (
            User.__table__,
            Conversation.__table__,
            WelfarePolicy.__table__,
            PolicySubscription.__table__,
            NotificationSettings.__table__,
            SubscriptionDialog.__table__,
        ):
            table.create(self.engine, checkfirst=True)

    def _seed(self, session: Session, deadline=True):
        user = User(
            email="subscription-test@example.com",
            password_hash="test",
            name="구독 테스트",
        )
        policy = WelfarePolicy(
            service_id="TEST-SUBSCRIPTION",
            service_name="구독 테스트 정책",
            application_deadline=(
                now_kst().date() + timedelta(days=30) if deadline else None
            ),
            page_content="테스트 본문",
        )
        session.add(user)
        session.add(policy)
        session.commit()
        session.refresh(user)
        session.refresh(policy)
        return user, policy

    def test_subscribe_is_idempotent_and_can_be_cancelled(self):
        with Session(self.engine) as session:
            user, policy = self._seed(session)
            service = PolicySubscriptionService(session)

            first, first_changed = service.subscribe(user.id, policy.id)
            second, second_changed = service.subscribe(user.id, policy.id)

            self.assertTrue(first_changed)
            self.assertFalse(second_changed)
            self.assertEqual(first.id, second.id)
            self.assertEqual(1, len(service.list_subscriptions(user.id)))

            service.unsubscribe(user.id, policy.id)
            self.assertEqual([], service.list_subscriptions(user.id))

    def test_policy_without_deadline_is_rejected(self):
        with Session(self.engine) as session:
            user, policy = self._seed(session, deadline=False)
            service = PolicySubscriptionService(session)

            with self.assertRaises(PolicyNotSubscribableError):
                service.subscribe(user.id, policy.id)


if __name__ == "__main__":
    unittest.main()
