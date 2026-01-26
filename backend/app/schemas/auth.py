"""Schemas cho authentication."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema đăng ký user mới."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    """Schema đăng nhập."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Response trả về thông tin user."""

    id: str
    email: str
    display_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 3600


class TokenData(BaseModel):
    """Dữ liệu trong JWT token."""

    user_id: str
    email: str
