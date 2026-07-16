"""
복지 정책 리포지토리 (SQLModel ORM 기반).

정형 메타데이터 조회/필터링을 담당.
벡터 유사도 검색은 PGVector 측(setup_vectorstore.py)에서 처리.
"""
from typing import Optional
from datetime import date
from sqlmodel import Session, select

from app.domain.welfare.entity.models import WelfarePolicy
from app.common.timezone import now_kst
from app.infrastructure.db.connection import get_session


class WelfareRepository:
    """WelfarePolicy 테이블 CRUD"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, policy: WelfarePolicy) -> WelfarePolicy:
        self.session.add(policy)
        self.session.commit()
        self.session.refresh(policy)
        return policy

    def get_by_id(self, policy_id: int) -> Optional[WelfarePolicy]:
        return self.session.get(WelfarePolicy, policy_id)

    def get_by_service_id(self, service_id: str) -> Optional[WelfarePolicy]:
        stmt = select(WelfarePolicy).where(WelfarePolicy.service_id == service_id)
        return self.session.exec(stmt).first()

    def update_deadline(
        self, policy: WelfarePolicy, application_deadline: date | None
    ) -> WelfarePolicy:
        """관리자가 확인한 명확한 신청 마감일만 구조화 필드에 저장한다."""
        policy.application_deadline = application_deadline
        policy.updated_at = now_kst()
        self.session.add(policy)
        self.session.commit()
        self.session.refresh(policy)
        return policy

    def abolish(self, policy: WelfarePolicy) -> WelfarePolicy:
        """구독/발송 이력을 보존하기 위해 정책을 물리 삭제하지 않는다."""
        now = now_kst()
        policy.status = "abolished"
        policy.abolished_at = now
        policy.updated_at = now
        self.session.add(policy)
        self.session.commit()
        self.session.refresh(policy)
        return policy

    def list_all(self, limit: int = 100, offset: int = 0) -> list[WelfarePolicy]:
        stmt = select(WelfarePolicy).limit(limit).offset(offset)
        return list(self.session.exec(stmt).all())

    def filter_by_department(self, department: str) -> list[WelfarePolicy]:
        stmt = select(WelfarePolicy).where(WelfarePolicy.department == department)
        return list(self.session.exec(stmt).all())

    def filter_by_year(self, year: int) -> list[WelfarePolicy]:
        stmt = select(WelfarePolicy).where(WelfarePolicy.year == year)
        return list(self.session.exec(stmt).all())

    def count(self) -> int:
        from sqlmodel import func
        stmt = select(func.count()).select_from(WelfarePolicy)
        return self.session.exec(stmt).one()

    def delete_all(self) -> int:
        from sqlalchemy import delete
        result = self.session.exec(delete(WelfarePolicy))
        self.session.commit()
        return result.rowcount or 0
