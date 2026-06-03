from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserCreate(BaseModel):
    login: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    repeat_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_repeat_password(self) -> "UserCreate":
        if self.repeat_password != self.password:
            raise ValueError("repeat_password must match password")
        return self


class UserLogin(BaseModel):
    login: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    id: int
    login: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
