"""Device port endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.device_port import DevicePortCreate, DevicePortResponse, DevicePortUpdate
from app.services.device import get_device_by_id
from app.services.device_port import (
    create_port,
    delete_port,
    get_port_by_id,
    get_port_by_name,
    get_ports_by_device,
    get_ports_by_project,
    update_port,
)
from app.services.link import check_port_in_use
from app.services.project import get_project_by_id

router = APIRouter(tags=["device-ports"])


async def _verify_project_access(db: DBSession, project_id: str, user_id: str):
    project = await get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project không tồn tại")
    return project


def _port_to_response(port) -> DevicePortResponse:
    response = DevicePortResponse.model_validate(port)
    if port.device:
        response.device_name = port.device.name
    return response


@router.get("/projects/{project_id}/ports", response_model=list[DevicePortResponse])
async def list_project_ports(
    project_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> list[DevicePortResponse]:
    """Lấy toàn bộ port trong project."""
    await _verify_project_access(db, project_id, current_user.id)
    ports = await get_ports_by_project(db, project_id)
    return [_port_to_response(port) for port in ports]


@router.get("/projects/{project_id}/devices/{device_id}/ports", response_model=list[DevicePortResponse])
async def list_device_ports(
    project_id: str,
    device_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> list[DevicePortResponse]:
    """Lấy port theo device."""
    await _verify_project_access(db, project_id, current_user.id)

    device = await get_device_by_id(db, device_id)
    if not device or device.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device không tồn tại")

    ports = await get_ports_by_device(db, project_id, device_id)
    return [_port_to_response(port) for port in ports]


@router.post(
    "/projects/{project_id}/devices/{device_id}/ports",
    response_model=DevicePortResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_device_port(
    project_id: str,
    device_id: str,
    data: DevicePortCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> DevicePortResponse:
    """Tạo port mới cho device."""
    await _verify_project_access(db, project_id, current_user.id)

    device = await get_device_by_id(db, device_id)
    if not device or device.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device không tồn tại")

    existing = await get_port_by_name(db, project_id, device_id, data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Port '{data.name}' đã tồn tại trên device '{device.name}'",
        )

    port = await create_port(db, project_id, device, data)
    port = await get_port_by_id(db, project_id, port.id)
    return _port_to_response(port)


@router.put(
    "/projects/{project_id}/devices/{device_id}/ports/{port_id}",
    response_model=DevicePortResponse,
)
async def update_device_port(
    project_id: str,
    device_id: str,
    port_id: str,
    data: DevicePortUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> DevicePortResponse:
    """Cập nhật port của device."""
    await _verify_project_access(db, project_id, current_user.id)

    device = await get_device_by_id(db, device_id)
    if not device or device.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device không tồn tại")

    port = await get_port_by_id(db, project_id, port_id)
    if not port or port.device_id != device_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Port không tồn tại")

    if data.name and data.name != port.name:
        existing = await get_port_by_name(db, project_id, device_id, data.name)
        if existing and existing.id != port.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Port '{data.name}' đã tồn tại trên device '{device.name}'",
            )

    if data.name and data.name != port.name:
        in_use = await check_port_in_use(db, project_id, device_id, port.name, exclude_link_id=None)
        if in_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Port '{port.name}' đang được sử dụng trong link, không thể đổi tên.",
            )

    updated = await update_port(db, port, data)
    updated = await get_port_by_id(db, project_id, updated.id)
    return _port_to_response(updated)


@router.delete(
    "/projects/{project_id}/devices/{device_id}/ports/{port_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_device_port(
    project_id: str,
    device_id: str,
    port_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Xóa port của device."""
    await _verify_project_access(db, project_id, current_user.id)

    port = await get_port_by_id(db, project_id, port_id)
    if not port or port.device_id != device_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Port không tồn tại")

    if await check_port_in_use(db, project_id, device_id, port.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Port '{port.name}' đang được sử dụng trong link, không thể xóa.",
        )

    await delete_port(db, port)
