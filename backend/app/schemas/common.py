"""Common schemas dùng chung."""

from typing import Any, Optional

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Chi tiết lỗi theo format chuẩn API."""

    entity: Optional[str] = None
    row: Optional[int] = None
    field: Optional[str] = None
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Response lỗi chuẩn."""

    errors: list[ErrorDetail]


class BulkResultItem(BaseModel):
    """Kết quả cho từng item trong bulk operation."""

    id: str
    name: str
    row: int


class RGBColor(BaseModel):
    """RGB color [R, G, B]."""

    r: int
    g: int
    b: int

    @classmethod
    def from_list(cls, rgb: list[int]) -> "RGBColor":
        return cls(r=rgb[0], g=rgb[1], b=rgb[2])

    def to_list(self) -> list[int]:
        return [self.r, self.g, self.b]
