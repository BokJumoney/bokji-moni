"""정책 구독과 채팅 진행 상태를 다루는 SQLModel 리포지토리."""

import uuid
from datetime import datetime

from sqlalchemy import or_
from sqlmodel import Session, select

from app.common.timezone import now_kst
from app.domain.subscription.entity.models import (
    NotificationSettings,
    PolicySubscription,
    SubscriptionDialog,
)
from app.domain.welfare.entity.models import WelfarePolicy


class SubscriptionRepository:
    """구독 서비스가 필요한 DB 연산을 한곳에 모은다."""

    def __init__(self, session: Session):
        self.session = session

    def get_policy(self, policy_id: int) -> WelfarePolicy | None:
        return self.session.get(WelfarePolicy, policy_id)

    def get_policy_by_service_id(self, service_id: str) -> WelfarePolicy | None:
        return self.session.exec(
            select(WelfarePolicy).where(WelfarePolicy.service_id == service_id)
        ).first()

    def find_policy_name_in_text(self, text: str) -> str | None:
        """이전 답변에 실제 정책명이 포함됐는지 가장 긴 이름부터 찾는다."""
        names = self.session.exec(select(WelfarePolicy.service_name).distinct()).all()
        matches = [name for name in names if name and name in text]
        return max(matches, key=len) if matches else None

    def get_policies(self, policy_ids: list[int]) -> list[WelfarePolicy]:
        if not policy_ids:
            return []
        rows = self.session.exec(
            select(WelfarePolicy).where(WelfarePolicy.id.in_(policy_ids))
        ).all()
        by_id = {row.id: row for row in rows}
        # DB의 반환 순서가 아니라 에이전트가 사용자에게 보여 준 후보 순서를 유지한다.
        return [by_id[policy_id] for policy_id in policy_ids if policy_id in by_id]

    def search_policies(self, query: str, limit: int = 3) -> list[WelfarePolicy]:
        """정확 일치와 부분 일치를 우선하는 가벼운 정책 검색."""
        normalized = query.strip()
        exact = list(
            self.session.exec(
                select(WelfarePolicy)
                .where(WelfarePolicy.status == "active")
                .where(
                    or_(
                        WelfarePolicy.service_name == normalized,
                        WelfarePolicy.service_id == normalized,
                    )
                )
                .order_by(WelfarePolicy.id)
                .limit(limit * 10)
            ).all()
        )
        partial = list(
            self.session.exec(
                select(WelfarePolicy)
                .where(WelfarePolicy.status == "active")
                .where(WelfarePolicy.service_name.ilike(f"%{normalized}%"))
                .order_by(WelfarePolicy.id)
                .limit(limit * 20)
            ).all()
        )
        # 과거 청크 단위 적재 데이터가 남아 있더라도 사용자에게 같은 정책을
        # 여러 번 보여주지 않도록 service_id 기준으로 중복을 제거한다.
        result: list[WelfarePolicy] = []
        seen_service_ids: set[str] = set()
        for policy in exact + partial:
            if policy.service_id in seen_service_ids:
                continue
            result.append(policy)
            seen_service_ids.add(policy.service_id)
            if len(result) == limit:
                break
        return result

    def get_subscription(
        self, user_id: uuid.UUID, policy_id: int
    ) -> PolicySubscription | None:
        return self.session.exec(
            select(PolicySubscription).where(
                PolicySubscription.user_id == user_id,
                PolicySubscription.policy_id == policy_id,
            )
        ).first()

    def list_active(self, user_id: uuid.UUID) -> list[PolicySubscription]:
        return list(
            self.session.exec(
                select(PolicySubscription).where(
                    PolicySubscription.user_id == user_id,
                    PolicySubscription.status == "active",
                )
            ).all()
        )

    def save_subscription(self, subscription: PolicySubscription) -> PolicySubscription:
        self.session.add(subscription)
        self.session.commit()
        self.session.refresh(subscription)
        return subscription

    def get_settings(self, user_id: uuid.UUID) -> NotificationSettings | None:
        return self.session.get(NotificationSettings, user_id)

    def save_settings(self, settings: NotificationSettings) -> NotificationSettings:
        self.session.add(settings)
        self.session.commit()
        self.session.refresh(settings)
        return settings


class SubscriptionDialogRepository:
    """채팅방별로 아직 끝나지 않은 구독 대화를 저장하고 복원한다."""

    ACTIVE_STAGES = ("awaiting_selection", "awaiting_confirmation")

    def __init__(self, session: Session):
        self.session = session

    def get_active(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> SubscriptionDialog | None:
        now = now_kst()
        dialog = self.session.exec(
            select(SubscriptionDialog)
            .where(
                SubscriptionDialog.conversation_id == conversation_id,
                SubscriptionDialog.user_id == user_id,
                SubscriptionDialog.stage.in_(self.ACTIVE_STAGES),
            )
            .order_by(SubscriptionDialog.updated_at.desc())
        ).first()
        if dialog is not None and dialog.expires_at <= now:
            dialog.stage = "expired"
            dialog.updated_at = now
            self.save(dialog)
            return None
        return dialog

    def save(self, dialog: SubscriptionDialog) -> SubscriptionDialog:
        dialog.updated_at = now_kst()
        self.session.add(dialog)
        self.session.commit()
        self.session.refresh(dialog)
        return dialog

    def finish(self, dialog: SubscriptionDialog, stage: str = "completed") -> None:
        dialog.stage = stage
        dialog.updated_at = now_kst()
        self.session.add(dialog)
        self.session.commit()
