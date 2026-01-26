"""Schemas cho Virtual Port."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

VirtualInterfaceType = Literal["Vlan", "Loopback", "Port-Channel"]


class VirtualPortCreate(BaseModel):
    """Schema tạo Virtual Port mới."""

    device_name: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    interface_type: VirtualInterfaceType

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        import re

        if not re.match(r"^(Vlan|Loopback|Port-[Cc]hannel)\s*\d+$", v):
            raise ValueError("Tên virtual port không hợp lệ (vd: 'Vlan 10', 'Loopback 0')")
        return v


class VirtualPortUpdate(BaseModel):
    """Schema cập nhật Virtual Port."""

    device_name: Optional[str] = Field(None, min_length=1)
    name: Optional[str] = Field(None, min_length=1)
    interface_type: Optional[VirtualInterfaceType] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        import re

        if not re.match(r"^(Vlan|Loopback|Port-[Cc]hannel)\s*\d+$", v):
            raise ValueError("Tên virtual port không hợp lệ (vd: 'Vlan 10', 'Loopback 0')")
        return v


class VirtualPortResponse(BaseModel):
    """Response trả về thông tin Virtual Port."""

    id: str
    project_id: str
    device_id: str
    device_name: Optional[str] = None
    name: str
    interface_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class VirtualPortBulkCreate(BaseModel):
    """Schema bulk create Virtual Ports."""

    virtual_ports: list[VirtualPortCreate]


class VirtualPortBulkResponse(BaseModel):
    """Response cho bulk create."""

    success_count: int
    error_count: int
    created: list[dict]
    errors: list[dict]
