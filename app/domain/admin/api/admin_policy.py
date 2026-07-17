from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.domain.admin.entity.models import PdfWelfareList
from app.infrastructure.db.connection import get_session

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

@router.get("/policies")
def get_policies(
        session: Session = Depends(get_session)
):
    """
    관리자 신청서 업로드용 정책 목록 조회
    """
    policies = session.exec(
        select(PdfWelfareList).order_by(PdfWelfareList.policy_name)
    ).all()

    return [
        {
            "policy_id": str(policy.policy_uuid),
            "name": policy.policy_name.strip(),
        }
        for policy in policies
    ]
