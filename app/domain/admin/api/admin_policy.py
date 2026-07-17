from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlmodel import Session
from app.infrastructure.db.connection import get_session
from app.domain.user.dependencies import get_current_admin

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin)],
)

@router.get("/policies")
def get_policies(
        session: Session = Depends(get_session)
):
    """
    관리자 신청서 업로드용 정책 목록 조회
    """
    query = text("""
                SELECT DISTINCT
                        policy_id, policy_name
                 FROM welfare_policy_pdf_vector
                 ORDER BY policy_name
                    """)
    result = session.exec(query).mappings().all()
    
    policies = []

    for row in result:
        policies.append(
            {
                "id": row.policy_id,
                "name": row.policy_name.strip()
            }
        )
    return policies
