from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlmodel import Session
from app.infrastructure.db.connection import get_session

from app.domain.admin.dto.response import FileDeleteResponse, FileUploadResponse
from app.domain.admin.service.admin_file_service import AdminFileService
from app.domain.admin.service.extract_data_service import ExtractDataService
from app.domain.admin.service.policy_embedding_service import PolicyEmbeddingService
from app.domain.admin.service.cmd_exec_service import CmdExecService
from app.domain.user.dependencies import get_current_admin

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin)],
)


def get_admin_file_service() -> AdminFileService:
    return AdminFileService()

def get_extract_data_service() -> ExtractDataService:
    return ExtractDataService(get_admin_file_service())

def get_policy_embedding_service() -> PolicyEmbeddingService:
    return PolicyEmbeddingService()

def get_cmd_exec_service() -> CmdExecService:
    return CmdExecService()

@router.post(
    "/file",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_file(
    file: UploadFile = File(...),
    file_service: AdminFileService = Depends(get_admin_file_service),
    extract_data_service: ExtractDataService = Depends(get_extract_data_service),
    policy_embedding_service: PolicyEmbeddingService = Depends(get_policy_embedding_service),
    cmd_exec_service: CmdExecService = Depends(get_cmd_exec_service)
) -> FileUploadResponse:
    store_result = await file_service.save_file(file)
    stored_path = store_result["storedFilename"]
    absolute_file_path = file_service.get_stored_path(stored_path)
    file_name, extension = stored_path.split(".")

    await cmd_exec_service.run_command([
        "npx.cmd", 
        "-y", 
        "kordoc", 
        str(absolute_file_path),
        "-o",
        f"{file_service.get_md_path()}/{file_name}.md",
    ])
    if extension == "pdf":
        await extract_data_service.parse_md_to_txt(f"{file_service.get_md_path()}/{file_name}.md", f"{file_service.get_txt_path()}/{file_name}.txt")
        await policy_embedding_service.txtfile_embedding(f"{file_service.get_txt_path()}/{file_name}.txt")

    return store_result


@router.delete(
    "/files/{file_id}",
    response_model=FileDeleteResponse,
)
def delete_file(
    file_id: str,
    service: AdminFileService = Depends(get_admin_file_service),
) -> FileDeleteResponse:
    return service.delete_file(file_id)
