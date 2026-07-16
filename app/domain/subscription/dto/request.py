"""구독 API 요청 DTO."""

from pydantic import BaseModel, ConfigDict, Field


class PolicySubscriptionRequest(BaseModel):
    policy_id: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid")


class PolicyNewsSettingRequest(BaseModel):
    enabled: bool

    model_config = ConfigDict(extra="forbid")


class PauseSettingRequest(BaseModel):
    paused: bool

    model_config = ConfigDict(extra="forbid")
