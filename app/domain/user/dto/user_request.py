"""사용자 계정 및 상세정보 변경 요청 DTO."""

from datetime import date
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class UserProfileUpdateRequest(BaseModel):
    """현재 사용자가 변경할 수 있는 계정 필드."""

    name: str = Field(min_length=1, max_length=100)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("이름은 공백일 수 없습니다.")
        return normalized


class UserBackgroundUpdateRequest(BaseModel):
    """복지 맞춤 서비스에 사용하는 사용자 상세정보의 부분 변경."""

    income: Optional[int] = Field(default=None, ge=0)
    age: Optional[int] = None
    family_size: Optional[int] = Field(default=None, ge=1, le=30)
    disability: Optional[bool] = None
    assets: Optional[int] = Field(default=None, ge=0)
    employment_stat: Optional[str] = Field(default=None, max_length=50)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "UserBackgroundUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("변경할 상세정보를 하나 이상 입력해야 합니다.")
        return self