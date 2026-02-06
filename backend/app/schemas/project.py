"""Schemas cho Project."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectStats(BaseModel):
    """Thống kê project."""

    area_count: int = 0
    device_count: int = 0
    link_count: int = 0


class ProjectCreate(BaseModel):
    """Schema tạo project mới."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    layout_mode: str = Field("standard", pattern="^(standard)$")


class ProjectUpdate(BaseModel):
    """Schema cập nhật project."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    layout_mode: Optional[str] = Field(None, pattern="^(standard)$")


class ProjectResponse(BaseModel):
    """Response trả về thông tin project."""

    id: str
    name: str
    description: Optional[str] = None
    owner_id: str
    layout_mode: str = "standard"
    created_at: datetime
    updated_at: datetime
    stats: Optional[ProjectStats] = None

    class Config:
        from_attributes = True
