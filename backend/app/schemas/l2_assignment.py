"""Schemas cho Interface L2 Assignment."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

PortMode = Literal["access", "trunk"]


class InterfaceL2AssignmentCreate(BaseModel):
    """Schema tạo L2 assignment mới."""

    device_name: str = Field(..., min_length=1)
    interface_name: str = Field(..., min_length=1)
    l2_segment_id: str = Field(..., min_length=1)
    port_mode: PortMode = "access"
    native_vlan: Optional[int] = Field(None, ge=1, le=4094)
    allowed_vlans: Optional[list[int]] = None

    @field_validator("interface_name")
    @classmethod
    def validate_interface_format(cls, v: str) -> str:
        """Interface phải có khoảng trắng giữa loại và số."""
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


class InterfaceL2AssignmentUpdate(BaseModel):
    """Schema cập nhật L2 assignment."""

    device_name: Optional[str] = Field(None, min_length=1)
    interface_name: Optional[str] = Field(None, min_length=1)
    l2_segment_id: Optional[str] = Field(None, min_length=1)
    port_mode: Optional[PortMode] = None
    native_vlan: Optional[int] = Field(None, ge=1, le=4094)
    allowed_vlans: Optional[list[int]] = None

    @field_validator("interface_name")
    @classmethod
    def validate_interface_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        import re

        if not re.match(r"^[A-Za-z\-]+\s+.+$", v):
            raise ValueError(
                f"Interface '{v}' không hợp lệ. Phải có khoảng trắng (vd: 'Gi 0/1')"
            )
        return v


class InterfaceL2AssignmentResponse(BaseModel):
    """Response trả về thông tin L2 assignment."""

    id: str
    project_id: str
    device_id: str
    device_name: Optional[str] = None
    interface_name: str
    l2_segment_id: str
    l2_segment_name: Optional[str] = None
    vlan_id: Optional[int] = None
    port_mode: str
    native_vlan: Optional[int] = None
    allowed_vlans: Optional[list[int]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InterfaceL2AssignmentBulkCreate(BaseModel):
    """Schema bulk create L2 assignments."""

    assignments: list[InterfaceL2AssignmentCreate]


class InterfaceL2AssignmentBulkResponse(BaseModel):
    """Response cho bulk create."""

    success_count: int
    error_count: int
    created: list[dict]
    errors: list[dict]
