"""
복지 정책 SQLModel 엔티티 (정형 메타데이터 + 본문).

langchain_postgres.PGVector가 임베딩+문서+메타데이터를 별도 테이블에 저장하므로,
이 모델은 구조화된 조회/필터링/CRUD를 위한 보조 테이블임.
임베딩 컬럼은 PGVector 측에만 존재.
"""
from typing import Optional
from sqlmodel import SQLModel, Field


class WelfarePolicy(SQLModel, table=True):
    __tablename__ = "welfare_policies"

    id: Optional[int] = Field(default=None, primary_key=True)

    # 정형 메타데이터
    service_id: str = Field(index=True)
    service_name: str = Field(index=True)
    department: str = Field(default="", index=True)
    year: int = Field(default=0, index=True)
    cycle: str = Field(default="")
    type: str = Field(default="")
    life_cycle: str = Field(default="")
    topic: str = Field(default="")
    household_type: str = Field(default="")

    # 본문 (서술형)
    page_content: str