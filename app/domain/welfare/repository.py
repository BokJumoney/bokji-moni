"""
복지 정책 리포지토리 (SQLModel ORM 기반).

정형 메타데이터 조회/필터링을 담당.
벡터 유사도 검색은 PGVector 측(setup_vectorstore.py)에서 처리.
"""
from typing import Optional
from sqlmodel import Session, select

from app.domain.welfare.entity.models import WelfarePolicy
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