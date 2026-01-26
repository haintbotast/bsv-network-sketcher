"""Service cho Port Channel CRUD."""

import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device, PortChannel
from app.schemas.port_channel import PortChannelCreate, PortChannelUpdate


async def get_port_channel(
    db: AsyncSession, port_channel_id: str
) -> Optional[PortChannel]:
    """Lấy Port Channel theo ID."""
    result = await db.execute(select(PortChannel).where(PortChannel.id == port_channel_id))
    return result.scalar_one_or_none()


async def get_port_channel_by_name(
    db: AsyncSession, project_id: str, device_id: str, name: str
) -> Optional[PortChannel]:
    """Lấy Port Channel theo tên trong device."""
    result = await db.execute(
        select(PortChannel).where(
            PortChannel.project_id == project_id,
            PortChannel.device_id == device_id,
            PortChannel.name == name,
        )
    )
    return result.scalar_one_or_none()


async def get_port_channel_by_number(
    db: AsyncSession, project_id: str, device_id: str, channel_number: int
) -> Optional[PortChannel]:
    """Lấy Port Channel theo số kênh trong device."""
    result = await db.execute(
        select(PortChannel).where(
            PortChannel.project_id == project_id,
            PortChannel.device_id == device_id,
            PortChannel.channel_number == channel_number,
        )
    )
    return result.scalar_one_or_none()


async def get_port_channels_by_project(
    db: AsyncSession,
    project_id: str,
    skip: int = 0,
    limit: int = 100,
) -> list[PortChannel]:
    """Lấy danh sách Port Channels theo project."""
    result = await db.execute(
        select(PortChannel)
        .where(PortChannel.project_id == project_id)
        .order_by(PortChannel.channel_number)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_port_channels_by_device(
    db: AsyncSession, device_id: str
) -> list[PortChannel]:
    """Lấy danh sách Port Channels theo device."""
    result = await db.execute(
        select(PortChannel).where(PortChannel.device_id == device_id)
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


async def create_port_channel(
    db: AsyncSession,
    project_id: str,
    device_id: str,
    data: PortChannelCreate,
    channel_number: int,
) -> PortChannel:
    """Tạo Port Channel mới."""
    members_json = json.dumps(data.members)
    port_channel = PortChannel(
        project_id=project_id,
        device_id=device_id,
        name=data.name,
        channel_number=channel_number,
        mode=data.mode,
        members_json=members_json,
    )
    db.add(port_channel)
    await db.commit()
    await db.refresh(port_channel)
    return port_channel


async def update_port_channel(
    db: AsyncSession,
    port_channel: PortChannel,
    data: PortChannelUpdate,
    device_id: Optional[str] = None,
    channel_number: Optional[int] = None,
) -> PortChannel:
    """Cập nhật Port Channel."""
    update_data = data.model_dump(exclude_unset=True, exclude={"device_name", "members"})

    if device_id:
        update_data["device_id"] = device_id

    if channel_number is not None:
        update_data["channel_number"] = channel_number

    if data.members is not None:
        update_data["members_json"] = json.dumps(data.members)

    for field, value in update_data.items():
        setattr(port_channel, field, value)

    await db.commit()
    await db.refresh(port_channel)
    return port_channel


async def delete_port_channel(db: AsyncSession, port_channel: PortChannel) -> None:
    """Xóa Port Channel."""
    await db.delete(port_channel)
    await db.commit()


async def count_port_channels_by_project(db: AsyncSession, project_id: str) -> int:
    """Đếm số Port Channels trong project."""
    from sqlalchemy import func

    result = await db.execute(
        select(func.count())
        .select_from(PortChannel)
        .where(PortChannel.project_id == project_id)
    )
    return result.scalar() or 0


def parse_members(members_json: Optional[str]) -> list[str]:
    """Parse members từ JSON string."""
    if not members_json:
        return []
    try:
        return json.loads(members_json)
    except json.JSONDecodeError:
        return []
