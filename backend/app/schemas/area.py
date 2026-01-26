"""Schemas cho Area."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AreaStyle(BaseModel):
    """Style của area."""

    fill_color_rgb: list[int] = Field(default=[240, 240, 240], min_length=3, max_length=3)
    stroke_color_rgb: list[int] = Field(default=[51, 51, 51], min_length=3, max_length=3)
    stroke_width: float = Field(default=1, ge=0.5, le=5)


class AreaCreate(BaseModel):
    """Schema tạo area mới."""

    name: str = Field(..., min_length=1, max_length=100, pattern="^[A-Za-z0-9_\\-\\s]+$")
    grid_row: int = Field(..., ge=1, le=100)
    grid_col: int = Field(..., ge=1, le=100)
    position_x: Optional[float] = Field(None, ge=0)
    position_y: Optional[float] = Field(None, ge=0)
    width: float = Field(3.0, ge=0.5, le=50)
    height: float = Field(1.5, ge=0.5, le=50)
    style: Optional[AreaStyle] = None


class AreaUpdate(BaseModel):
    """Schema cập nhật area."""

    name: Optional[str] = Field(None, min_length=1, max_length=100, pattern="^[A-Za-z0-9_\\-\\s]+$")
    grid_row: Optional[int] = Field(None, ge=1, le=100)
    grid_col: Optional[int] = Field(None, ge=1, le=100)
    position_x: Optional[float] = Field(None, ge=0)
    position_y: Optional[float] = Field(None, ge=0)
    width: Optional[float] = Field(None, ge=0.5, le=50)
    height: Optional[float] = Field(None, ge=0.5, le=50)
    style: Optional[AreaStyle] = None


class AreaResponse(BaseModel):
    """Response trả về thông tin area."""

    id: str
    project_id: str
    name: str
    grid_row: int
    grid_col: int
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    width: float = 3.0
    height: float = 1.5
    style: Optional[AreaStyle] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AreaBulkCreate(BaseModel):
    """Schema bulk create areas."""

    areas: list[AreaCreate]


class AreaBulkResponse(BaseModel):
    """Response cho bulk create."""

    success_count: int
    error_count: int
    created: list[dict]
    errors: list[dict]
