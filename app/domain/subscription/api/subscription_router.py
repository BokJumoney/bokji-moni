"""정책 상세/설정 화면에서 사용하는 구독 API."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.common.exceptions import SubscriptionError
from app.domain.subscription.dto.request import (
    PauseSettingRequest,
    PolicyNewsSettingRequest,
    PolicySubscriptionRequest,
)
from app.domain.subscription.dto.response import (
    NotificationSettingsResponse,
    PolicySubscriptionListResponse,
    PolicySubscriptionResponse,
)
from app.domain.subscription.service.subscription_service import (
    PolicySubscriptionService,
)
from app.domain.user.dependencies import get_current_user
from app.domain.user.entity.models import User
from app.infrastructure.db.connection import get_session

router = APIRouter()


def _to_http(exc: SubscriptionError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


def _subscription_response(subscription, policy) -> PolicySubscriptionResponse:
    # 서비스가 마감일을 검증했으므로 API 응답에서는 date로 안전하게 반환할 수 있다.
    return PolicySubscriptionResponse(
        id=subscription.id,
        policy_id=policy.id,
        service_id=policy.service_id,
        service_name=policy.service_name,
        application_deadline=policy.application_deadline,
        status=subscription.status,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
    )


@router.post(
    "",
    response_model=PolicySubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="정책 마감 알림 구독",
)
def subscribe(
    body: PolicySubscriptionRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PolicySubscriptionResponse:
    service = PolicySubscriptionService(session)
    try:
        subscription, _ = service.subscribe(user.id, body.policy_id)
        policy = service.validate_subscribable(body.policy_id)
        return _subscription_response(subscription, policy)
    except SubscriptionError as exc:
        raise _to_http(exc) from exc


@router.delete(
    "/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="특정 정책 구독 해지",
)
def unsubscribe(
    policy_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        PolicySubscriptionService(session).unsubscribe(user.id, policy_id)
    except SubscriptionError as exc:
        raise _to_http(exc) from exc
    return None


@router.get(
    "",
    response_model=PolicySubscriptionListResponse,
    summary="구독 정책 목록 조회",
)
def list_subscriptions(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PolicySubscriptionListResponse:
    service = PolicySubscriptionService(session)
    rows = service.list_subscriptions(user.id)
    return PolicySubscriptionListResponse(
        items=[_subscription_response(subscription, policy) for subscription, policy in rows]
    )


@router.get(
    "/settings",
    response_model=NotificationSettingsResponse,
    summary="알림 설정 조회",
)
def get_settings(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> NotificationSettingsResponse:
    settings = PolicySubscriptionService(session).get_or_create_settings(user.id)
    return NotificationSettingsResponse.model_validate(settings, from_attributes=True)


@router.put(
    "/settings/policy-news",
    response_model=NotificationSettingsResponse,
    summary="전체 정책 소식 수신 설정",
)
def set_policy_news(
    body: PolicyNewsSettingRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> NotificationSettingsResponse:
    settings = PolicySubscriptionService(session).set_policy_news(
        user.id, body.enabled
    )
    return NotificationSettingsResponse.model_validate(settings, from_attributes=True)


@router.put(
    "/settings/pause",
    response_model=NotificationSettingsResponse,
    summary="모든 알림 일시 중지 또는 재개",
)
def set_pause(
    body: PauseSettingRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> NotificationSettingsResponse:
    settings = PolicySubscriptionService(session).set_paused(user.id, body.paused)
    return NotificationSettingsResponse.model_validate(settings, from_attributes=True)
