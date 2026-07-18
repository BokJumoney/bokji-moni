"""REST API와 구독 Tool이 함께 사용하는 애플리케이션 서비스.

API와 채팅 Tool이 같은 비즈니스 규칙을 사용하도록 조회·변경·DTO 변환을
한곳에 모은다. Repository는 SQL만 만들고, 이 계층이 transaction 경계와
동시성 충돌 복구 및 안전한 도메인 예외 변환을 책임진다.
"""

import uuid
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.common.timezone import KST, now_kst
from app.domain.subscription.dto.response import (
    NotificationSettingsResponse,
    PolicySubscriptionItemResponse,
    PolicySubscriptionListResponse,
)
from app.domain.subscription.entity.models import (
    PolicySubscription,
    SubscriptionSettings,
)
from app.domain.subscription.exceptions import (
    PolicyNotFoundError,
    SubscriptionStorageError,
)
from app.domain.subscription.repository import SubscriptionRepository


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

    def get_settings(self, user_id: uuid.UUID) -> NotificationSettingsResponse:
        """사용자 설정을 조회하고 없으면 기본 설정 행을 지연 생성한다."""
        try:
            settings = self._get_or_create_settings(user_id)
            return self._settings_response(settings)
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
        """정책 소식 수신 여부를 바꾸고 변경된 전체 설정을 반환한다."""
        return self._update_settings(
            user_id,
            field_name="policy_news_enabled",
            value=enabled,
        )

    def update_pause(
        self,
        user_id: uuid.UUID,
        paused: bool,
    ) -> NotificationSettingsResponse:
        """전체 알림 일시 중지 여부를 바꾸고 전체 설정을 반환한다."""
        return self._update_settings(
            user_id,
            field_name="is_paused",
            value=paused,
        )

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

    def _get_or_create_settings(
        self,
        user_id: uuid.UUID,
    ) -> SubscriptionSettings:
        """설정 GET에서도 항상 완전한 기본 객체를 주기 위해 행을 생성한다.

        미존재 행은 잠글 수 없으므로 동시 최초 GET은 둘 다 INSERT를 시도할
        수 있다. PK 충돌이 난 요청은 rollback하고 다른 요청이 만든 행을 읽는다.
        """
        settings = self.repository.get_settings(user_id)
        if settings is not None:
            return settings

        settings = SubscriptionSettings(user_id=user_id)
        self.repository.add_settings(settings)
        try:
            self.session.commit()
            self.session.refresh(settings)
            return settings
        except IntegrityError:
            # 최초 GET이 동시에 들어온 경우 다른 요청이 만든 행을 사용한다.
            self.session.rollback()
            existing = self.repository.get_settings(user_id)
            if existing is not None:
                return existing
            raise SubscriptionStorageError() from None
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionStorageError() from exc

    def _update_settings(
        self,
        user_id: uuid.UUID,
        *,
        field_name: str,
        value: bool,
    ) -> NotificationSettingsResponse:
        """설정 생성과 변경을 한 transaction에서 처리한다.

        기존 행은 ``FOR UPDATE``로 잠근 뒤 시간을 계산하므로 동시 PUT에서도
        서로 다른 설정값이 보존되고 ``updated_at``이 역행하지 않는다.
        ``FOR UPDATE``는 존재하는 행만 잠글 수 있으므로 최초 생성 경합의
        loser는 UNIQUE 충돌을 rollback한 뒤 생성된 행을 잠가 한 번 재시도한다.
        """
        try:
            settings = self.repository.get_settings_for_update(user_id)
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionStorageError() from exc
        if settings is None:
            settings = SubscriptionSettings(user_id=user_id)
            try:
                self.repository.add_settings(settings)
            except Exception as exc:
                self.session.rollback()
                raise SubscriptionStorageError() from exc

        # lock을 획득한 다음 변경 시각을 계산해야 늦게 commit된 요청의 시간이
        # 더 과거로 돌아가는 현상을 막을 수 있다.
        setattr(settings, field_name, value)
        settings.updated_at = now_kst()
        try:
            self.session.commit()
            self.session.refresh(settings)
        except IntegrityError:
            self.session.rollback()
            try:
                settings = self.repository.get_settings_for_update(user_id)
            except Exception as exc:
                raise SubscriptionStorageError() from exc
            if settings is None:
                raise SubscriptionStorageError() from None
            setattr(settings, field_name, value)
            settings.updated_at = now_kst()
            try:
                self.session.commit()
                self.session.refresh(settings)
            except Exception as exc:
                self.session.rollback()
                raise SubscriptionStorageError() from exc
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionStorageError() from exc
        return self._settings_response(settings)

    @staticmethod
    def _settings_response(
        settings: SubscriptionSettings,
    ) -> NotificationSettingsResponse:
        """ORM 필드명을 프런트 설정 계약에 맞춰 명시적으로 투영한다."""
        return NotificationSettingsResponse(
            policy_news_enabled=settings.policy_news_enabled,
            is_paused=settings.is_paused,
            updated_at=_response_datetime(settings.updated_at),
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
