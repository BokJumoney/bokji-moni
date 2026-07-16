"""정책 구독의 검증과 상태 변경을 담당하는 애플리케이션 서비스."""

import uuid

from sqlmodel import Session

from app.common.exceptions import (
    PolicyNotFoundError,
    PolicyNotSubscribableError,
    SubscriptionNotFoundError,
)
from app.common.timezone import now_kst
from app.domain.subscription.entity.models import NotificationSettings, PolicySubscription
from app.domain.subscription.repository import SubscriptionRepository
from app.domain.welfare.entity.models import WelfarePolicy


class PolicySubscriptionService:
    """LLM과 화면 API가 공통으로 호출하는 확정적 구독 서비스.

    에이전트가 정책을 잘못 해석하더라도 이 서비스의 검증을 통과하지 못하면
    실제 DB 상태가 바뀌지 않는다. 모든 구독 진입점은 이 서비스를 사용한다.
    """

    def __init__(self, session: Session):
        self.repo = SubscriptionRepository(session)

    def validate_subscribable(self, policy_id: int) -> WelfarePolicy:
        policy = self.repo.get_policy(policy_id)
        if policy is None:
            raise PolicyNotFoundError()
        if policy.status != "active":
            raise PolicyNotSubscribableError("폐지된 정책은 구독할 수 없습니다.")
        if policy.application_deadline is None:
            raise PolicyNotSubscribableError(
                "신청 마감일이 명확하지 않아 마감 알림을 등록할 수 없습니다."
            )
        if policy.application_deadline < now_kst().date():
            raise PolicyNotSubscribableError("신청 마감일이 지난 정책입니다.")
        return policy

    def subscribe(
        self, user_id: uuid.UUID, policy_id: int
    ) -> tuple[PolicySubscription, bool]:
        """구독을 활성화하고, 새로 상태가 바뀌었는지도 함께 반환한다."""
        self.validate_subscribable(policy_id)
        subscription = self.repo.get_subscription(user_id, policy_id)
        if subscription is not None and subscription.status == "active":
            return subscription, False

        now = now_kst()
        if subscription is None:
            subscription = PolicySubscription(user_id=user_id, policy_id=policy_id)
        else:
            # 사용자-정책 조합은 한 행만 유지하고 재구독 시 다시 활성화한다.
            subscription.status = "active"
            subscription.cancelled_at = None
            subscription.updated_at = now
        return self.repo.save_subscription(subscription), True

    def unsubscribe(
        self, user_id: uuid.UUID, policy_id: int
    ) -> PolicySubscription:
        subscription = self.repo.get_subscription(user_id, policy_id)
        if subscription is None or subscription.status != "active":
            raise SubscriptionNotFoundError()
        now = now_kst()
        subscription.status = "cancelled"
        subscription.cancelled_at = now
        subscription.updated_at = now
        return self.repo.save_subscription(subscription)

    def list_subscriptions(
        self, user_id: uuid.UUID
    ) -> list[tuple[PolicySubscription, WelfarePolicy]]:
        subscriptions = self.repo.list_active(user_id)
        policies = self.repo.get_policies([item.policy_id for item in subscriptions])
        by_id = {policy.id: policy for policy in policies}
        return [
            (item, by_id[item.policy_id])
            for item in subscriptions
            if item.policy_id in by_id
        ]

    def get_or_create_settings(self, user_id: uuid.UUID) -> NotificationSettings:
        settings = self.repo.get_settings(user_id)
        if settings is None:
            settings = self.repo.save_settings(NotificationSettings(user_id=user_id))
        return settings

    def set_policy_news(self, user_id: uuid.UUID, enabled: bool) -> NotificationSettings:
        settings = self.get_or_create_settings(user_id)
        settings.policy_news_enabled = enabled
        settings.updated_at = now_kst()
        return self.repo.save_settings(settings)

    def set_paused(self, user_id: uuid.UUID, paused: bool) -> NotificationSettings:
        settings = self.get_or_create_settings(user_id)
        settings.is_paused = paused
        settings.updated_at = now_kst()
        return self.repo.save_settings(settings)
