"""API endpoints cho Port Channels."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.schemas.port_channel import (
    PortChannelBulkCreate,
    PortChannelBulkResponse,
    PortChannelCreate,
    PortChannelResponse,
    PortChannelUpdate,
)
from app.services import port_channel as port_channel_service
from app.services import project as project_service

router = APIRouter(prefix="/projects/{project_id}/port-channels", tags=["port-channels"])


def extract_channel_number(name: str) -> Optional[int]:
    import re

    match = re.search(r"(\d+)$", name)
    if not match:
        return None
    return int(match.group(1))


def build_port_channel_response(port_channel, device_name=None):
    """Build response với thông tin bổ sung."""
    members = port_channel_service.parse_members(port_channel.members_json)
    return PortChannelResponse(
        id=port_channel.id,
        project_id=port_channel.project_id,
        device_id=port_channel.device_id,
        device_name=device_name,
        name=port_channel.name,
        channel_number=port_channel.channel_number,
        mode=port_channel.mode,
        members=members,
        created_at=port_channel.created_at,
    )


@router.get("", response_model=list[PortChannelResponse])
async def list_port_channels(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
):
    """Lấy danh sách Port Channels của project."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    port_channels = await port_channel_service.get_port_channels_by_project(
        db, project_id, skip, limit
    )

    result = []
    for pc in port_channels:
        from sqlalchemy import select
        from app.db.models import Device

        device_result = await db.execute(select(Device).where(Device.id == pc.device_id))
        device = device_result.scalar_one_or_none()
        result.append(build_port_channel_response(pc, device_name=device.name if device else None))

    return result


@router.get("/{port_channel_id}", response_model=PortChannelResponse)
async def get_port_channel(
    project_id: str,
    port_channel_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Lấy thông tin Port Channel."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    port_channel = await port_channel_service.get_port_channel(db, port_channel_id)
    if not port_channel or port_channel.project_id != project_id:
        raise HTTPException(status_code=404, detail="Port Channel không tồn tại")

    from sqlalchemy import select
    from app.db.models import Device

    device_result = await db.execute(select(Device).where(Device.id == port_channel.device_id))
    device = device_result.scalar_one_or_none()

    return build_port_channel_response(
        port_channel, device_name=device.name if device else None
    )


@router.post("", response_model=PortChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_port_channel(
    project_id: str,
    data: PortChannelCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Tạo Port Channel mới."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    device = await port_channel_service.get_device_by_name(db, project_id, data.device_name)
    if not device:
        raise HTTPException(
            status_code=400,
            detail=f"Device '{data.device_name}' không tồn tại trong project",
        )

    parsed_number = extract_channel_number(data.name)
    channel_number = data.channel_number or parsed_number
    if channel_number is None:
        raise HTTPException(status_code=400, detail="Không xác định được channel_number")
    if channel_number < 1 or channel_number > 256:
        raise HTTPException(status_code=400, detail="channel_number phải từ 1 đến 256")
    if parsed_number is not None and data.channel_number is not None:
        if parsed_number != data.channel_number:
            raise HTTPException(status_code=400, detail="Tên và channel_number không khớp")

    existing_by_name = await port_channel_service.get_port_channel_by_name(
        db, project_id, device.id, data.name
    )
    if existing_by_name:
        raise HTTPException(status_code=400, detail="Port Channel đã tồn tại trong device")

    existing_by_number = await port_channel_service.get_port_channel_by_number(
        db, project_id, device.id, channel_number
    )
    if existing_by_number:
        raise HTTPException(status_code=400, detail="channel_number đã tồn tại trong device")

    port_channel = await port_channel_service.create_port_channel(
        db, project_id, device.id, data, channel_number
    )
    return build_port_channel_response(port_channel, device_name=device.name)


@router.post("/bulk", response_model=PortChannelBulkResponse)
async def bulk_create_port_channels(
    project_id: str,
    data: PortChannelBulkCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Tạo nhiều Port Channels cùng lúc."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    created = []
    errors = []

    for idx, pc_data in enumerate(data.port_channels):
        try:
            device = await port_channel_service.get_device_by_name(
                db, project_id, pc_data.device_name
            )
            if not device:
                errors.append({
                    "index": idx,
                    "data": pc_data.model_dump(),
                    "error": f"Device '{pc_data.device_name}' không tồn tại",
                })
                continue

            parsed_number = extract_channel_number(pc_data.name)
            channel_number = pc_data.channel_number or parsed_number
            if channel_number is None:
                errors.append({
                    "index": idx,
                    "data": pc_data.model_dump(),
                    "error": "Không xác định được channel_number",
                })
                continue
            if channel_number < 1 or channel_number > 256:
                errors.append({
                    "index": idx,
                    "data": pc_data.model_dump(),
                    "error": "channel_number phải từ 1 đến 256",
                })
                continue
            if parsed_number is not None and pc_data.channel_number is not None:
                if parsed_number != pc_data.channel_number:
                    errors.append({
                        "index": idx,
                        "data": pc_data.model_dump(),
                        "error": "Tên và channel_number không khớp",
                    })
                    continue

            existing_by_name = await port_channel_service.get_port_channel_by_name(
                db, project_id, device.id, pc_data.name
            )
            if existing_by_name:
                errors.append({
                    "index": idx,
                    "data": pc_data.model_dump(),
                    "error": "Port Channel đã tồn tại trong device",
                })
                continue

            existing_by_number = await port_channel_service.get_port_channel_by_number(
                db, project_id, device.id, channel_number
            )
            if existing_by_number:
                errors.append({
                    "index": idx,
                    "data": pc_data.model_dump(),
                    "error": "channel_number đã tồn tại trong device",
                })
                continue

            port_channel = await port_channel_service.create_port_channel(
                db, project_id, device.id, pc_data, channel_number
            )
            created.append({
                "id": port_channel.id,
                "device_name": device.name,
                "name": port_channel.name,
                "channel_number": port_channel.channel_number,
            })
        except Exception as e:
            errors.append({
                "index": idx,
                "data": pc_data.model_dump(),
                "error": str(e),
            })

    return PortChannelBulkResponse(
        success_count=len(created),
        error_count=len(errors),
        created=created,
        errors=errors,
    )


@router.put("/{port_channel_id}", response_model=PortChannelResponse)
async def update_port_channel(
    project_id: str,
    port_channel_id: str,
    data: PortChannelUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Cập nhật Port Channel."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    port_channel = await port_channel_service.get_port_channel(db, port_channel_id)
    if not port_channel or port_channel.project_id != project_id:
        raise HTTPException(status_code=404, detail="Port Channel không tồn tại")

    device_id = None
    device_name = None

    if data.device_name:
        device = await port_channel_service.get_device_by_name(db, project_id, data.device_name)
        if not device:
            raise HTTPException(
                status_code=400,
                detail=f"Device '{data.device_name}' không tồn tại trong project",
            )
        device_id = device.id
        device_name = device.name
    else:
        from sqlalchemy import select
        from app.db.models import Device

        device_result = await db.execute(select(Device).where(Device.id == port_channel.device_id))
        device = device_result.scalar_one_or_none()
        device_name = device.name if device else None

    effective_name = data.name or port_channel.name
    parsed_number = extract_channel_number(effective_name)
    if parsed_number is None:
        raise HTTPException(status_code=400, detail="Tên port-channel không hợp lệ")
    if parsed_number < 1 or parsed_number > 256:
        raise HTTPException(status_code=400, detail="channel_number phải từ 1 đến 256")

    if data.channel_number is not None and parsed_number != data.channel_number:
        raise HTTPException(status_code=400, detail="Tên và channel_number không khớp")

    channel_number = data.channel_number
    if data.channel_number is None and data.name is not None:
        channel_number = parsed_number

    target_device_id = device_id or port_channel.device_id

    if data.name is not None or device_id is not None:
        existing_by_name = await port_channel_service.get_port_channel_by_name(
            db, project_id, target_device_id, effective_name
        )
        if existing_by_name and existing_by_name.id != port_channel.id:
            raise HTTPException(status_code=400, detail="Port Channel đã tồn tại trong device")

    if channel_number is not None:
        existing_by_number = await port_channel_service.get_port_channel_by_number(
            db, project_id, target_device_id, channel_number
        )
        if existing_by_number and existing_by_number.id != port_channel.id:
            raise HTTPException(status_code=400, detail="channel_number đã tồn tại trong device")

    port_channel = await port_channel_service.update_port_channel(
        db, port_channel, data, device_id=device_id, channel_number=channel_number
    )

    return build_port_channel_response(port_channel, device_name=device_name)


@router.delete("/{port_channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_port_channel(
    project_id: str,
    port_channel_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Xóa Port Channel."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    port_channel = await port_channel_service.get_port_channel(db, port_channel_id)
    if not port_channel or port_channel.project_id != project_id:
        raise HTTPException(status_code=404, detail="Port Channel không tồn tại")

    await port_channel_service.delete_port_channel(db, port_channel)
