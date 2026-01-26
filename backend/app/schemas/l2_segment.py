"""Schemas cho L2 Segment (VLAN)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class L2SegmentCreate(BaseModel):
    """Schema tạo L2 segment mới."""

    name: str = Field(..., min_length=1, max_length=100)
    vlan_id: int = Field(..., ge=1, le=4094)
    description: Optional[str] = Field(None, max_length=255)


class L2SegmentUpdate(BaseModel):
    """Schema cập nhật L2 segment."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    vlan_id: Optional[int] = Field(None, ge=1, le=4094)
    description: Optional[str] = Field(None, max_length=255)


class L2SegmentResponse(BaseModel):
    """Response trả về thông tin L2 segment."""

    id: str
    project_id: str
    name: str
    vlan_id: int
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class L2SegmentBulkCreate(BaseModel):
    """Schema bulk create L2 segments."""

    segments: list[L2SegmentCreate]


class L2SegmentBulkResponse(BaseModel):
    """Response cho bulk create."""

    success_count: int
    error_count: int
    created: list[dict]
    errors: list[dict]
