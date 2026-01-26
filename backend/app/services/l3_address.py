"""Service cho L3 Address CRUD."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device, L3Address
from app.schemas.l3_address import L3AddressCreate, L3AddressUpdate


async def get_address(db: AsyncSession, address_id: str) -> Optional[L3Address]:
    """Lấy L3 address theo ID."""
    result = await db.execute(select(L3Address).where(L3Address.id == address_id))
    return result.scalar_one_or_none()


async def get_addresses_by_project(
    db: AsyncSession,
    project_id: str,
    skip: int = 0,
    limit: int = 100,
) -> list[L3Address]:
    """Lấy danh sách L3 addresses theo project."""
    result = await db.execute(
        select(L3Address)
        .where(L3Address.project_id == project_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_addresses_by_device(
    db: AsyncSession, device_id: str
) -> list[L3Address]:
    """Lấy danh sách L3 addresses theo device."""
    result = await db.execute(
        select(L3Address).where(L3Address.device_id == device_id)
    )
    return list(result.scalars().all())


async def get_addresses_by_interface(
    db: AsyncSession, device_id: str, interface_name: str
) -> list[L3Address]:
    """Lấy danh sách L3 addresses theo interface."""
    result = await db.execute(
        select(L3Address).where(
            L3Address.device_id == device_id,
            L3Address.interface_name == interface_name,
        )
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


async def create_address(
    db: AsyncSession,
    project_id: str,
    device_id: str,
    data: L3AddressCreate,
) -> L3Address:
    """Tạo L3 address mới."""
    address = L3Address(
        project_id=project_id,
        device_id=device_id,
        interface_name=data.interface_name,
        ip_address=data.ip_address,
        prefix_length=data.prefix_length,
        is_secondary=data.is_secondary,
        description=data.description,
    )
    db.add(address)
    await db.commit()
    await db.refresh(address)
    return address


async def update_address(
    db: AsyncSession,
    address: L3Address,
    data: L3AddressUpdate,
    device_id: Optional[str] = None,
) -> L3Address:
    """Cập nhật L3 address."""
    update_data = data.model_dump(exclude_unset=True, exclude={"device_name"})

    # Handle device_id nếu device_name thay đổi
    if device_id:
        update_data["device_id"] = device_id

    for field, value in update_data.items():
        setattr(address, field, value)

    await db.commit()
    await db.refresh(address)
    return address


async def delete_address(db: AsyncSession, address: L3Address) -> None:
    """Xóa L3 address."""
    await db.delete(address)
    await db.commit()


async def count_addresses_by_project(db: AsyncSession, project_id: str) -> int:
    """Đếm số L3 addresses trong project."""
    from sqlalchemy import func

    result = await db.execute(
        select(func.count())
        .select_from(L3Address)
        .where(L3Address.project_id == project_id)
    )
    return result.scalar() or 0
