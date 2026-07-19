"""사용자 계정 및 상세정보 응답 DTO."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserProfileResponse(BaseModel):
    """비밀번호 해시와 권한을 노출하지 않는 사용자 계정정보."""

    id: UUID
    email: EmailStr
    name: str
    created_at: datetime
    updated_at: datetime


class UserDetailResponse(BaseModel):
    """복지 맞춤 서비스에 사용하는 현재 사용자의 상세정보."""

    birth_date: Optional[date] = None
    monthly_income: Optional[int] = None
    family_size: Optional[int] = None
    household_type: Optional[str] = None
    region: Optional[str] = None
    district: Optional[str] = None
    has_disability: Optional[bool] = None
    assets: Optional[int] = None
    employment_status: Optional[str] = None
    updated_at: Optional[datetime] = None
