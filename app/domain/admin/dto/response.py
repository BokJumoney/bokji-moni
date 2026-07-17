from datetime import datetime

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    fileId: str
    originalFilename: str
    storedFilename: str
    size: int


class FileDeleteResponse(BaseModel):
    fileId: str
    deleted: bool


class FileListItemResponse(BaseModel):
    fileId: str
    originalFilename: str
    storedFilename: str
    size: int
    uploadedAt: datetime | None = None
    status: str
    policyName: str | None = None
