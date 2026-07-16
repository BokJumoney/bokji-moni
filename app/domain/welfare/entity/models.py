"""
복지 정책 SQLModel 엔티티 (정형 메타데이터 + 본문).

langchain_postgres.PGVector가 임베딩+문서+메타데이터를 별도 테이블에 저장하므로,
이 모델은 구조화된 조회/필터링/CRUD를 위한 보조 테이블임.
임베딩 컬럼은 PGVector 측에만 존재.
"""
from datetime import date, datetime
from typing import Optional

from sqlmodel import SQLModel, Field

from app.common.timezone import now_kst


class WelfarePolicy(SQLModel, table=True):
    __tablename__ = "welfare_policies"

    id: Optional[int] = Field(default=None, primary_key=True)

    # 정형 메타데이터
    # 외부 복지 데이터의 서비스 ID를 정책의 안정적인 업무 식별자로 사용한다.
    # 구독은 청크가 아니라 정책 자체를 참조해야 하므로 중복을 허용하지 않는다.
    service_id: str = Field(index=True, unique=True)
    service_name: str = Field(index=True)
    department: str = Field(default="", index=True)
    year: int = Field(default=0, index=True)
    cycle: str = Field(default="")
    type: str = Field(default="")
    life_cycle: str = Field(default="")
    topic: str = Field(default="")
    household_type: str = Field(default="")

    # 마감일이 명확하지 않은 수시/예산 소진 정책은 NULL로 유지한다.
    # 구독 서비스는 NULL인 정책에 마감 알림을 등록하지 않는다.
    application_deadline: Optional[date] = Field(default=None, index=True)
    status: str = Field(default="active", max_length=20, index=True)
    created_at: datetime = Field(default_factory=now_kst, nullable=False)
    updated_at: datetime = Field(default_factory=now_kst, nullable=False)
    abolished_at: Optional[datetime] = Field(default=None)

    # 본문 (서술형)
    page_content: str
