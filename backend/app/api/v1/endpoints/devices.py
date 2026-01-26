"""Device endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.device import DeviceBulkCreate, DeviceBulkResponse, DeviceCreate, DeviceResponse, DeviceUpdate
from app.services.area import get_area_by_name
from app.services.device import (
    create_device,
    delete_device,
    get_device_by_id,
    get_device_by_name,
    get_devices,
    parse_device_color,
    update_device,
)
from app.services.project import get_project_by_id

router = APIRouter(tags=["devices"])


async def _verify_project_access(db: DBSession, project_id: str, user_id: str):
    """Verify user có quyền truy cập project."""
    project = await get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project không tồn tại",
        )
    return project


def _device_to_response(device) -> DeviceResponse:
    """Convert device model to response."""
    response = DeviceResponse.model_validate(device)
    response.color_rgb = parse_device_color(device)
    if device.area:
        response.area_name = device.area.name
    return response


@router.get("/projects/{project_id}/devices", response_model=list[DeviceResponse])
async def list_devices(
    project_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> list[DeviceResponse]:
    """Lấy danh sách devices của project."""
    await _verify_project_access(db, project_id, current_user.id)
    devices = await get_devices(db, project_id)
    return [_device_to_response(device) for device in devices]


@router.post("/projects/{project_id}/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_new_device(
    project_id: str,
    data: DeviceCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> DeviceResponse:
    """Tạo device mới."""
    await _verify_project_access(db, project_id, current_user.id)

    # Check area exists
    area = await get_area_by_name(db, project_id, data.area_name)
    if not area:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Area '{data.area_name}' không tồn tại",
        )

    # Check duplicate name
    existing = await get_device_by_name(db, project_id, data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tên device '{data.name}' đã tồn tại trong project",
        )

    device = await create_device(db, project_id, area, data)
    # Reload to get area relationship
    device = await get_device_by_id(db, device.id)
    return _device_to_response(device)


@router.get("/projects/{project_id}/devices/{device_id}", response_model=DeviceResponse)
async def get_device(
    project_id: str,
    device_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> DeviceResponse:
    """Lấy thông tin device."""
    await _verify_project_access(db, project_id, current_user.id)

    device = await get_device_by_id(db, device_id)
    if not device or device.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device không tồn tại",
        )
    return _device_to_response(device)


@router.put("/projects/{project_id}/devices/{device_id}", response_model=DeviceResponse)
async def update_existing_device(
    project_id: str,
    device_id: str,
    data: DeviceUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> DeviceResponse:
    """Cập nhật device."""
    await _verify_project_access(db, project_id, current_user.id)

    device = await get_device_by_id(db, device_id)
    if not device or device.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device không tồn tại",
        )

    # Check area if updating
    area = None
    if data.area_name:
        area = await get_area_by_name(db, project_id, data.area_name)
        if not area:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Area '{data.area_name}' không tồn tại",
            )

    # Check duplicate name if updating
    if data.name and data.name != device.name:
        existing = await get_device_by_name(db, project_id, data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tên device '{data.name}' đã tồn tại trong project",
            )

    device = await update_device(db, device, data, area)
    device = await get_device_by_id(db, device.id)
    return _device_to_response(device)


@router.delete("/projects/{project_id}/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_device(
    project_id: str,
    device_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Xóa device."""
    await _verify_project_access(db, project_id, current_user.id)

    device = await get_device_by_id(db, device_id)
    if not device or device.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device không tồn tại",
        )
    await delete_device(db, device)


@router.post("/projects/{project_id}/devices/bulk", response_model=DeviceBulkResponse)
async def bulk_create_devices(
    project_id: str,
    data: DeviceBulkCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> DeviceBulkResponse:
    """Bulk create devices."""
    await _verify_project_access(db, project_id, current_user.id)

    created = []
    errors = []

    for row, device_data in enumerate(data.devices):
        try:
            # Check area
            area = await get_area_by_name(db, project_id, device_data.area_name)
            if not area:
                errors.append({
                    "entity": "device",
                    "row": row,
                    "field": "area_name",
                    "code": "AREA_NOT_FOUND",
                    "message": f"Area '{device_data.area_name}' không tồn tại",
                })
                continue

            # Check duplicate
            existing = await get_device_by_name(db, project_id, device_data.name)
            if existing:
                errors.append({
                    "entity": "device",
                    "row": row,
                    "field": "name",
                    "code": "DEVICE_NAME_DUP",
                    "message": f"Tên device '{device_data.name}' đã tồn tại",
                })
                continue

            device = await create_device(db, project_id, area, device_data)
            created.append({"id": device.id, "name": device.name, "row": row})
        except Exception as e:
            errors.append({
                "entity": "device",
                "row": row,
                "code": "DEVICE_CREATE_FAILED",
                "message": str(e),
            })

    return DeviceBulkResponse(
        success_count=len(created),
        error_count=len(errors),
        created=created,
        errors=errors,
    )
