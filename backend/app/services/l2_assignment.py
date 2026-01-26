"""Service cho Interface L2 Assignment CRUD."""

import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device, InterfaceL2Assignment, L2Segment
from app.schemas.l2_assignment import InterfaceL2AssignmentCreate, InterfaceL2AssignmentUpdate


async def get_assignment(
    db: AsyncSession, assignment_id: str
) -> Optional[InterfaceL2Assignment]:
    """Lấy L2 assignment theo ID."""
    result = await db.execute(
        select(InterfaceL2Assignment).where(InterfaceL2Assignment.id == assignment_id)
    )
    return result.scalar_one_or_none()


async def get_assignment_by_interface(
    db: AsyncSession, project_id: str, device_id: str, interface_name: str
) -> Optional[InterfaceL2Assignment]:
    """Lấy L2 assignment theo device và interface."""
    result = await db.execute(
        select(InterfaceL2Assignment).where(
            InterfaceL2Assignment.project_id == project_id,
            InterfaceL2Assignment.device_id == device_id,
            InterfaceL2Assignment.interface_name == interface_name,
        )
    )
    return result.scalar_one_or_none()


async def get_assignments_by_project(
    db: AsyncSession,
    project_id: str,
    skip: int = 0,
    limit: int = 100,
) -> list[InterfaceL2Assignment]:
    """Lấy danh sách L2 assignments theo project."""
    result = await db.execute(
        select(InterfaceL2Assignment)
        .where(InterfaceL2Assignment.project_id == project_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_assignments_by_segment(
    db: AsyncSession, segment_id: str
) -> list[InterfaceL2Assignment]:
    """Lấy danh sách assignments theo L2 segment."""
    result = await db.execute(
        select(InterfaceL2Assignment).where(
            InterfaceL2Assignment.l2_segment_id == segment_id
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


async def create_assignment(
    db: AsyncSession,
    project_id: str,
    device_id: str,
    data: InterfaceL2AssignmentCreate,
) -> InterfaceL2Assignment:
    """Tạo L2 assignment mới."""
    allowed_vlans_json = None
    if data.allowed_vlans:
        allowed_vlans_json = json.dumps(data.allowed_vlans)

    assignment = InterfaceL2Assignment(
        project_id=project_id,
        device_id=device_id,
        interface_name=data.interface_name,
        l2_segment_id=data.l2_segment_id,
        port_mode=data.port_mode,
        native_vlan=data.native_vlan,
        allowed_vlans_json=allowed_vlans_json,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


async def update_assignment(
    db: AsyncSession,
    assignment: InterfaceL2Assignment,
    data: InterfaceL2AssignmentUpdate,
    device_id: Optional[str] = None,
) -> InterfaceL2Assignment:
    """Cập nhật L2 assignment."""
    update_data = data.model_dump(exclude_unset=True, exclude={"device_name", "allowed_vlans"})

    # Handle device_id nếu device_name thay đổi
    if device_id:
        update_data["device_id"] = device_id

    # Handle allowed_vlans
    if data.allowed_vlans is not None:
        update_data["allowed_vlans_json"] = json.dumps(data.allowed_vlans)

    for field, value in update_data.items():
        setattr(assignment, field, value)

    await db.commit()
    await db.refresh(assignment)
    return assignment


async def delete_assignment(db: AsyncSession, assignment: InterfaceL2Assignment) -> None:
    """Xóa L2 assignment."""
    await db.delete(assignment)
    await db.commit()


async def count_assignments_by_project(db: AsyncSession, project_id: str) -> int:
    """Đếm số L2 assignments trong project."""
    from sqlalchemy import func

    result = await db.execute(
        select(func.count())
        .select_from(InterfaceL2Assignment)
        .where(InterfaceL2Assignment.project_id == project_id)
    )
    return result.scalar() or 0


def parse_allowed_vlans(allowed_vlans_json: Optional[str]) -> Optional[list[int]]:
    """Parse allowed_vlans từ JSON string."""
    if not allowed_vlans_json:
        return None
    try:
        return json.loads(allowed_vlans_json)
    except json.JSONDecodeError:
        return None
