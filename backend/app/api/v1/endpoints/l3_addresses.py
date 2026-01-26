"""API endpoints cho L3 Addresses."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.schemas.l3_address import (
    L3AddressBulkCreate,
    L3AddressBulkResponse,
    L3AddressCreate,
    L3AddressResponse,
    L3AddressUpdate,
)
from app.services import l3_address as address_service
from app.services import project as project_service

router = APIRouter(prefix="/projects/{project_id}/l3/addresses", tags=["l3-addresses"])


def build_address_response(address, device_name=None):
    """Build response với thông tin bổ sung."""
    return L3AddressResponse(
        id=address.id,
        project_id=address.project_id,
        device_id=address.device_id,
        device_name=device_name,
        interface_name=address.interface_name,
        ip_address=address.ip_address,
        prefix_length=address.prefix_length,
        is_secondary=address.is_secondary,
        description=address.description,
        created_at=address.created_at,
    )


@router.get("", response_model=list[L3AddressResponse])
async def list_addresses(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
):
    """Lấy danh sách L3 addresses của project."""
    project = await project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    addresses = await address_service.get_addresses_by_project(db, project_id, skip, limit)

    # Lấy thêm thông tin device
    result = []
    for a in addresses:
        from sqlalchemy import select
        from app.db.models import Device
        device_result = await db.execute(select(Device).where(Device.id == a.device_id))
        device = device_result.scalar_one_or_none()
        result.append(build_address_response(a, device_name=device.name if device else None))

    return result


@router.get("/{address_id}", response_model=L3AddressResponse)
async def get_address(
    project_id: str,
    address_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Lấy thông tin L3 address."""
    project = await project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    address = await address_service.get_address(db, address_id)
    if not address or address.project_id != project_id:
        raise HTTPException(status_code=404, detail="L3 address không tồn tại")

    from sqlalchemy import select
    from app.db.models import Device
    device_result = await db.execute(select(Device).where(Device.id == address.device_id))
    device = device_result.scalar_one_or_none()

    return build_address_response(address, device_name=device.name if device else None)


@router.post("", response_model=L3AddressResponse, status_code=status.HTTP_201_CREATED)
async def create_address(
    project_id: str,
    data: L3AddressCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Tạo L3 address mới."""
    project = await project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    # Validate device
    device = await address_service.get_device_by_name(db, project_id, data.device_name)
    if not device:
        raise HTTPException(
            status_code=400,
            detail=f"Device '{data.device_name}' không tồn tại trong project",
        )

    address = await address_service.create_address(db, project_id, device.id, data)
    return build_address_response(address, device_name=device.name)


@router.post("/bulk", response_model=L3AddressBulkResponse)
async def bulk_create_addresses(
    project_id: str,
    data: L3AddressBulkCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Tạo nhiều L3 addresses cùng lúc."""
    project = await project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    created = []
    errors = []

    for idx, addr_data in enumerate(data.addresses):
        try:
            device = await address_service.get_device_by_name(
                db, project_id, addr_data.device_name
            )
            if not device:
                errors.append({
                    "index": idx,
                    "data": addr_data.model_dump(),
                    "error": f"Device '{addr_data.device_name}' không tồn tại",
                })
                continue

            address = await address_service.create_address(
                db, project_id, device.id, addr_data
            )
            created.append({
                "id": address.id,
                "device_name": device.name,
                "interface_name": address.interface_name,
                "ip_address": address.ip_address,
                "prefix_length": address.prefix_length,
            })
        except Exception as e:
            errors.append({
                "index": idx,
                "data": addr_data.model_dump(),
                "error": str(e),
            })

    return L3AddressBulkResponse(
        success_count=len(created),
        error_count=len(errors),
        created=created,
        errors=errors,
    )


@router.put("/{address_id}", response_model=L3AddressResponse)
async def update_address(
    project_id: str,
    address_id: str,
    data: L3AddressUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Cập nhật L3 address."""
    project = await project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    address = await address_service.get_address(db, address_id)
    if not address or address.project_id != project_id:
        raise HTTPException(status_code=404, detail="L3 address không tồn tại")

    device_id = None
    device_name = None

    # Validate device nếu thay đổi
    if data.device_name:
        device = await address_service.get_device_by_name(db, project_id, data.device_name)
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
        device_result = await db.execute(select(Device).where(Device.id == address.device_id))
        device = device_result.scalar_one_or_none()
        device_name = device.name if device else None

    address = await address_service.update_address(db, address, data, device_id)
    return build_address_response(address, device_name=device_name)


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    project_id: str,
    address_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Xóa L3 address."""
    project = await project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    address = await address_service.get_address(db, address_id)
    if not address or address.project_id != project_id:
        raise HTTPException(status_code=404, detail="L3 address không tồn tại")

    await address_service.delete_address(db, address)
