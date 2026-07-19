"""사용자 계정 및 상세정보 애플리케이션 서비스."""

from uuid import UUID

from sqlmodel import Session

from app.common.timezone import now_kst
from app.domain.user.dto.user_request import (
    UserDetailUpdateRequest,
    UserProfileUpdateRequest,
)
from app.domain.user.dto.user_response import (
    UserDetailResponse,
    UserProfileResponse,
)
from app.domain.user.entity.models import User, UserWelfare
from app.domain.user.repository.repository import (
    UserRepository,
    UserWelfareRepository,
)


class UserService:
    """인증·구독 규칙과 분리된 사용자 계정 및 상세정보 처리."""

    def __init__(self, session: Session):
        self.user_repository = UserRepository(session)
        self.detail_repository = UserWelfareRepository(session)

    @staticmethod
    def profile_response(user: User) -> UserProfileResponse:
        return UserProfileResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def update_profile(
        self,
        user: User,
        request: UserProfileUpdateRequest,
    ) -> UserProfileResponse:
        updated = self.user_repository.update_name(user, request.name)
        return self.profile_response(updated)

    def get_detail(self, user_id: UUID) -> UserDetailResponse:
        detail = self.detail_repository.get_by_user_id(user_id)
        return self.detail_response(detail)

    def update_detail(
        self,
        user_id: UUID,
        request: UserDetailUpdateRequest,
    ) -> UserDetailResponse:
        fields = request.model_dump(exclude_unset=True)
        detail = self.detail_repository.get_by_user_id(user_id)

        if detail is None:
            now = now_kst()
            detail = UserWelfare(
                user_id=user_id,
                created_at=now,
                updated_at=now,
                **fields,
            )
            detail = self.detail_repository.create(detail)
        else:
            detail = self.detail_repository.update_fields(detail, fields)

        return self.detail_response(detail)

    @staticmethod
    def detail_response(detail: UserWelfare | None) -> UserDetailResponse:
        if detail is None:
            return UserDetailResponse()
        return UserDetailResponse(
            birth_date=detail.birth_date,
            monthly_income=detail.monthly_income,
            family_size=detail.family_size,
            household_type=detail.household_type,
            region=detail.region,
            district=detail.district,
            has_disability=detail.has_disability,
            assets=detail.assets,
            employment_status=detail.employment_status,
            updated_at=detail.updated_at,
        )
