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
