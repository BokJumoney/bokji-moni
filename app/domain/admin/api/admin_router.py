from fastapi import APIRouter, Depends, File, UploadFile, status

from app.domain.admin.dto.response import FileDeleteResponse, FileUploadResponse
from app.domain.admin.service.admin_service import AdminFileService

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


def get_admin_file_service() -> AdminFileService:
    return AdminFileService()


@router.post(
    "/file",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    file: UploadFile = File(...),
    service: AdminFileService = Depends(get_admin_file_service),
) -> FileUploadResponse:
    return await service.save_file(file)


@router.delete(
    "/files/{file_id}",
    response_model=FileDeleteResponse,
)
def delete_file(
    file_id: str,
    service: AdminFileService = Depends(get_admin_file_service),
) -> FileDeleteResponse:
    return service.delete_file(file_id)
