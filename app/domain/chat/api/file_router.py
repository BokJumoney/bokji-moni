from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.domain.admin.repository import AdminRepository
from app.domain.admin.service.admin_file_service import AdminFileService
from app.domain.user.dependencies import get_current_user
from app.domain.user.entity.models import User
from app.infrastructure.db.connection import get_session


router = APIRouter()


@router.get("/{file_id}/download", response_class=FileResponse)
def download_hwp_file(
    file_id: UUID,
    _current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    hwp_file = AdminRepository(session).find_hwp_file_by_uuid(file_id)
    if hwp_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="신청서 정보를 찾을 수 없습니다.",
        )

    file_service = AdminFileService()
    stored_path = file_service.resolve_hwp_path(file_id)
    if stored_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="신청서 파일을 찾을 수 없습니다.",
        )

    original_name = Path(hwp_file.origin_file_name).name
    if Path(original_name).suffix.lower() not in file_service.HWP_EXTENSIONS:
        original_name = f"{original_name}{stored_path.suffix}"

    return FileResponse(
        path=stored_path,
        filename=original_name,
        media_type="application/octet-stream",
        headers={"Cache-Control": "private, no-store"},
    )
