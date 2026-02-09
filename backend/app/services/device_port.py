"""Device port service."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Device, DevicePort
from app.schemas.device_port import DevicePortCreate, DevicePortUpdate


async def get_ports_by_project(db: AsyncSession, project_id: str) -> list[DevicePort]:
    """Lấy danh sách port theo project."""
    result = await db.execute(
        select(DevicePort)
        .where(DevicePort.project_id == project_id)
        .options(selectinload(DevicePort.device))
        .order_by(DevicePort.device_id, DevicePort.name)
    )
    return list(result.scalars().all())


async def get_ports_by_device(db: AsyncSession, project_id: str, device_id: str) -> list[DevicePort]:
    """Lấy danh sách port của một device."""
    result = await db.execute(
        select(DevicePort)
        .where(DevicePort.project_id == project_id, DevicePort.device_id == device_id)
        .options(selectinload(DevicePort.device))
        .order_by(DevicePort.name)
    )
    return list(result.scalars().all())


async def get_port_by_id(db: AsyncSession, project_id: str, port_id: str) -> Optional[DevicePort]:
    """Lấy port theo ID."""
    result = await db.execute(
        select(DevicePort)
        .where(DevicePort.id == port_id, DevicePort.project_id == project_id)
        .options(selectinload(DevicePort.device))
    )
    return result.scalar_one_or_none()


async def get_port_by_name(
    db: AsyncSession,
    project_id: str,
    device_id: str,
    port_name: str,
) -> Optional[DevicePort]:
    """Lấy port theo tên trong cùng device/project."""
    result = await db.execute(
        select(DevicePort).where(
            DevicePort.project_id == project_id,
            DevicePort.device_id == device_id,
            DevicePort.name == port_name.strip(),
        )
    )
    return result.scalar_one_or_none()


async def create_port(
    db: AsyncSession,
    project_id: str,
    device: Device,
    data: DevicePortCreate,
) -> DevicePort:
    """Tạo port mới."""
    port = DevicePort(
        project_id=project_id,
        device_id=device.id,
        name=data.name.strip(),
        side=data.side,
        offset_ratio=data.offset_ratio,
    )
    db.add(port)
    await db.commit()
    await db.refresh(port)
    return port


async def update_port(db: AsyncSession, port: DevicePort, data: DevicePortUpdate) -> DevicePort:
    """Cập nhật port."""
    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] is not None:
        update_data["name"] = update_data["name"].strip()

    for field, value in update_data.items():
        setattr(port, field, value)

    await db.commit()
    await db.refresh(port)
    return port


async def delete_port(db: AsyncSession, port: DevicePort) -> None:
    """Xóa port."""
    await db.delete(port)
    await db.commit()
