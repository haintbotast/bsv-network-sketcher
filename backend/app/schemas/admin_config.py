"""Schemas cho Admin Config."""

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class AdminConfigPayload(BaseModel):
    """Payload cấu hình admin (JSON)."""

    config: Dict[str, Any] = Field(default_factory=dict)


class AdminConfigResponse(BaseModel):
    """Response cấu hình admin."""

    config: Dict[str, Any]
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
