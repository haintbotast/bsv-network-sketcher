"""Admin config endpoints."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas.admin_config import AdminConfigPayload, AdminConfigResponse
from app.services.admin_config import get_admin_config, upsert_admin_config

router = APIRouter(tags=["admin"])


@router.get("/admin/config", response_model=AdminConfigResponse)
async def get_config(
    current_user: CurrentUser,
    db: DBSession,
) -> AdminConfigResponse:
    """Lấy cấu hình admin (global)."""
    config = await get_admin_config(db)
    return AdminConfigResponse(config=config)


@router.put("/admin/config", response_model=AdminConfigResponse)
async def update_config(
    data: AdminConfigPayload,
    current_user: CurrentUser,
    db: DBSession,
) -> AdminConfigResponse:
    """Cập nhật cấu hình admin (global)."""
    record = await upsert_admin_config(db, data.config)
    return AdminConfigResponse(config=data.config, updated_at=record.updated_at)
