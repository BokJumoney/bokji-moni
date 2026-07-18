"""구독 Tool 입력과 서버 주입 실행 컨텍스트."""

import uuid
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, StrictBool


@dataclass(frozen=True)
class SubscriptionExecutionContext:
    """모델에게 노출하지 않고 서버가 주입하는 인증 컨텍스트."""

    user_id: uuid.UUID


class EmptyToolInput(BaseModel):
    """인자가 필요 없는 조회 Tool의 빈 스키마."""

    # 모델이 user_id 같은 임의 필드를 끼워 넣지 못하게 한다.
    model_config = ConfigDict(extra="forbid")


class PolicyQueryInput(BaseModel):
    """정책 구독·해지 Tool이 받는 정책 ID 또는 이름."""

    query: str = Field(
        min_length=1,
        max_length=300,
        description="사용자가 말한 정책 ID 또는 정책명",
    )

    model_config = ConfigDict(extra="forbid")


class BooleanSettingInput(BaseModel):
    """알림 설정 변경 Tool이 받는 엄격한 boolean 값."""

    enabled: StrictBool

    model_config = ConfigDict(extra="forbid")
