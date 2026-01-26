"""Service cho Virtual Port CRUD."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device, VirtualPort
from app.schemas.virtual_port import VirtualPortCreate, VirtualPortUpdate


async def get_virtual_port(
    db: AsyncSession, virtual_port_id: str
) -> Optional[VirtualPort]:
    """Lấy Virtual Port theo ID."""
    result = await db.execute(select(VirtualPort).where(VirtualPort.id == virtual_port_id))
    return result.scalar_one_or_none()


async def get_virtual_port_by_name(
    db: AsyncSession, project_id: str, device_id: str, name: str
) -> Optional[VirtualPort]:
    """Lấy Virtual Port theo tên trong device."""
    result = await db.execute(
        select(VirtualPort).where(
            VirtualPort.project_id == project_id,
            VirtualPort.device_id == device_id,
            VirtualPort.name == name,
        )
    )
    return result.scalar_one_or_none()


async def get_virtual_ports_by_project(
    db: AsyncSession,
    project_id: str,
    skip: int = 0,
    limit: int = 100,
) -> list[VirtualPort]:
    """Lấy danh sách Virtual Ports theo project."""
    result = await db.execute(
        select(VirtualPort)
        .where(VirtualPort.project_id == project_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_virtual_ports_by_device(
    db: AsyncSession, device_id: str
) -> list[VirtualPort]:
    """Lấy danh sách Virtual Ports theo device."""
    result = await db.execute(
        select(VirtualPort).where(VirtualPort.device_id == device_id)
    )
    return list(result.scalars().all())


async def get_device_by_name(
    db: AsyncSession, project_id: str, device_name: str
) -> Optional[Device]:
    """Lấy device theo tên trong project."""
    result = await db.execute(
        select(Device).where(
            Device.project_id == project_id,
            Device.name == device_name,
        )
    )
    return result.scalar_one_or_none()


async def create_virtual_port(
    db: AsyncSession,
    project_id: str,
    device_id: str,
    data: VirtualPortCreate,
) -> VirtualPort:
    """Tạo Virtual Port mới."""
    virtual_port = VirtualPort(
        project_id=project_id,
        device_id=device_id,
        name=data.name,
        interface_type=data.interface_type,
    )
    db.add(virtual_port)
    await db.commit()
    await db.refresh(virtual_port)
    return virtual_port


async def update_virtual_port(
    db: AsyncSession,
    virtual_port: VirtualPort,
    data: VirtualPortUpdate,
    device_id: Optional[str] = None,
) -> VirtualPort:
    """Cập nhật Virtual Port."""
    update_data = data.model_dump(exclude_unset=True, exclude={"device_name"})

    if device_id:
        update_data["device_id"] = device_id

    for field, value in update_data.items():
        setattr(virtual_port, field, value)

    await db.commit()
    await db.refresh(virtual_port)
    return virtual_port


async def delete_virtual_port(db: AsyncSession, virtual_port: VirtualPort) -> None:
    """Xóa Virtual Port."""
    await db.delete(virtual_port)
    await db.commit()


async def count_virtual_ports_by_project(db: AsyncSession, project_id: str) -> int:
    """Đếm số Virtual Ports trong project."""
    from sqlalchemy import func

    result = await db.execute(
        select(func.count())
        .select_from(VirtualPort)
        .where(VirtualPort.project_id == project_id)
    )
    return result.scalar() or 0
