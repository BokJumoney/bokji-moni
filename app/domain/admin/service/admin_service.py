from pathlib import Path
import re
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status


class AdminFileService:
    def __init__(self) -> None:
        self.upload_dir = Path(__file__).resolve().parents[4] / "storage" / "admin_files"

    async def save_file(self, file: UploadFile) -> dict:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required.",
            )

        self.upload_dir.mkdir(parents=True, exist_ok=True)

        original_name = Path(file.filename).name
        extension = Path(original_name).suffix
        file_id = uuid4().hex
        stored_name = f"{file_id}{extension}"
        stored_path = self.upload_dir / stored_name

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

    def delete_file(self, file_id: str) -> dict:
        if not re.fullmatch(r"[0-9a-f]{32}", file_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file ID.",
            )

        matches = [path for path in self.upload_dir.glob(f"{file_id}*") if path.stem == file_id]
        if not matches:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found.",
            )

        deleted = matches[0]
        deleted.unlink()

        return {
            "fileId": file_id,
            "deleted": True,
        }
