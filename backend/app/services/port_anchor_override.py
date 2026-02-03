"""Service cho Port Anchor Override."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PortAnchorOverride
from app.schemas.port_anchor_override import PortAnchorOverrideCreate, PortAnchorOverrideUpdate


async def get_overrides_by_project(
    db: AsyncSession,
    project_id: str,
) -> list[PortAnchorOverride]:
    result = await db.execute(
        select(PortAnchorOverride).where(PortAnchorOverride.project_id == project_id)
    )
    return list(result.scalars().all())


async def get_override_by_port(
    db: AsyncSession,
    project_id: str,
    device_id: str,
    port_name: str,
) -> Optional[PortAnchorOverride]:
    result = await db.execute(
        select(PortAnchorOverride).where(
            PortAnchorOverride.project_id == project_id,
            PortAnchorOverride.device_id == device_id,
            PortAnchorOverride.port_name == port_name,
        )
    )
    return result.scalar_one_or_none()


async def upsert_override(
    db: AsyncSession,
    project_id: str,
    data: PortAnchorOverrideCreate,
) -> PortAnchorOverride:
    override = await get_override_by_port(db, project_id, data.device_id, data.port_name)
    if override:
        override.side = data.side
        override.offset_ratio = data.offset_ratio
    else:
        override = PortAnchorOverride(
            project_id=project_id,
            device_id=data.device_id,
            port_name=data.port_name,
            side=data.side,
            offset_ratio=data.offset_ratio,
        )
        db.add(override)
    await db.commit()
    await db.refresh(override)
    return override


async def update_override(
    db: AsyncSession,
    override: PortAnchorOverride,
    data: PortAnchorOverrideUpdate,
) -> PortAnchorOverride:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(override, field, value)
    await db.commit()
    await db.refresh(override)
    return override


async def delete_override(
    db: AsyncSession,
    override: PortAnchorOverride,
) -> None:
    await db.delete(override)
    await db.commit()
