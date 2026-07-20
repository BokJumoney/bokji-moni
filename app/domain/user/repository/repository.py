"""
사용자·세션·복지정보 리포지토리 (SQLModel 기반).

- UserRepository: 사용자 생성·이메일/ID 조회·이름 갱신
- AuthSessionRepository: 세션 생성·토큰 해시 조회·폐기·touch
- UserWelfareRepository: 사용자별 1:1 복지 정보 생성/조회/부분 갱신(upsert)
"""
from datetime import timedelta
from typing import Optional

from sqlmodel import Session, select

from app.common.timezone import now_kst
from app.domain.user.entity.models import AuthSession, User, UserWelfare


class UserRepository:
    """users 테이블 DB 접근."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        return self.session.exec(stmt).first()

    def get_by_id(self, user_id) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        return self.session.exec(stmt).first()

    def get_by_id_for_update(self, user_id) -> Optional[User]:
        """알림 설정 변경이 끝날 때까지 사용자 행을 잠근다."""
        stmt = select(User).where(User.id == user_id).with_for_update()
        return self.session.exec(stmt).first()

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update_name(self, user: User, name: str) -> User:
        """사용자 표시 이름과 updated_at 을 갱신한다."""
        user.name = name
        user.updated_at = now_kst()
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update_notification_enabled(self, user: User, enabled: bool) -> User:
        """전역 알림 수신 여부와 계정 변경 시각을 함께 갱신한다."""
        user.noti_agreed = enabled
        user.updated_at = now_kst()
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user


class AuthSessionRepository:
    """auth_sessions 테이블 DB 접근."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, auth_session: AuthSession) -> AuthSession:
        self.session.add(auth_session)
        self.session.commit()
        self.session.refresh(auth_session)
        return auth_session

    def get_by_token_hash(self, token_hash: str) -> Optional[AuthSession]:
        stmt = select(AuthSession).where(AuthSession.token_hash == token_hash)
        return self.session.exec(stmt).first()

    def revoke(self, auth_session: AuthSession) -> AuthSession:
        auth_session.revoked_at = now_kst()
        self.session.add(auth_session)
        self.session.commit()
        self.session.refresh(auth_session)
        return auth_session

    def touch(
        self,
        auth_session: AuthSession,
        idle_minutes: int,
    ) -> AuthSession:
        """last_seen_at과 idle 만료 시각을 갱신하고 commit 한다."""
        from app.infrastructure.config import settings

        now = now_kst()
        auth_session.last_seen_at = now
        auth_session.idle_expires_at = now + timedelta(minutes=idle_minutes)
        self.session.add(auth_session)
        self.session.commit()
        self.session.refresh(auth_session)
        return auth_session


class UserWelfareRepository:
    """user_welfare 테이블 DB 접근 (사용자별 1:1)."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_user_id(self, user_id) -> Optional[UserWelfare]:
        stmt = select(UserWelfare).where(UserWelfare.user_id == user_id)
        return self.session.exec(stmt).first()

    def create(self, user_welfare: UserWelfare) -> UserWelfare:
        self.session.add(user_welfare)
        self.session.commit()
        self.session.refresh(user_welfare)
        return user_welfare

    def update_fields(self, user_welfare: UserWelfare, fields: dict) -> UserWelfare:
        """전달된 필드만 갱신하고 updated_at 을 서버에서 설정한다.

        fields 값이 None 이면 해당 컬럼을 DB 에서 지운다(null 삭제).
        user_id 는 변경하지 않는다.
        """
        protected = {"user_id", "created_at", "updated_at"}
        for key, value in fields.items():
            if key in protected:
                continue
            if hasattr(user_welfare, key):
                setattr(user_welfare, key, value)
        user_welfare.updated_at = now_kst()
        self.session.add(user_welfare)
        self.session.commit()
        self.session.refresh(user_welfare)
        return user_welfare