"""Schemas cho Device Port."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

PortSide = Literal["top", "bottom", "left", "right"]


class DevicePortCreate(BaseModel):
    """Schema tạo port mới cho device."""

    name: str = Field(..., min_length=1, max_length=50)
    side: PortSide = "bottom"
    offset_ratio: Optional[float] = Field(None, ge=0, le=1)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Tên port không được để trống")
        return normalized


class DevicePortUpdate(BaseModel):
    """Schema cập nhật port cho device."""

    name: Optional[str] = Field(None, min_length=1, max_length=50)
    side: Optional[PortSide] = None
    offset_ratio: Optional[float] = Field(None, ge=0, le=1)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Tên port không được để trống")
        return normalized


class DevicePortResponse(BaseModel):
    """Response cho device port."""

    id: str
    project_id: str
    device_id: str
    device_name: Optional[str] = None
    name: str
    side: PortSide
    offset_ratio: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
