"""Area service."""

import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Area
from app.schemas.area import AreaCreate, AreaStyle, AreaUpdate
from app.services.grid_excel import (
    GRID_CELL_UNITS,
    excel_range_to_rect_units,
    normalize_excel_range,
    rect_units_to_excel_range,
)


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

    grid_row = _normalize_grid_value(data.grid_row) or 1
    grid_col = _normalize_grid_value(data.grid_col) or 1
    position_x = data.position_x
    position_y = data.position_y
    width = data.width
    height = data.height
    grid_range = data.grid_range

    if grid_range:
        grid_range = normalize_excel_range(grid_range)
        rect = excel_range_to_rect_units(grid_range)
        grid_row = rect["row_start"]
        grid_col = rect["col_start"]
        position_x = rect["x"]
        position_y = rect["y"]
        width = rect["width"]
        height = rect["height"]
    else:
        fallback_x = position_x if position_x is not None else (grid_col - 1) * GRID_CELL_UNITS
        fallback_y = position_y if position_y is not None else (grid_row - 1) * GRID_CELL_UNITS
        grid_range = rect_units_to_excel_range(fallback_x, fallback_y, width, height)

    area = Area(
        project_id=project_id,
        name=data.name,
        grid_row=grid_row,
        grid_col=grid_col,
        grid_range=grid_range,
        position_x=position_x,
        position_y=position_y,
        width=width,
        height=height,
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

    if "grid_range" in update_data:
        grid_range = update_data.pop("grid_range")
        if grid_range:
            normalized = normalize_excel_range(grid_range)
            rect = excel_range_to_rect_units(normalized)
            update_data["grid_range"] = normalized
            update_data["grid_row"] = rect["row_start"]
            update_data["grid_col"] = rect["col_start"]
            update_data["position_x"] = rect["x"]
            update_data["position_y"] = rect["y"]
            update_data["width"] = rect["width"]
            update_data["height"] = rect["height"]

    for field, value in update_data.items():
        setattr(area, field, value)

    fallback_x = area.position_x if area.position_x is not None else (max(1, int(area.grid_col)) - 1) * GRID_CELL_UNITS
    fallback_y = area.position_y if area.position_y is not None else (max(1, int(area.grid_row)) - 1) * GRID_CELL_UNITS
    area.grid_range = rect_units_to_excel_range(fallback_x, fallback_y, area.width, area.height)

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
