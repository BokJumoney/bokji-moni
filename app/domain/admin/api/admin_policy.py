from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.domain.welfare.entity.models import WelfarePolicy
from app.infrastructure.db.connection import get_session

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/policies")
def get_policies(session: Session = Depends(get_session)):
    """신청서 업로드용 정책 목록을 반환한다."""
    policies = session.exec(
        select(WelfarePolicy.service_id, WelfarePolicy.service_name)
        .distinct()
        .order_by(WelfarePolicy.service_name)
    ).all()
    return [
        {"policy_id": service_id, "name": service_name.strip()}
        for service_id, service_name in policies
    ]
