"""Schemas cho L1 Link."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

LinkPurpose = Literal[
    "WAN",
    "INTERNET",
    "DMZ",
    "LAN",
    "MGMT",
    "HA",
    "HSRP",
    "STACK",
    "STORAGE",
    "BACKUP",
    "VPN",
    "DEFAULT",
]
LineStyle = Literal["solid", "dashed", "dotted"]
PORT_NAME_RE = r"^[A-Za-z][A-Za-z0-9 _./-]*$"


class L1LinkCreate(BaseModel):
    """Schema tạo L1 link mới."""

    from_device: str = Field(..., min_length=1)
    from_port: str = Field(..., min_length=1)
    to_device: str = Field(..., min_length=1)
    to_port: str = Field(..., min_length=1)
    purpose: LinkPurpose = "DEFAULT"
    line_style: LineStyle = "solid"
    color_rgb: Optional[list[int]] = Field(None, min_length=3, max_length=3)

    @field_validator("from_port", "to_port")
    @classmethod
    def validate_port_format(cls, v: str) -> str:
        """Port phải là chuỗi interface hợp lệ (vd: Gi 0/1, Gi0/1, P1)."""
        import re

        if not re.match(PORT_NAME_RE, v.strip()):
            raise ValueError(
                f"Port '{v}' không hợp lệ. Ví dụ hợp lệ: 'Gi 0/1', 'Gi0/1', 'P1'"
            )
        return v.strip()


class L1LinkUpdate(BaseModel):
    """Schema cập nhật L1 link."""

    from_device: Optional[str] = Field(None, min_length=1)
    from_port: Optional[str] = Field(None, min_length=1)
    to_device: Optional[str] = Field(None, min_length=1)
    to_port: Optional[str] = Field(None, min_length=1)
    purpose: Optional[LinkPurpose] = None
    line_style: Optional[LineStyle] = None
    color_rgb: Optional[list[int]] = Field(None, min_length=3, max_length=3)

    @field_validator("from_port", "to_port")
    @classmethod
    def validate_port_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        import re

        if not re.match(PORT_NAME_RE, v.strip()):
            raise ValueError(
                f"Port '{v}' không hợp lệ. Ví dụ hợp lệ: 'Gi 0/1', 'Gi0/1', 'P1'"
            )
        return v.strip()


class L1LinkResponse(BaseModel):
    """Response trả về thông tin L1 link."""

    id: str
    project_id: str
    from_device_id: str
    from_device_name: Optional[str] = None
    from_port: str
    to_device_id: str
    to_device_name: Optional[str] = None
    to_port: str
    purpose: str = "DEFAULT"
    line_style: str = "solid"
    color_rgb: Optional[list[int]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class L1LinkBulkCreate(BaseModel):
    """Schema bulk create links."""

    links: list[L1LinkCreate]


class L1LinkBulkResponse(BaseModel):
    """Response cho bulk create."""

    success_count: int
    error_count: int
    created: list[dict]
    errors: list[dict]
