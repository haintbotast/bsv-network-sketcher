"""Service cho L2 Segment CRUD."""

import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import L2Segment, Project
from app.schemas.l2_segment import L2SegmentCreate, L2SegmentUpdate


async def get_segment(db: AsyncSession, segment_id: str) -> Optional[L2Segment]:
    """Lấy L2 segment theo ID."""
    result = await db.execute(select(L2Segment).where(L2Segment.id == segment_id))
    return result.scalar_one_or_none()


async def get_segment_by_vlan(
    db: AsyncSession, project_id: str, vlan_id: int
) -> Optional[L2Segment]:
    """Lấy L2 segment theo VLAN ID trong project."""
    result = await db.execute(
        select(L2Segment).where(
            L2Segment.project_id == project_id,
            L2Segment.vlan_id == vlan_id,
        )
    )
    return result.scalar_one_or_none()


async def get_segments_by_project(
    db: AsyncSession,
    project_id: str,
    skip: int = 0,
    limit: int = 100,
) -> list[L2Segment]:
    """Lấy danh sách L2 segments theo project."""
    result = await db.execute(
        select(L2Segment)
        .where(L2Segment.project_id == project_id)
        .order_by(L2Segment.vlan_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_segment(
    db: AsyncSession, project_id: str, data: L2SegmentCreate
) -> L2Segment:
    """Tạo L2 segment mới."""
    segment = L2Segment(
        project_id=project_id,
        name=data.name,
        vlan_id=data.vlan_id,
        description=data.description,
    )
    db.add(segment)
    await db.commit()
    await db.refresh(segment)
    return segment


async def update_segment(
    db: AsyncSession, segment: L2Segment, data: L2SegmentUpdate
) -> L2Segment:
    """Cập nhật L2 segment."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(segment, field, value)
    await db.commit()
    await db.refresh(segment)
    return segment


async def delete_segment(db: AsyncSession, segment: L2Segment) -> None:
    """Xóa L2 segment."""
    await db.delete(segment)
    await db.commit()


async def count_segments_by_project(db: AsyncSession, project_id: str) -> int:
    """Đếm số L2 segments trong project."""
    from sqlalchemy import func

    result = await db.execute(
        select(func.count()).select_from(L2Segment).where(L2Segment.project_id == project_id)
    )
    return result.scalar() or 0
