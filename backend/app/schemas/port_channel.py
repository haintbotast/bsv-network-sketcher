"""Schemas cho Port Channel."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

PortChannelMode = Literal["LACP", "static"]


class PortChannelCreate(BaseModel):
    """Schema tạo Port Channel mới."""

    device_name: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    channel_number: Optional[int] = Field(None, ge=1, le=256)
    mode: PortChannelMode = "LACP"
    members: list[str] = Field(..., min_length=1, max_length=16)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        import re

        if not re.match(r"^Port-[Cc]hannel\s*\d+$", v):
            raise ValueError("Tên port-channel không hợp lệ (vd: 'Port-Channel 1')")
        return v

    @field_validator("members")
    @classmethod
    def validate_members(cls, v: list[str]) -> list[str]:
        import re

        for member in v:
            if not re.match(r"^[A-Za-z\-]+\s+.+$", member):
                raise ValueError(
                    f"Member '{member}' không hợp lệ. Phải có khoảng trắng (vd: 'Gi 0/1')"
                )
        return v


class PortChannelUpdate(BaseModel):
    """Schema cập nhật Port Channel."""

    device_name: Optional[str] = Field(None, min_length=1)
    name: Optional[str] = Field(None, min_length=1)
    channel_number: Optional[int] = Field(None, ge=1, le=256)
    mode: Optional[PortChannelMode] = None
    members: Optional[list[str]] = Field(None, min_length=1, max_length=16)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        import re

        if not re.match(r"^Port-[Cc]hannel\s*\d+$", v):
            raise ValueError("Tên port-channel không hợp lệ (vd: 'Port-Channel 1')")
        return v

    @field_validator("members")
    @classmethod
    def validate_members(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        import re

        for member in v:
            if not re.match(r"^[A-Za-z\-]+\s+.+$", member):
                raise ValueError(
                    f"Member '{member}' không hợp lệ. Phải có khoảng trắng (vd: 'Gi 0/1')"
                )
        return v


class PortChannelResponse(BaseModel):
    """Response trả về thông tin Port Channel."""

    id: str
    project_id: str
    device_id: str
    device_name: Optional[str] = None
    name: str
    channel_number: int
    mode: str
    members: list[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PortChannelBulkCreate(BaseModel):
    """Schema bulk create Port Channels."""

    port_channels: list[PortChannelCreate]


class PortChannelBulkResponse(BaseModel):
    """Response cho bulk create."""

    success_count: int
    error_count: int
    created: list[dict]
    errors: list[dict]
