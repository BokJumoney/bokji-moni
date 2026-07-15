from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    fileId: str
    originalFilename: str
    storedFilename: str
    size: int


class FileDeleteResponse(BaseModel):
    fileId: str
    deleted: bool
