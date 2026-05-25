from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentRead(BaseModel):
    id: int
    project_id: int
    uploaded_by_id: int
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentUpdate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)


class DocumentPresignUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)


class DocumentPresignUploadRead(BaseModel):
    document_id: int
    storage_key: str
    upload_url: str
    headers: dict[str, str]
    expires_in: int


class DocumentCompleteUploadRequest(BaseModel):
    document_id: int


class DocumentDownloadUrlRead(BaseModel):
    download_url: str
    expires_in: int
