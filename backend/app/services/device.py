"""Device service."""

import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Area, Device
from app.schemas.device import DeviceCreate, DeviceUpdate
from app.services.grid_excel import (
    GRID_CELL_UNITS,
    excel_range_to_rect_units,
    normalize_excel_range,
    rect_units_to_excel_range,
)


async def get_devices(db: AsyncSession, project_id: str) -> list[Device]:
    """Lấy danh sách devices của project."""
    result = await db.execute(
        select(Device)
        .where(Device.project_id == project_id)
        .options(selectinload(Device.area))
        .order_by(Device.name)
    )
    return list(result.scalars().all())


async def get_device_by_id(db: AsyncSession, device_id: str) -> Optional[Device]:
    """Lấy device theo ID."""
    result = await db.execute(
        select(Device).where(Device.id == device_id).options(selectinload(Device.area))
    )
    return result.scalar_one_or_none()


async def get_device_by_name(db: AsyncSession, project_id: str, name: str) -> Optional[Device]:
    """Lấy device theo tên trong project."""
    result = await db.execute(
        select(Device)
        .where(Device.project_id == project_id, Device.name == name)
        .options(selectinload(Device.area))
    )
    return result.scalar_one_or_none()


async def create_device(
    db: AsyncSession,
    project_id: str,
    area: Area,
    data: DeviceCreate,
) -> Device:
    """Tạo device mới."""
    color_rgb_json = None
    if data.color_rgb:
        color_rgb_json = json.dumps(data.color_rgb)

    position_x = data.position_x
    position_y = data.position_y
    width = data.width
    height = data.height
    grid_range = data.grid_range

    if grid_range:
        grid_range = normalize_excel_range(grid_range)
        rect = excel_range_to_rect_units(grid_range)
        position_x = rect["x"]
        position_y = rect["y"]
        width = rect["width"]
        height = rect["height"]
    else:
        fallback_x = position_x if position_x is not None else (max(1, int(area.grid_col)) - 1) * GRID_CELL_UNITS
        fallback_y = position_y if position_y is not None else (max(1, int(area.grid_row)) - 1) * GRID_CELL_UNITS
        grid_range = rect_units_to_excel_range(fallback_x, fallback_y, width, height)

    device = Device(
        project_id=project_id,
        area_id=area.id,
        name=data.name,
        device_type=data.device_type,
        grid_range=grid_range,
        position_x=position_x,
        position_y=position_y,
        width=width,
        height=height,
        color_rgb_json=color_rgb_json,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


async def update_device(
    db: AsyncSession,
    device: Device,
    data: DeviceUpdate,
    area: Optional[Area] = None,
) -> Device:
    """Cập nhật device."""
    update_data = data.model_dump(exclude_unset=True)

    # Handle area_name -> area_id
    if "area_name" in update_data:
        update_data.pop("area_name")
        if area:
            device.area_id = area.id

    # Handle color_rgb
    if "color_rgb" in update_data:
        color_rgb = update_data.pop("color_rgb")
        if color_rgb:
            device.color_rgb_json = json.dumps(color_rgb)
        else:
            device.color_rgb_json = None

    if "grid_range" in update_data:
        grid_range = update_data.pop("grid_range")
        if grid_range:
            normalized = normalize_excel_range(grid_range)
            rect = excel_range_to_rect_units(normalized)
            update_data["grid_range"] = normalized
            update_data["position_x"] = rect["x"]
            update_data["position_y"] = rect["y"]
            update_data["width"] = rect["width"]
            update_data["height"] = rect["height"]

    for field, value in update_data.items():
        setattr(device, field, value)

    fallback_x = device.position_x if device.position_x is not None else 0.0
    fallback_y = device.position_y if device.position_y is not None else 0.0
    device.grid_range = rect_units_to_excel_range(fallback_x, fallback_y, device.width, device.height)

    await db.commit()
    await db.refresh(device)
    return device


async def delete_device(db: AsyncSession, device: Device) -> None:
    """Xóa device."""
    await db.delete(device)
    await db.commit()


def parse_device_color(device: Device) -> Optional[list[int]]:
    """Parse color RGB từ device."""
    if not device.color_rgb_json:
        return None
    try:
        return json.loads(device.color_rgb_json)
    except Exception:
        return None
