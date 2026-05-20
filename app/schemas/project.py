from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)


class ProjectRead(BaseModel):
    id: int
    name: str
    description: str | None
    owner_id: int
    total_size_bytes: int
    documents_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectInviteCreate(BaseModel):
    login: str = Field(min_length=1, max_length=50)
    role: Literal["owner", "participant"]


class ProjectInviteRead(BaseModel):
    id: int
    project_id: int
    invited_login: str
    role: str
    token: str
    expires_at: datetime
    created_at: datetime


class ProjectInviteAccept(BaseModel):
    token: str = Field(min_length=1)


class ProjectMemberRead(BaseModel):
    id: int
    project_id: int
    user_id: int
    login: str
    role: str
    created_at: datetime
