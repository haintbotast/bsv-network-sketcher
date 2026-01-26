"""L1 Link service."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Device, L1Link
from app.schemas.link import L1LinkCreate, L1LinkUpdate


async def get_links(db: AsyncSession, project_id: str) -> list[L1Link]:
    """Lấy danh sách links của project."""
    result = await db.execute(
        select(L1Link)
        .where(L1Link.project_id == project_id)
        .options(selectinload(L1Link.from_device), selectinload(L1Link.to_device))
        .order_by(L1Link.created_at)
    )
    return list(result.scalars().all())


async def get_link_by_id(db: AsyncSession, link_id: str) -> Optional[L1Link]:
    """Lấy link theo ID."""
    result = await db.execute(
        select(L1Link)
        .where(L1Link.id == link_id)
        .options(selectinload(L1Link.from_device), selectinload(L1Link.to_device))
    )
    return result.scalar_one_or_none()


async def check_link_exists(
    db: AsyncSession,
    project_id: str,
    from_device_id: str,
    from_port: str,
    to_device_id: str,
    to_port: str,
) -> bool:
    """Kiểm tra link đã tồn tại chưa (cả 2 chiều)."""
    # Check chiều 1
    result = await db.execute(
        select(L1Link).where(
            L1Link.project_id == project_id,
            L1Link.from_device_id == from_device_id,
            L1Link.from_port == from_port,
            L1Link.to_device_id == to_device_id,
            L1Link.to_port == to_port,
        )
    )
    if result.scalar_one_or_none():
        return True

    # Check chiều ngược
    result = await db.execute(
        select(L1Link).where(
            L1Link.project_id == project_id,
            L1Link.from_device_id == to_device_id,
            L1Link.from_port == to_port,
            L1Link.to_device_id == from_device_id,
            L1Link.to_port == from_port,
        )
    )
    return result.scalar_one_or_none() is not None


async def check_port_in_use(
    db: AsyncSession,
    project_id: str,
    device_id: str,
    port: str,
    exclude_link_id: Optional[str] = None,
) -> bool:
    """Kiểm tra port đã được sử dụng trong link khác chưa."""
    # Check as from_port
    query = select(L1Link).where(
        L1Link.project_id == project_id,
        L1Link.from_device_id == device_id,
        L1Link.from_port == port,
    )
    if exclude_link_id:
        query = query.where(L1Link.id != exclude_link_id)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        return True

    # Check as to_port
    query = select(L1Link).where(
        L1Link.project_id == project_id,
        L1Link.to_device_id == device_id,
        L1Link.to_port == port,
    )
    if exclude_link_id:
        query = query.where(L1Link.id != exclude_link_id)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def create_link(
    db: AsyncSession,
    project_id: str,
    from_device: Device,
    to_device: Device,
    data: L1LinkCreate,
) -> L1Link:
    """Tạo link mới."""
    link = L1Link(
        project_id=project_id,
        from_device_id=from_device.id,
        from_port=data.from_port,
        to_device_id=to_device.id,
        to_port=data.to_port,
        purpose=data.purpose,
        line_style=data.line_style,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


async def update_link(
    db: AsyncSession,
    link: L1Link,
    data: L1LinkUpdate,
    from_device: Optional[Device] = None,
    to_device: Optional[Device] = None,
) -> L1Link:
    """Cập nhật link."""
    update_data = data.model_dump(exclude_unset=True)

    # Handle device references
    if "from_device" in update_data:
        update_data.pop("from_device")
        if from_device:
            link.from_device_id = from_device.id

    if "to_device" in update_data:
        update_data.pop("to_device")
        if to_device:
            link.to_device_id = to_device.id

    for field, value in update_data.items():
        setattr(link, field, value)

    await db.commit()
    await db.refresh(link)
    return link


async def delete_link(db: AsyncSession, link: L1Link) -> None:
    """Xóa link."""
    await db.delete(link)
    await db.commit()
