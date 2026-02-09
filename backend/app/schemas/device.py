"""Schemas cho Device."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.services.grid_excel import normalize_excel_range

DeviceType = Literal["Router", "Switch", "Firewall", "Server", "AP", "PC", "Storage", "Unknown"]


class DeviceCreate(BaseModel):
    """Schema tạo device mới."""

    name: str = Field(..., min_length=1, max_length=100, pattern="^[A-Za-z0-9_\\-\\s]+$")
    area_name: str = Field(..., min_length=1)
    device_type: DeviceType = "Unknown"
    grid_range: Optional[str] = Field(None, min_length=2, max_length=32)
    position_x: Optional[float] = Field(None, ge=0)
    position_y: Optional[float] = Field(None, ge=0)
    width: float = Field(1.2, ge=0.5, le=10)
    height: float = Field(0.5, ge=0.2, le=5)
    color_rgb: Optional[list[int]] = Field(None, min_length=3, max_length=3)

    @field_validator("grid_range")
    @classmethod
    def validate_grid_range(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return None
        return normalize_excel_range(value)


class DeviceUpdate(BaseModel):
    """Schema cập nhật device."""

    name: Optional[str] = Field(None, min_length=1, max_length=100, pattern="^[A-Za-z0-9_\\-\\s]+$")
    area_name: Optional[str] = Field(None, min_length=1)
    device_type: Optional[DeviceType] = None
    grid_range: Optional[str] = Field(None, min_length=2, max_length=32)
    position_x: Optional[float] = Field(None, ge=0)
    position_y: Optional[float] = Field(None, ge=0)
    width: Optional[float] = Field(None, ge=0.5, le=10)
    height: Optional[float] = Field(None, ge=0.2, le=5)
    color_rgb: Optional[list[int]] = Field(None, min_length=3, max_length=3)

    @field_validator("grid_range")
    @classmethod
    def validate_grid_range(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return None
        return normalize_excel_range(value)


class DeviceResponse(BaseModel):
    """Response trả về thông tin device."""

    id: str
    project_id: str
    name: str
    area_id: str
    area_name: Optional[str] = None
    device_type: str = "Unknown"
    grid_range: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    width: float = 1.2
    height: float = 0.5
    color_rgb: Optional[list[int]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceBulkCreate(BaseModel):
    """Schema bulk create devices."""

    devices: list[DeviceCreate]


class DeviceBulkResponse(BaseModel):
    """Response cho bulk create."""

    success_count: int
    error_count: int
    created: list[dict]
    errors: list[dict]
