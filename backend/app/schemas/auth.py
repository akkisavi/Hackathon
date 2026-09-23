from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

from app.models.user import RoleEnum, StatusEnum
from app.models.api_key import ApiKeyStatusEnum


class Token(BaseModel):
    access_token: str
    token_type: str


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    token: str
    new_password: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str
    role: RoleEnum = RoleEnum.user
    status: StatusEnum = StatusEnum.active


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[RoleEnum] = None
    status: Optional[StatusEnum] = None
    password: Optional[str] = None


class UserOut(UserBase):
    id: int
    role: RoleEnum
    status: StatusEnum
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApiKeyCreate(BaseModel):
    expires_in_days: Optional[int] = None


class ApiKeyOut(BaseModel):
    id: int
    user_id: int
    status: ApiKeyStatusEnum
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class ApiKeyGenerateOut(ApiKeyOut):
    raw_key: str
