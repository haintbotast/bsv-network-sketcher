"""API endpoints cho Port Anchor Override."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.port_anchor_override import (
    get_overrides_by_project,
    get_override_by_port,
    upsert_override,
    delete_override,
)
from app.schemas.port_anchor_override import (
    PortAnchorOverrideBulkUpsert,
    PortAnchorOverrideCreate,
    PortAnchorOverrideResponse,
)


router = APIRouter(prefix="/projects/{project_id}/port-anchors", tags=["port-anchors"])


@router.get("", response_model=list[PortAnchorOverrideResponse])
async def list_port_anchor_overrides(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await get_overrides_by_project(db, project_id)


@router.put("", response_model=list[PortAnchorOverrideResponse])
async def upsert_port_anchor_overrides(
    project_id: str,
    payload: PortAnchorOverrideBulkUpsert,
    db: AsyncSession = Depends(get_db),
):
    results: list[PortAnchorOverrideResponse] = []
    for item in payload.overrides:
        created = await upsert_override(db, project_id, PortAnchorOverrideCreate(**item.model_dump()))
        results.append(created)
    return results


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_port_anchor_override(
    project_id: str,
    device_id: str,
    port_name: str,
    db: AsyncSession = Depends(get_db),
):
    override = await get_override_by_port(db, project_id, device_id, port_name)
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")
    await delete_override(db, override)
    return None
