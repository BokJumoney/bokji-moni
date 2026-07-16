"""구독 API 응답 DTO."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class PolicySubscriptionResponse(BaseModel):
    id: UUID
    policy_id: int
    service_id: str
    service_name: str
    application_deadline: date
    status: str
    created_at: datetime
    updated_at: datetime


class PolicySubscriptionListResponse(BaseModel):
    items: list[PolicySubscriptionResponse]


class NotificationSettingsResponse(BaseModel):
    policy_news_enabled: bool
    is_paused: bool
    updated_at: datetime
