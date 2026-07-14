"""
인증 요청 DTO.

- 입력 모델은 예상하지 않은 필드를 거부한다 (extra="forbid").
- 회원가입과 로그인 요청을 함께 정의한다.
"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=20)
    name: str = Field(min_length=1, max_length=100)

    model_config = ConfigDict(extra="forbid")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=20)

    model_config = ConfigDict(extra="forbid")