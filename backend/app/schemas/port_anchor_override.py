"""Schemas cho Port Anchor Override."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

AnchorSide = Literal["left", "right", "top", "bottom"]


class PortAnchorOverrideCreate(BaseModel):
    """Schema tạo hoặc cập nhật override anchor."""

    device_id: str = Field(..., min_length=1)
    port_name: str = Field(..., min_length=1)
    side: AnchorSide = "right"
    offset_ratio: float = Field(default=0.5, ge=0.0, le=1.0)


class PortAnchorOverrideUpdate(BaseModel):
    """Schema cập nhật override anchor."""

    side: Optional[AnchorSide] = None
    offset_ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class PortAnchorOverrideResponse(BaseModel):
    """Response trả về override anchor."""

    id: str
    project_id: str
    device_id: str
    port_name: str
    side: AnchorSide
    offset_ratio: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PortAnchorOverrideBulkUpsert(BaseModel):
    """Schema bulk upsert."""

    overrides: list[PortAnchorOverrideCreate]
