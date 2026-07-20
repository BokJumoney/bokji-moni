"""프런트 구독 API 계약에 맞춘 응답 DTO."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class NotificationSettingsResponse(BaseModel):
    """조회와 두 PUT에서 공통으로 반환하는 전체 알림 설정.

    ``updated_at``은 서비스에서 timezone-aware KST로 복원되어 RFC3339의
    ``+09:00`` 오프셋을 포함한다.
    """

    policy_news_enabled: bool
    updated_at: datetime


class PolicySubscriptionItemResponse(BaseModel):
    """설정 화면의 구독 정책 한 행.

    ``created_at``은 ``+09:00``을 포함하고, 날짜만 있는 마감일은
    ``YYYY-MM-DD`` 또는 ``null``로 직렬화된다.
    """

    id: int
    service_id: str
    service_name: str
    # 원본 정책에 구조화된 날짜가 없으면 null로 반환한다.
    application_deadline: Optional[date]
    created_at: datetime


class PolicySubscriptionListResponse(BaseModel):
    """프런트가 배열 여부를 안정적으로 판별할 수 있는 목록 envelope."""

    items: list[PolicySubscriptionItemResponse]
