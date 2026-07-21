"""현재 로그인 사용자의 계정 및 상세정보 API."""

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.domain.user.dependencies import get_current_user
from app.domain.user.dto.user_request import (
    UserBackgroundUpdateRequest,
    UserProfileUpdateRequest,
)
from app.domain.user.dto.user_response import (
    UserBackgroundResponse,
    UserProfileResponse,
)
from app.domain.user.entity.models import User
from app.domain.user.service.user_service import UserService
from app.infrastructure.db.connection import get_session

router = APIRouter()


def _private_no_store(response: Response) -> None:
    """개인정보 응답이 브라우저나 중간 캐시에 남지 않도록 한다."""
    response.headers["Cache-Control"] = "private, no-store"


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="내 계정정보 조회",
)
def get_my_profile(
    response: Response,
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    _private_no_store(response)
    return UserService.profile_response(current_user)


@router.patch(
    "/me",
    response_model=UserProfileResponse,
    summary="내 계정정보 수정",
)
def update_my_profile(
    body: UserProfileUpdateRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> UserProfileResponse:
    _private_no_store(response)
    return UserService(session).update_profile(current_user, body)


@router.get(
    "/me/welfare-info",
    response_model=UserBackgroundResponse,
    summary="내 사용자 상세정보 조회",
)
def get_my_background(
    response: Response,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> UserBackgroundResponse:
    _private_no_store(response)
    return UserService(session).get_background(current_user.id)


@router.patch(
    "/me/welfare-info",
    response_model=UserBackgroundResponse,
    summary="내 사용자 상세정보 수정",
)
def update_my_background(
    body: UserBackgroundUpdateRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> UserBackgroundResponse:
    _private_no_store(response)
    return UserService(session).update_background(current_user.id, body)
