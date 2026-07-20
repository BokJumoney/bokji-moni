"""사용자 계정 및 상세정보 애플리케이션 서비스."""

from uuid import UUID

from sqlmodel import Session

from app.common.timezone import now_kst
from app.domain.user.dto.user_request import (
    UserBackgroundUpdateRequest,
    UserProfileUpdateRequest,
)
from app.domain.user.dto.user_response import (
    UserBackgroundResponse,
    UserProfileResponse,
)
from app.domain.user.entity.models import User, UserBackground
from app.domain.user.repository.repository import (
    UserRepository,
    UserBackgroundRepository,
)


class UserService:
    """인증·구독 규칙과 분리된 사용자 계정 및 상세정보 처리."""

    def __init__(self, session: Session):
        self.user_repository = UserRepository(session)
        self.background_repository = UserBackgroundRepository(session)

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

    def get_background(self, user_id: UUID) -> UserBackgroundResponse:
        background = self.background_repository.get_by_user_id(user_id)
        return self.background_response(background)

    def update_background(
        self,
        user_id: UUID,
        request: UserBackgroundUpdateRequest,
    ) -> UserBackgroundResponse:
        fields = request.model_dump(exclude_unset=True)
        background = self.background_repository.get_by_user_id(user_id)

        if background is None:
            now = now_kst()
            background = UserBackground(
                user_id=user_id,
                updated_at=now,
                **fields,
            )
            background = self.background_repository.create(background)
        else:
            background = self.background_repository.update_fields(background, fields)

        return self.background_response(background)

    @staticmethod
    def background_response(background: UserBackground | None) -> UserBackgroundResponse:
        if background is None:
            return UserBackgroundResponse()
        return UserBackgroundResponse(
            income=background.income,
            age=background.age,
            family_size=background.family_size,
            disability=background.disability,
            assets=background.assets,
            employment_stat=background.employment_stat,
            updated_at=background.updated_at,
        )
