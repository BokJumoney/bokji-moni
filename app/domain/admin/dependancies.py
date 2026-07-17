from app.domain.admin.repository import AdminRepository
from app.domain.admin.service.admin_service import AdminService
from fastapi import Depends
from sqlalchemy.orm import Session

from app.infrastructure.db.connection import get_session

def _get_admin_repository(session: Session = Depends(get_session)):
    return AdminRepository(session)

def get_admin_service(
    repository: AdminRepository = Depends(_get_admin_repository),
) -> AdminService:
    return AdminService(repository)