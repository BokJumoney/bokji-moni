"""
인증 응답 DTO.

세션 토큰은 응답 JSON에 포함하지 않고 Set-Cookie 로만 전달한다.
password_hash 는 어떤 응답에서도 노출되지 않는다.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class AuthUserResponse(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    role: str


class LoginResponse(BaseModel):
    user: AuthUserResponse
    expires_at: datetime


class SessionResponse(BaseModel):
    user: AuthUserResponse
    idle_expires_at: datetime
    absolute_expires_at: datetime