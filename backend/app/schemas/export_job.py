"""Schemas cho export job."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

ExportType = Literal[
    "l1_diagram",
    "l2_diagram",
    "l3_diagram",
    "device_file",
    "master_file",
]

ExportFormat = Literal["pptx", "pdf", "png", "xlsx"]
ExportMode = Literal["all_areas", "per_area"]
ExportTheme = Literal["default", "contrast", "dark", "light"]


class ExportOptions(BaseModel):
    """Tùy chọn export."""

    mode: ExportMode = "all_areas"
    theme: ExportTheme = "default"
    format: ExportFormat = "pptx"
    version_id: Optional[str] = None


class ExportRequest(BaseModel):
    """Request tạo export job."""

    mode: ExportMode = "all_areas"
    theme: ExportTheme = "default"
    format: Optional[ExportFormat] = None
    version_id: Optional[str] = None


class ExportJobResponse(BaseModel):
    """Response trả về export job."""

    id: str
    project_id: str
    export_type: ExportType
    status: str
    progress: int = 0
    message: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    options: Optional[dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
