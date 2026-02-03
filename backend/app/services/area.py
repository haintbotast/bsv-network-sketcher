"""Area service."""

import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Area
from app.schemas.area import AreaCreate, AreaStyle, AreaUpdate


def _normalize_grid_value(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1


async def get_areas(db: AsyncSession, project_id: str) -> list[Area]:
    """Lấy danh sách areas của project."""
    result = await db.execute(
        select(Area)
        .where(Area.project_id == project_id)
        .order_by(Area.grid_row, Area.grid_col)
    )
    return list(result.scalars().all())


async def get_area_by_id(db: AsyncSession, area_id: str) -> Optional[Area]:
    """Lấy area theo ID."""
    result = await db.execute(select(Area).where(Area.id == area_id))
    return result.scalar_one_or_none()


async def get_area_by_name(db: AsyncSession, project_id: str, name: str) -> Optional[Area]:
    """Lấy area theo tên trong project."""
    result = await db.execute(
        select(Area).where(Area.project_id == project_id, Area.name == name)
    )
    return result.scalar_one_or_none()


async def create_area(db: AsyncSession, project_id: str, data: AreaCreate) -> Area:
    """Tạo area mới."""
    style_json = None
    if data.style:
        style_json = json.dumps(data.style.model_dump())

    area = Area(
        project_id=project_id,
        name=data.name,
        grid_row=_normalize_grid_value(data.grid_row),
        grid_col=_normalize_grid_value(data.grid_col),
        position_x=data.position_x,
        position_y=data.position_y,
        width=data.width,
        height=data.height,
        style_json=style_json,
    )
    db.add(area)
    await db.commit()
    await db.refresh(area)
    return area


async def update_area(db: AsyncSession, area: Area, data: AreaUpdate) -> Area:
    """Cập nhật area."""
    update_data = data.model_dump(exclude_unset=True)

    if "style" in update_data and update_data["style"]:
        update_data["style_json"] = json.dumps(update_data.pop("style"))
    elif "style" in update_data:
        update_data.pop("style")

    if "grid_row" in update_data:
        if update_data["grid_row"] is None:
            update_data.pop("grid_row")
        else:
            update_data["grid_row"] = _normalize_grid_value(update_data["grid_row"])

    if "grid_col" in update_data:
        if update_data["grid_col"] is None:
            update_data.pop("grid_col")
        else:
            update_data["grid_col"] = _normalize_grid_value(update_data["grid_col"])

    for field, value in update_data.items():
        setattr(area, field, value)

    await db.commit()
    await db.refresh(area)
    return area


async def delete_area(db: AsyncSession, area: Area) -> None:
    """Xóa area."""
    await db.delete(area)
    await db.commit()


def parse_area_style(area: Area) -> Optional[AreaStyle]:
    """Parse style JSON từ area."""
    if not area.style_json:
        return None
    try:
        return AreaStyle(**json.loads(area.style_json))
    except Exception:
        return None
