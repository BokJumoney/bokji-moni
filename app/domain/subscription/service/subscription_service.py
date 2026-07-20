"""REST API와 구독 Tool이 함께 사용하는 애플리케이션 서비스.

API와 채팅 Tool이 같은 비즈니스 규칙을 사용하도록 조회·변경·DTO 변환을
한곳에 모은다. Repository는 SQL만 만들고, 이 계층이 transaction 경계와
동시성 충돌 복구 및 안전한 도메인 예외 변환을 책임진다.
"""

import uuid
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.common.timezone import KST
from app.domain.subscription.dto.response import (
    NotificationSettingsResponse,
    PolicySubscriptionItemResponse,
    PolicySubscriptionListResponse,
)
from app.domain.subscription.entity.models import PolicySubscription
from app.domain.subscription.exceptions import (
    PolicyNotFoundError,
    SubscriptionStorageError,
)
from app.domain.subscription.repository import SubscriptionRepository
from app.domain.user.entity.models import User
from app.domain.user.repository.repository import UserRepository


def _response_datetime(value: datetime) -> datetime:
    """DB의 naive KST wall time을 RFC3339 +09:00 응답으로 바꾼다."""
    if value.tzinfo is None:
        return value.replace(tzinfo=KST)
    return value.astimezone(KST)


class SubscriptionApplicationService:
    """구독 도메인의 transaction과 응답 변환을 조정한다."""

    def __init__(self, session: Session):
        self.session = session
        self.repository = SubscriptionRepository(session)
        self.user_repository = UserRepository(session)

    def get_settings(self, user_id: uuid.UUID) -> NotificationSettingsResponse:
        """users 행에 저장된 단일 알림 수신 여부를 호환 응답으로 반환한다."""
        try:
            user = self.user_repository.get_by_id(user_id)
            if user is None:
                raise SubscriptionStorageError()
            return self._settings_response(user)
        except SubscriptionStorageError:
            raise
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionStorageError() from exc

    def update_policy_news(
        self,
        user_id: uuid.UUID,
        enabled: bool,
    ) -> NotificationSettingsResponse:
        """기존 정책 소식 API를 전체 알림 수신 여부에 연결한다."""
        return self._update_notification_enabled(user_id, enabled)

    def list_subscriptions(
        self,
        user_id: uuid.UUID,
    ) -> PolicySubscriptionListResponse:
        """현재 사용자의 구독만 프런트 목록 DTO로 변환한다."""
        try:
            rows = self.repository.list_subscriptions(user_id)
            return PolicySubscriptionListResponse(
                items=[self._subscription_response(row) for row in rows]
            )
        except SubscriptionStorageError:
            raise
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionStorageError() from exc

    def subscribe(
        self,
        user_id: uuid.UUID,
        service_id: str,
        service_name: str,
    ) -> PolicySubscriptionItemResponse:
        """정책 스냅샷을 멱등하게 구독한다.

        같은 사용자·서비스 ID가 이미 있으면 기존 행을 그대로 반환한다.
        동시에 같은 정책을 구독한 경우 DB UNIQUE 제약에서 한 요청만 성공하고,
        loser는 rollback 후 winner가 만든 행을 읽어 같은 결과를 돌려준다.
        이 메서드는 호출자가 후보를 이미 확정했다고 보고 전달된 ID·이름을
        신뢰하며, 원본 정책을 다시 조회하거나 기존 엔티티와 join하지 않는다.
        """
        normalized_id = service_id.strip()
        normalized_name = service_name.strip()
        if not normalized_id or not normalized_name:
            raise PolicyNotFoundError()

        try:
            existing = self.repository.get_subscription(user_id, normalized_id)
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionStorageError() from exc
        if existing is not None:
            return self._subscription_response(existing)

        # 원본 정책 청크를 직접 참조하지 않고 표시용 값을 스냅샷으로 저장한다.
        # 구조화된 마감일 공급원이 아직 없어 application_deadline은 null로
        # 두며, 이후 수집 경로가 생겨도 이 신규 테이블 안에서 채울 수 있다.
        subscription = PolicySubscription(
            user_id=user_id,
            service_id=normalized_id,
            service_name=normalized_name,
        )
        try:
            self.repository.add_subscription(subscription)
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionStorageError() from exc
        try:
            self.session.commit()
            self.session.refresh(subscription)
        except IntegrityError:
            # 같은 사용자의 동시 구독 요청은 기존 행을 반환한다.
            self.session.rollback()
            try:
                existing = self.repository.get_subscription(user_id, normalized_id)
            except Exception as exc:
                raise SubscriptionStorageError() from exc
            if existing is None:
                raise SubscriptionStorageError() from None
            subscription = existing
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionStorageError() from exc

        return self._subscription_response(subscription)

    def unsubscribe(self, user_id: uuid.UUID, service_id: str) -> bool:
        """사용자 소유 구독을 해지하고 실제 삭제 대상이 있었는지 반환한다."""
        try:
            deleted = self.repository.delete_subscription(
                user_id,
                service_id.strip(),
            )
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionStorageError() from exc
        if not deleted:
            return False
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionStorageError() from exc
        return True

    def find_policy_candidates(
        self,
        query: str,
        limit: int = 5,
    ) -> list[tuple[str, str]]:
        """구독 추가에 사용할 원본 정책 후보를 찾는다."""
        try:
            return self.repository.find_policy_candidates(query, limit)
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionStorageError() from exc

    def find_subscription_candidates(
        self,
        user_id: uuid.UUID,
        query: str,
        limit: int = 5,
    ) -> list[PolicySubscription]:
        """구독 해지에 사용할 현재 사용자 소유 후보를 찾는다."""
        try:
            return self.repository.find_subscription_candidates(
                user_id,
                query,
                limit,
            )
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionStorageError() from exc

    def _update_notification_enabled(
        self,
        user_id: uuid.UUID,
        enabled: bool,
    ) -> NotificationSettingsResponse:
        """사용자 행을 잠근 뒤 전체 알림 수신 여부를 변경한다."""
        try:
            user = self.user_repository.get_by_id_for_update(user_id)
            if user is None:
                raise SubscriptionStorageError() from None
            user = self.user_repository.update_notification_enabled(user, enabled)
            return self._settings_response(user)
        except SubscriptionStorageError:
            self.session.rollback()
            raise
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionStorageError() from exc

    @staticmethod
    def _settings_response(
        user: User,
    ) -> NotificationSettingsResponse:
        """user.noti_agreed를 반환함"""
        return NotificationSettingsResponse(
            policy_news_enabled=user.noti_agreed,
            updated_at=_response_datetime(user.updated_at)
        )

    @staticmethod
    def _subscription_response(
        subscription: PolicySubscription,
    ) -> PolicySubscriptionItemResponse:
        """저장된 정책 스냅샷을 프런트 목록 항목으로 변환한다."""
        # flush/commit 전의 임시 객체는 숫자 PK가 없으므로 외부 응답으로
        # 내보내지 않고 저장 오류로 처리한다.
        if subscription.id is None:
            raise SubscriptionStorageError()
        return PolicySubscriptionItemResponse(
            id=subscription.id,
            service_id=subscription.service_id,
            service_name=subscription.service_name,
            application_deadline=subscription.application_deadline,
            created_at=_response_datetime(subscription.created_at),
        )
