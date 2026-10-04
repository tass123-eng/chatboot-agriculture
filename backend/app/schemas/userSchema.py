from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    language: str = "en"
    role: str = "farmer"


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    language: str | None = None
    role: str | None = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)