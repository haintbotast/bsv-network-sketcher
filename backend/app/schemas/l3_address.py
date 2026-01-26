"""Schemas cho L3 Address."""

import ipaddress
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class L3AddressCreate(BaseModel):
    """Schema tạo L3 address mới."""

    device_name: str = Field(..., min_length=1)
    interface_name: str = Field(..., min_length=1)
    ip_address: str = Field(..., min_length=1)
    prefix_length: int = Field(..., ge=0, le=128)
    is_secondary: bool = False
    description: Optional[str] = Field(None, max_length=255)

    @field_validator("interface_name")
    @classmethod
    def validate_interface_format(cls, v: str) -> str:
        """Interface phải có khoảng trắng giữa loại và số."""
        import re

        if not re.match(r"^[A-Za-z\-]+\s+.+$", v):
            raise ValueError(
                f"Interface '{v}' không hợp lệ. Phải có khoảng trắng (vd: 'Gi 0/1', 'Vlan 100')"
            )
        return v

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v: str) -> str:
        """Validate IPv4 hoặc IPv6."""
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"Địa chỉ IP '{v}' không hợp lệ")
        return v

    @field_validator("prefix_length")
    @classmethod
    def validate_prefix_length(cls, v: int, info) -> int:
        """Prefix length phải phù hợp với loại IP."""
        # Sẽ validate kết hợp với ip_address trong model_validator nếu cần
        return v


class L3AddressUpdate(BaseModel):
    """Schema cập nhật L3 address."""

    device_name: Optional[str] = Field(None, min_length=1)
    interface_name: Optional[str] = Field(None, min_length=1)
    ip_address: Optional[str] = Field(None, min_length=1)
    prefix_length: Optional[int] = Field(None, ge=0, le=128)
    is_secondary: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=255)

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

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"Địa chỉ IP '{v}' không hợp lệ")
        return v


class L3AddressResponse(BaseModel):
    """Response trả về thông tin L3 address."""

    id: str
    project_id: str
    device_id: str
    device_name: Optional[str] = None
    interface_name: str
    ip_address: str
    prefix_length: int
    is_secondary: bool = False
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class L3AddressBulkCreate(BaseModel):
    """Schema bulk create L3 addresses."""

    addresses: list[L3AddressCreate]


class L3AddressBulkResponse(BaseModel):
    """Response cho bulk create."""

    success_count: int
    error_count: int
    created: list[dict]
    errors: list[dict]
