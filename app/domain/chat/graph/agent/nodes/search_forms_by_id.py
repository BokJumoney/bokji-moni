from app.domain.chat.graph.agent.states.search_form_state import SearchFormState
from app.domain.admin.repository import AdminRepository
from app.domain.admin.service.admin_file_service import AdminFileService
from app.infrastructure.db.connection import engine
from fastapi.concurrency import run_in_threadpool
from pathlib import Path
from sqlmodel import Session

async def search_forms_by_id(search_form_state: SearchFormState) -> dict:
    """
    DB에 저장된 신청서(HWP파일)를 찾을 때 사용합니다.
    service_id를 활용해 가져옵니다.
    """
    service_id = search_form_state.get("service_id")
    if not service_id:
        return {"forms": []}

    def _find_forms():
        with Session(engine) as session:
            return AdminRepository(session).find_hwp_files_by_service_id(service_id)

    rows = await run_in_threadpool(_find_forms)
    file_service = AdminFileService()
    forms: list[dict[str, str]] = []
    for hwp in rows:
        stored_path = file_service.resolve_hwp_path(hwp.hwp_uuid)
        original_name = Path(hwp.origin_file_name).name
        if Path(original_name).suffix.lower() not in file_service.HWP_EXTENSIONS:
            extension = stored_path.suffix if stored_path else ".hwp"
            original_name = f"{original_name}{extension}"

        file_id = str(hwp.hwp_uuid)
        forms.append(
            {
                "fileId": file_id,
                "originalFilename": original_name,
                "downloadUrl": f"/api/v1/files/{file_id}/download",
            }
        )

    return {
        "forms": forms,
    }
