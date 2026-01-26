"""Schemas cho import dữ liệu tổng hợp."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ErrorDetail

ImportMode = Literal["template", "json", "excel", "csv"]
MergeStrategy = Literal["replace", "merge"]


class ImportOptions(BaseModel):
    """Tùy chọn import."""

    validate_only: bool = False
    merge_strategy: MergeStrategy = "replace"


class ImportRequest(BaseModel):
    """Request import tổng hợp."""

    mode: ImportMode
    template_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    options: ImportOptions = Field(default_factory=ImportOptions)


class ImportL2Assignment(BaseModel):
    """Schema import L2 assignment (dùng tên L2 segment)."""

    device_name: str = Field(..., min_length=1)
    interface_name: str = Field(..., min_length=1)
    l2_segment: str = Field(..., min_length=1)
    port_mode: Literal["access", "trunk"] = "access"
    native_vlan: Optional[int] = Field(None, ge=1, le=4094)
    allowed_vlans: Optional[list[int]] = None

    @field_validator("interface_name")
    @classmethod
    def validate_interface_format(cls, v: str) -> str:
        import re

        if not re.match(r"^[A-Za-z\-]+\s+.+$", v):
            raise ValueError(
                f"Interface '{v}' không hợp lệ. Phải có khoảng trắng (vd: 'Gi 0/1')"
            )
        return v

    @field_validator("allowed_vlans")
    @classmethod
    def validate_allowed_vlans(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        if v is None:
            return v
        for vlan in v:
            if not 1 <= vlan <= 4094:
                raise ValueError(f"VLAN {vlan} không hợp lệ (phải từ 1-4094)")
        return v


class ImportResult(BaseModel):
    """Kết quả import tổng hợp."""

    mode: str
    validate_only: bool
    merge_strategy: str
    applied: bool
    created: dict[str, int]
    skipped: dict[str, int]
    errors: list[ErrorDetail]
