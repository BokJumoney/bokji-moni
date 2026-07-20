from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status


class AdminFileService:
    HWP_EXTENSIONS = (".hwp", ".hwpx")

    def __init__(self) -> None:
        self.upload_pdf_dir = Path(__file__).resolve().parents[4] / "storage" / "pdf_files"
        self.upload_hwp_dir = Path(__file__).resolve().parents[4] / "storage" / "hwp_files"
        self.md_dir = Path(__file__).resolve().parents[4] / "storage" / "output" / "md"
        self.txt_dir = Path(__file__).resolve().parents[4] / "storage" / "output" / "txt"

    def get_stored_pdf_path(self, stored_filename: str) :
        return f"{self.upload_pdf_dir}/{stored_filename}" 

    def get_stored_hwp_path(self, stored_filename: str):
        return f"{self.upload_hwp_dir}/{stored_filename}"

    def resolve_hwp_path(self, file_id: UUID | str) -> Path | None:
        """UUID에 해당하는 실제 HWP/HWPX 저장 파일을 반환한다."""
        try:
            normalized_id = UUID(str(file_id)).hex
        except (TypeError, ValueError):
            return None

        for extension in self.HWP_EXTENSIONS:
            candidate = self.upload_hwp_dir / f"{normalized_id}{extension}"
            if candidate.is_file():
                return candidate
        return None

    def get_upload_path(self):
        return self.upload_pdf_dir

    def get_stored_file_info(self, stored_filename: str, file_type: str) -> dict:
        directory = self.upload_pdf_dir if file_type == "pdf" else self.upload_hwp_dir
        stored_path = directory / stored_filename

        if not stored_path.is_file():
            return {
                "size": 0,
                "uploadedAt": None,
                "status": "파일 없음",
            }

        stat = stored_path.stat()
        return {
            "size": stat.st_size,
            "uploadedAt": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            "status": "업로드 완료",
        }
    
    def get_md_path(self):
        if not self.md_dir.exists():
            self.md_dir.mkdir()
        return self.md_dir
    
    def get_txt_path(self):
        if not self.txt_dir.exists():
            self.txt_dir.mkdir()
        return self.txt_dir

    # 파일에 따라서 경로 분리
    async def save_file(self, file: UploadFile) -> dict:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required.",
            )

        self.md_dir.mkdir(parents=True, exist_ok=True)
        self.txt_dir.mkdir(parents=True, exist_ok=True)

        original_name = Path(file.filename).name
        extension = Path(original_name).suffix.lower()
        file_id = uuid4().hex
        stored_name = f"{file_id}{extension}"
        if extension == ".pdf":
            stored_path = self.upload_pdf_dir / stored_name
            self.upload_pdf_dir.mkdir(parents=True, exist_ok=True)
        else:
            stored_path = self.upload_hwp_dir / stored_name
            self.upload_hwp_dir.mkdir(parents=True, exist_ok=True)

        size = 0
        try:
            with stored_path.open("wb") as output:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    output.write(chunk)
        finally:
            await file.close()

        return {
            "fileId": file_id,
            "originalFilename": original_name,
            "storedFilename": stored_name,
            "size": size,
        }
