from enum import Enum
from typing import Literal

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlmodel import Session

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.domain.admin.dto.response import FileListItemResponse, FileUploadResponse
from app.domain.admin.service.admin_file_service import AdminFileService
from app.domain.admin.service.admin_service import AdminService
from app.domain.admin.service.extract_data_service import ExtractDataService
from app.domain.admin.service.policy_embedding_service import PolicyEmbeddingService
from app.domain.admin.service.cmd_exec_service import CmdExecService
from app.domain.user.dependencies import get_current_admin
from app.domain.admin.dependancies import get_admin_service
from pathlib import Path
from app.infrastructure.db.connection import get_session
from app.domain.welfare.service.rag_update import service as rag_service

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin)],
)

class Tags(str, Enum):
    ADMIN = "admin"
    USER = "user"

def get_admin_file_service() -> AdminFileService:
    return AdminFileService()

def get_extract_data_service() -> ExtractDataService:
    return ExtractDataService(get_admin_file_service())

def get_policy_embedding_service() -> PolicyEmbeddingService:
    return PolicyEmbeddingService()

def get_cmd_exec_service() -> CmdExecService:
    return CmdExecService()


@router.get(
    "/files",
    response_model=list[FileListItemResponse],
)
def get_uploaded_files(
    file_type: Literal["pdf", "hwp"],
    file_service: AdminFileService = Depends(get_admin_file_service),
    admin_service: AdminService = Depends(get_admin_service),
) -> list[FileListItemResponse]:
    if file_type == "pdf":
        items = []
        for policy in admin_service.get_pdf_files():
            stored_filename = f"{policy.policy_uuid.hex}.pdf"
            file_info = file_service.get_stored_file_info(stored_filename, "pdf")
            items.append(
                FileListItemResponse(
                    fileId=str(policy.policy_uuid),
                    originalFilename=f"{policy.policy_name}.pdf",
                    storedFilename=stored_filename,
                    policyName=policy.policy_name,
                    **file_info,
                )
            )
        return items

    items = []
    for hwp_file, policy_name in admin_service.get_hwp_files():
        stored_filename = f"{hwp_file.hwp_uuid.hex}.hwp"
        file_info = file_service.get_stored_file_info(stored_filename, "hwp")
        original_filename = hwp_file.origin_file_name
        if Path(original_filename).suffix.lower() != ".hwp":
            original_filename = f"{original_filename}.hwp"

        items.append(
            FileListItemResponse(
                fileId=str(hwp_file.hwp_uuid),
                originalFilename=original_filename,
                storedFilename=stored_filename,
                policyName=policy_name,
                **file_info,
            )
        )
    return items

@router.post(
    "/file",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_pdf_file(
    file: UploadFile = File(...),
    file_service: AdminFileService = Depends(get_admin_file_service),
    extract_data_service: ExtractDataService = Depends(get_extract_data_service),
    policy_embedding_service: PolicyEmbeddingService = Depends(get_policy_embedding_service),
    admin_service: AdminService = Depends(get_admin_service),
    cmd_exec_service: CmdExecService = Depends(get_cmd_exec_service)
) -> FileUploadResponse:
    store_result = await file_service.save_file(file)
    stored_file_name = store_result["storedFilename"]
    absolute_file_path = file_service.get_stored_pdf_path(stored_file_name)
    stored_path = Path(stored_file_name)
    file_name = stored_path.stem
    extension = stored_path.suffix.lower()

    await cmd_exec_service.run_command([
        "npx.cmd", 
        "-y", 
        "kordoc", 
        str(absolute_file_path),
        "-o",
        f"{file_service.get_md_path()}/{file_name}.md",
    ])
    if extension == ".pdf":
        await extract_data_service.parse_md_to_txt(f"{file_service.get_md_path()}/{file_name}.md", f"{file_service.get_txt_path()}/{file_name}.txt")
        documents = await policy_embedding_service.get_pdf_documents(f"{file_service.get_txt_path()}/{file_name}.txt")
        policy_name = Path(store_result["originalFilename"]).stem
        await admin_service.save_pdf_embedding(file_name, policy_name, documents)

    return store_result

# hwp 신청서 파일 업로드 router
@router.post(
        "/form",
        response_model=FileUploadResponse,
        status_code=status.HTTP_201_CREATED
)
async def upload_hwp_file(
    policy_uuid: str = Form(...),
    file: UploadFile = File(...),
    admin_file_service: AdminFileService = Depends(get_admin_file_service),
    admin_service: AdminService = Depends(get_admin_service),
) -> dict:
    # hwp파일 저장
    store_result = await admin_file_service.save_file(file)
    origin_file_name = Path(store_result["originalFilename"]).stem
    file_uuid = Path(store_result["storedFilename"]).stem
    # DB 저장 로직(uuid 이름, 원본 파일 이름)
    admin_service.save_hwp_form(policy_uuid, origin_file_name, file_uuid)

    return store_result

# @router.delete(
#     "/files/{file_id}",
#     response_model=FileDeleteResponse,
# )
# def delete_file(
#     file_id: str,
#     service: AdminFileService = Depends(get_admin_file_service),
# ) -> FileDeleteResponse:
#     return service.delete_file(file_id)
@router.get("/api_call", tags=[Tags.ADMIN])
async def rag_api_call(session: Session = Depends(get_session)):
    await rag_service.api_call_rag_update(session)
