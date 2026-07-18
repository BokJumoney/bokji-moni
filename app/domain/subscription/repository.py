"""구독 설정·정책 구독의 SQLModel Repository.

Repository는 SQL 작성과 행 추가/삭제만 담당하고 transaction의 commit과
rollback은 애플리케이션 서비스가 담당한다. 모든 개인 데이터 쿼리는
``user_id`` 조건을 포함해 다른 사용자의 행이 섞이지 않도록 한다.
"""

import uuid
from typing import Optional

from sqlalchemy import case, func, or_
from sqlmodel import Session, select

from app.domain.subscription.entity.models import (
    PolicySubscription,
    SubscriptionSettings,
)
from app.domain.welfare.entity.models import WelfarePolicy


class SubscriptionRepository:
    """구독 도메인의 동기 SQLModel 데이터 접근 계층."""

    def __init__(self, session: Session):
        self.session = session

    def get_settings(self, user_id: uuid.UUID) -> Optional[SubscriptionSettings]:
        """사용자 PK로 설정 한 행을 조회한다."""
        return self.session.get(SubscriptionSettings, user_id)

    def get_settings_for_update(
        self,
        user_id: uuid.UUID,
    ) -> Optional[SubscriptionSettings]:
        """설정 변경이 끝날 때까지 기존 행을 잠가 동시 PUT 덮어쓰기를 막는다.

        행이 아직 없으면 잠글 대상도 없다. 그 최초 생성 경합은 서비스에서
        PK 충돌을 rollback한 뒤 생성된 행을 다시 잠그는 방식으로 처리한다.
        """
        statement = (
            select(SubscriptionSettings)
            .where(SubscriptionSettings.user_id == user_id)
            .with_for_update()
        )
        return self.session.exec(statement).first()

    def add_settings(self, settings: SubscriptionSettings) -> None:
        """설정 행을 세션에 추가하되 commit은 호출한 서비스에 맡긴다."""
        self.session.add(settings)

    def get_subscription(
        self,
        user_id: uuid.UUID,
        service_id: str,
    ) -> Optional[PolicySubscription]:
        """현재 사용자가 가진 특정 정책 구독만 조회한다."""
        # service_id만으로 조회하면 다른 사용자의 구독이 노출될 수 있으므로
        # 소유자 조건을 항상 같은 SQL 문에 포함한다.
        statement = select(PolicySubscription).where(
            PolicySubscription.user_id == user_id,
            PolicySubscription.service_id == service_id,
        )
        return self.session.exec(statement).first()

    def add_subscription(self, subscription: PolicySubscription) -> None:
        """구독 행을 세션에 추가하되 commit은 호출한 서비스에 맡긴다."""
        self.session.add(subscription)

    def list_subscriptions(self, user_id: uuid.UUID) -> list[PolicySubscription]:
        """사용자의 구독을 최신 생성 순으로 일관되게 반환한다."""
        statement = (
            select(PolicySubscription)
            .where(PolicySubscription.user_id == user_id)
            # 생성 시간이 같아도 숫자 PK를 보조 정렬키로 사용해 순서를 고정한다.
            .order_by(
                PolicySubscription.created_at.desc(),
                PolicySubscription.id.desc(),
            )
        )
        return list(self.session.exec(statement).all())

    def delete_subscription(
        self,
        user_id: uuid.UUID,
        service_id: str,
    ) -> bool:
        """사용자 소유 구독을 삭제 대상으로 표시하고 존재 여부를 반환한다.

        실제 commit은 서비스가 수행한다. 행이 없어도 False를 반환하므로
        DELETE API는 멱등적인 204 응답을 만들 수 있다.
        """
        subscription = self.get_subscription(user_id, service_id)
        if subscription is None:
            return False
        self.session.delete(subscription)
        return True

    def find_policy_candidates(
        self,
        query: str,
        limit: int = 5,
    ) -> list[tuple[str, str]]:
        """정책 ID 또는 이름으로 중복 청크를 제거해 후보를 찾는다.

        한 정책이 여러 ``WelfarePolicy`` 청크로 존재하므로 ID와 이름으로
        GROUP BY한다. 완전 일치 후보를 부분 일치보다 먼저 보여주고, Tool
        응답이 너무 길어지지 않도록 상위 ``limit``건만 반환한다.
        """
        normalized = query.strip()
        if not normalized:
            return []

        lowered = normalized.casefold()
        # LLM이 정확한 정책명/ID를 전달한 경우 해당 후보가 첫 번째가 되도록
        # PostgreSQL CASE 정렬값을 만든다.
        exact_rank = case(
            (
                func.lower(func.trim(WelfarePolicy.service_id)) == lowered,
                0,
            ),
            (
                func.lower(func.trim(WelfarePolicy.service_name)) == lowered,
                0,
            ),
            else_=1,
        )
        statement = (
            select(WelfarePolicy.service_id, WelfarePolicy.service_name)
            .where(
                or_(
                    WelfarePolicy.service_id.ilike(f"%{normalized}%"),
                    WelfarePolicy.service_name.ilike(f"%{normalized}%"),
                )
            )
            # 정책당 여러 청크 행을 사용자에게 한 후보로 보여준다.
            .group_by(WelfarePolicy.service_id, WelfarePolicy.service_name)
            .order_by(
                exact_rank,
                WelfarePolicy.service_name,
                WelfarePolicy.service_id,
            )
            .limit(limit)
        )
        return [
            (str(service_id), str(service_name).strip())
            for service_id, service_name in self.session.exec(statement).all()
        ]

    def find_subscription_candidates(
        self,
        user_id: uuid.UUID,
        query: str,
        limit: int = 5,
    ) -> list[PolicySubscription]:
        """현재 사용자의 구독 안에서만 ID/이름 후보를 검색한다."""
        normalized = query.strip()
        if not normalized:
            return []

        lowered = normalized.casefold()
        exact_rank = case(
            (
                func.lower(func.trim(PolicySubscription.service_id)) == lowered,
                0,
            ),
            (
                func.lower(func.trim(PolicySubscription.service_name)) == lowered,
                0,
            ),
            else_=1,
        )
        # 해지 후보 검색 역시 user_id를 SQL 조건에 포함해 다른 사용자의
        # service_id가 후보나 삭제 대상으로 선택되지 않게 한다.
        statement = (
            select(PolicySubscription)
            .where(
                PolicySubscription.user_id == user_id,
                or_(
                    PolicySubscription.service_id.ilike(f"%{normalized}%"),
                    PolicySubscription.service_name.ilike(f"%{normalized}%"),
                ),
            )
            .order_by(
                exact_rank,
                PolicySubscription.service_name,
                PolicySubscription.service_id,
            )
            .limit(limit)
        )
        return list(self.session.exec(statement).all())
