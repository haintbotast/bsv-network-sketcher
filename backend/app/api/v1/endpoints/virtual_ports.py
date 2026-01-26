"""API endpoints cho Virtual Ports."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.schemas.virtual_port import (
    VirtualPortBulkCreate,
    VirtualPortBulkResponse,
    VirtualPortCreate,
    VirtualPortResponse,
    VirtualPortUpdate,
)
from app.services import project as project_service
from app.services import virtual_port as virtual_port_service

router = APIRouter(prefix="/projects/{project_id}/virtual-ports", tags=["virtual-ports"])


def validate_name_for_type(name: str, interface_type: str) -> bool:
    import re

    patterns = {
        "Vlan": r"^Vlan\s*\d+$",
        "Loopback": r"^Loopback\s*\d+$",
        "Port-Channel": r"^Port-[Cc]hannel\s*\d+$",
    }
    pattern = patterns.get(interface_type)
    if not pattern:
        return False
    return re.match(pattern, name) is not None


def build_virtual_port_response(virtual_port, device_name=None):
    """Build response với thông tin bổ sung."""
    return VirtualPortResponse(
        id=virtual_port.id,
        project_id=virtual_port.project_id,
        device_id=virtual_port.device_id,
        device_name=device_name,
        name=virtual_port.name,
        interface_type=virtual_port.interface_type,
        created_at=virtual_port.created_at,
    )


@router.get("", response_model=list[VirtualPortResponse])
async def list_virtual_ports(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
):
    """Lấy danh sách Virtual Ports của project."""
    project = await project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    virtual_ports = await virtual_port_service.get_virtual_ports_by_project(
        db, project_id, skip, limit
    )

    result = []
    for vp in virtual_ports:
        from sqlalchemy import select
        from app.db.models import Device

        device_result = await db.execute(select(Device).where(Device.id == vp.device_id))
        device = device_result.scalar_one_or_none()
        result.append(build_virtual_port_response(vp, device_name=device.name if device else None))

    return result


@router.get("/{virtual_port_id}", response_model=VirtualPortResponse)
async def get_virtual_port(
    project_id: str,
    virtual_port_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Lấy thông tin Virtual Port."""
    project = await project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    virtual_port = await virtual_port_service.get_virtual_port(db, virtual_port_id)
    if not virtual_port or virtual_port.project_id != project_id:
        raise HTTPException(status_code=404, detail="Virtual Port không tồn tại")

    from sqlalchemy import select
    from app.db.models import Device

    device_result = await db.execute(select(Device).where(Device.id == virtual_port.device_id))
    device = device_result.scalar_one_or_none()

    return build_virtual_port_response(virtual_port, device_name=device.name if device else None)


@router.post("", response_model=VirtualPortResponse, status_code=status.HTTP_201_CREATED)
async def create_virtual_port(
    project_id: str,
    data: VirtualPortCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Tạo Virtual Port mới."""
    project = await project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    if not validate_name_for_type(data.name, data.interface_type):
        raise HTTPException(status_code=400, detail="Tên không khớp interface_type")

    device = await virtual_port_service.get_device_by_name(db, project_id, data.device_name)
    if not device:
        raise HTTPException(
            status_code=400,
            detail=f"Device '{data.device_name}' không tồn tại trong project",
        )

    existing = await virtual_port_service.get_virtual_port_by_name(
        db, project_id, device.id, data.name
    )
    if existing:
        raise HTTPException(status_code=400, detail="Virtual Port đã tồn tại trong device")

    virtual_port = await virtual_port_service.create_virtual_port(
        db, project_id, device.id, data
    )
    return build_virtual_port_response(virtual_port, device_name=device.name)


@router.post("/bulk", response_model=VirtualPortBulkResponse)
async def bulk_create_virtual_ports(
    project_id: str,
    data: VirtualPortBulkCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Tạo nhiều Virtual Ports cùng lúc."""
    project = await project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    created = []
    errors = []

    for idx, vp_data in enumerate(data.virtual_ports):
        try:
            if not validate_name_for_type(vp_data.name, vp_data.interface_type):
                errors.append({
                    "index": idx,
                    "data": vp_data.model_dump(),
                    "error": "Tên không khớp interface_type",
                })
                continue

            device = await virtual_port_service.get_device_by_name(
                db, project_id, vp_data.device_name
            )
            if not device:
                errors.append({
                    "index": idx,
                    "data": vp_data.model_dump(),
                    "error": f"Device '{vp_data.device_name}' không tồn tại",
                })
                continue

            existing = await virtual_port_service.get_virtual_port_by_name(
                db, project_id, device.id, vp_data.name
            )
            if existing:
                errors.append({
                    "index": idx,
                    "data": vp_data.model_dump(),
                    "error": "Virtual Port đã tồn tại trong device",
                })
                continue

            virtual_port = await virtual_port_service.create_virtual_port(
                db, project_id, device.id, vp_data
            )
            created.append({
                "id": virtual_port.id,
                "device_name": device.name,
                "name": virtual_port.name,
                "interface_type": virtual_port.interface_type,
            })
        except Exception as e:
            errors.append({
                "index": idx,
                "data": vp_data.model_dump(),
                "error": str(e),
            })

    return VirtualPortBulkResponse(
        success_count=len(created),
        error_count=len(errors),
        created=created,
        errors=errors,
    )


@router.put("/{virtual_port_id}", response_model=VirtualPortResponse)
async def update_virtual_port(
    project_id: str,
    virtual_port_id: str,
    data: VirtualPortUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Cập nhật Virtual Port."""
    project = await project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    virtual_port = await virtual_port_service.get_virtual_port(db, virtual_port_id)
    if not virtual_port or virtual_port.project_id != project_id:
        raise HTTPException(status_code=404, detail="Virtual Port không tồn tại")

    device_id = None
    device_name = None

    if data.device_name:
        device = await virtual_port_service.get_device_by_name(db, project_id, data.device_name)
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

        device_result = await db.execute(select(Device).where(Device.id == virtual_port.device_id))
        device = device_result.scalar_one_or_none()
        device_name = device.name if device else None

    effective_name = data.name or virtual_port.name
    effective_type = data.interface_type or virtual_port.interface_type

    if not validate_name_for_type(effective_name, effective_type):
        raise HTTPException(status_code=400, detail="Tên không khớp interface_type")

    target_device_id = device_id or virtual_port.device_id

    if data.name is not None or device_id is not None:
        existing = await virtual_port_service.get_virtual_port_by_name(
            db, project_id, target_device_id, effective_name
        )
        if existing and existing.id != virtual_port.id:
            raise HTTPException(status_code=400, detail="Virtual Port đã tồn tại trong device")

    virtual_port = await virtual_port_service.update_virtual_port(
        db, virtual_port, data, device_id=device_id
    )

    return build_virtual_port_response(virtual_port, device_name=device_name)


@router.delete("/{virtual_port_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_virtual_port(
    project_id: str,
    virtual_port_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Xóa Virtual Port."""
    project = await project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    virtual_port = await virtual_port_service.get_virtual_port(db, virtual_port_id)
    if not virtual_port or virtual_port.project_id != project_id:
        raise HTTPException(status_code=404, detail="Virtual Port không tồn tại")

    await virtual_port_service.delete_virtual_port(db, virtual_port)
