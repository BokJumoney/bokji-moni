"""프런트 구독 화면에서 사용하는 인증 필수 REST API.

라우터는 HTTP 입출력과 인증 사용자 주입만 담당하고 실제 규칙은
``SubscriptionApplicationService``에 위임한다. 모든 응답 형태는 프런트의
subscriptionApi.js 계약에 맞춘다. ``user_id``는 body나 path로 받지 않고
인증 의존성이 반환한 ``current_user.id``만 사용한다.

SQLModel 접근이 동기 방식이므로 endpoint도 일반 ``def``로 선언하며 FastAPI가
별도 worker thread에서 실행하도록 맡긴다.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from app.domain.subscription.dto.request import (
    NotificationPauseUpdateRequest,
    PolicyNewsUpdateRequest,
)
from app.domain.subscription.dto.response import (
    NotificationSettingsResponse,
    PolicySubscriptionListResponse,
)
from app.domain.subscription.exceptions import SubscriptionError
from app.domain.subscription.service.subscription_service import (
    SubscriptionApplicationService,
)
from app.domain.user.dependencies import get_current_user
from app.domain.user.entity.models import User
from app.infrastructure.db.connection import get_session

router = APIRouter(prefix="/api/v1/subscriptions", tags=["구독"])


def _subscription_error_to_http(exc: SubscriptionError) -> HTTPException:
    """도메인 예외를 프런트가 읽는 ``detail.code/message``로 변환한다."""
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


@router.get(
    "/settings",
    response_model=NotificationSettingsResponse,
    summary="알림 설정 조회",
)
def get_notification_settings(
    response: Response,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> NotificationSettingsResponse:
    """현재 사용자의 알림 설정을 조회한다."""
    # 개인 설정은 브라우저나 중간 캐시에 남기지 않는다.
    response.headers["Cache-Control"] = "private, no-store"
    try:
        return SubscriptionApplicationService(session).get_settings(current_user.id)
    except SubscriptionError as exc:
        raise _subscription_error_to_http(exc) from exc


@router.put(
    "/settings/policy-news",
    response_model=NotificationSettingsResponse,
    summary="정책 소식 수신 설정 변경",
)
def update_policy_news(
    body: PolicyNewsUpdateRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> NotificationSettingsResponse:
    """정책 소식 수신 여부를 변경하고 두 설정값을 모두 반환한다."""
    response.headers["Cache-Control"] = "private, no-store"
    try:
        return SubscriptionApplicationService(session).update_policy_news(
            current_user.id,
            body.enabled,
        )
    except SubscriptionError as exc:
        raise _subscription_error_to_http(exc) from exc


@router.put(
    "/settings/pause",
    response_model=NotificationSettingsResponse,
    summary="모든 알림 일시 중지 설정 변경",
)
def update_notification_pause(
    body: NotificationPauseUpdateRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> NotificationSettingsResponse:
    """모든 알림의 일시 중지 여부를 변경하고 전체 설정을 반환한다."""
    response.headers["Cache-Control"] = "private, no-store"
    try:
        return SubscriptionApplicationService(session).update_pause(
            current_user.id,
            body.paused,
        )
    except SubscriptionError as exc:
        raise _subscription_error_to_http(exc) from exc


@router.get(
    "",
    response_model=PolicySubscriptionListResponse,
    summary="구독 정책 목록 조회",
)
def list_policy_subscriptions(
    response: Response,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PolicySubscriptionListResponse:
    """항상 ``{"items": [...]}`` 형태로 현재 사용자 구독을 반환한다."""
    response.headers["Cache-Control"] = "private, no-store"
    try:
        return SubscriptionApplicationService(session).list_subscriptions(
            current_user.id
        )
    except SubscriptionError as exc:
        raise _subscription_error_to_http(exc) from exc


@router.delete(
    "/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="개별 정책 알림 해지",
)
def unsubscribe_policy(
    service_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    """정책 구독을 멱등하게 해지한다.

    존재하지 않거나 이미 삭제된 구독도 204를 반환한다. 다른 사용자의 동일
    service_id 행은 서비스의 user_id 조건 때문에 삭제되지 않는다.
    """
    try:
        SubscriptionApplicationService(session).unsubscribe(
            current_user.id,
            service_id,
        )
    except SubscriptionError as exc:
        raise _subscription_error_to_http(exc) from exc
    # 프런트 요청 모듈은 빈 본문의 204와 JSON 성공 응답을 모두 처리할 수
    # 있으므로, 삭제 응답은 가장 단순한 빈 204로 통일한다.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
