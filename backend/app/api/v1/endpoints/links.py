"""L1 Link endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.link import L1LinkBulkCreate, L1LinkBulkResponse, L1LinkCreate, L1LinkResponse, L1LinkUpdate
from app.services.device import get_device_by_name
from app.services.link import (
    check_link_exists,
    check_port_in_use,
    create_link,
    delete_link,
    get_link_by_id,
    get_links,
    update_link,
)
from app.services.project import get_project_by_id

router = APIRouter(tags=["links"])


# Mapping purpose -> color RGB
PURPOSE_COLORS = {
    "WAN": [255, 0, 0],       # Red
    "INTERNET": [255, 128, 0],  # Orange
    "DMZ": [255, 255, 0],     # Yellow
    "LAN": [112, 173, 71],    # Green
    "MGMT": [0, 112, 192],    # Blue
    "HA": [112, 48, 160],     # Purple
    "STORAGE": [165, 42, 42], # Brown
    "BACKUP": [128, 128, 128],  # Gray
    "VPN": [0, 176, 240],     # Cyan
    "DEFAULT": [0, 0, 0],     # Black
}


async def _verify_project_access(db: DBSession, project_id: str, user_id: str):
    """Verify user có quyền truy cập project."""
    project = await get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project không tồn tại",
        )
    return project


def _link_to_response(link) -> L1LinkResponse:
    """Convert link model to response."""
    response = L1LinkResponse.model_validate(link)
    if link.from_device:
        response.from_device_name = link.from_device.name
    if link.to_device:
        response.to_device_name = link.to_device.name
    response.color_rgb = PURPOSE_COLORS.get(link.purpose, PURPOSE_COLORS["DEFAULT"])
    return response


@router.get("/projects/{project_id}/links", response_model=list[L1LinkResponse])
async def list_links(
    project_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> list[L1LinkResponse]:
    """Lấy danh sách links của project."""
    await _verify_project_access(db, project_id, current_user.id)
    links = await get_links(db, project_id)
    return [_link_to_response(link) for link in links]


@router.post("/projects/{project_id}/links", response_model=L1LinkResponse, status_code=status.HTTP_201_CREATED)
async def create_new_link(
    project_id: str,
    data: L1LinkCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> L1LinkResponse:
    """Tạo link mới."""
    await _verify_project_access(db, project_id, current_user.id)

    # Check from_device
    from_device = await get_device_by_name(db, project_id, data.from_device)
    if not from_device:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Device '{data.from_device}' không tồn tại",
        )

    # Check to_device
    to_device = await get_device_by_name(db, project_id, data.to_device)
    if not to_device:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Device '{data.to_device}' không tồn tại",
        )

    # Check duplicate link
    if await check_link_exists(db, project_id, from_device.id, data.from_port, to_device.id, data.to_port):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link đã tồn tại",
        )

    # Check port already in use
    if await check_port_in_use(db, project_id, from_device.id, data.from_port):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Port '{data.from_port}' trên device '{data.from_device}' đã được sử dụng",
        )

    if await check_port_in_use(db, project_id, to_device.id, data.to_port):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Port '{data.to_port}' trên device '{data.to_device}' đã được sử dụng",
        )

    link = await create_link(db, project_id, from_device, to_device, data)
    link = await get_link_by_id(db, link.id)
    return _link_to_response(link)


@router.get("/projects/{project_id}/links/{link_id}", response_model=L1LinkResponse)
async def get_link(
    project_id: str,
    link_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> L1LinkResponse:
    """Lấy thông tin link."""
    await _verify_project_access(db, project_id, current_user.id)

    link = await get_link_by_id(db, link_id)
    if not link or link.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link không tồn tại",
        )
    return _link_to_response(link)


@router.put("/projects/{project_id}/links/{link_id}", response_model=L1LinkResponse)
async def update_existing_link(
    project_id: str,
    link_id: str,
    data: L1LinkUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> L1LinkResponse:
    """Cập nhật link."""
    await _verify_project_access(db, project_id, current_user.id)

    link = await get_link_by_id(db, link_id)
    if not link or link.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link không tồn tại",
        )

    from_device = None
    to_device = None

    if data.from_device:
        from_device = await get_device_by_name(db, project_id, data.from_device)
        if not from_device:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Device '{data.from_device}' không tồn tại",
            )

    if data.to_device:
        to_device = await get_device_by_name(db, project_id, data.to_device)
        if not to_device:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Device '{data.to_device}' không tồn tại",
            )

    link = await update_link(db, link, data, from_device, to_device)
    link = await get_link_by_id(db, link.id)
    return _link_to_response(link)


@router.delete("/projects/{project_id}/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_link(
    project_id: str,
    link_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Xóa link."""
    await _verify_project_access(db, project_id, current_user.id)

    link = await get_link_by_id(db, link_id)
    if not link or link.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link không tồn tại",
        )
    await delete_link(db, link)


@router.post("/projects/{project_id}/links/bulk", response_model=L1LinkBulkResponse)
async def bulk_create_links(
    project_id: str,
    data: L1LinkBulkCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> L1LinkBulkResponse:
    """Bulk create links."""
    await _verify_project_access(db, project_id, current_user.id)

    created = []
    errors = []

    for row, link_data in enumerate(data.links):
        try:
            # Check from_device
            from_device = await get_device_by_name(db, project_id, link_data.from_device)
            if not from_device:
                errors.append({
                    "entity": "link",
                    "row": row,
                    "field": "from_device",
                    "code": "DEVICE_NOT_FOUND",
                    "message": f"Device '{link_data.from_device}' không tồn tại",
                })
                continue

            # Check to_device
            to_device = await get_device_by_name(db, project_id, link_data.to_device)
            if not to_device:
                errors.append({
                    "entity": "link",
                    "row": row,
                    "field": "to_device",
                    "code": "DEVICE_NOT_FOUND",
                    "message": f"Device '{link_data.to_device}' không tồn tại",
                })
                continue

            # Check duplicate
            if await check_link_exists(db, project_id, from_device.id, link_data.from_port, to_device.id, link_data.to_port):
                errors.append({
                    "entity": "link",
                    "row": row,
                    "code": "L1_LINK_DUP",
                    "message": "Link đã tồn tại",
                })
                continue

            link = await create_link(db, project_id, from_device, to_device, link_data)
            created.append({
                "id": link.id,
                "name": f"{link_data.from_device}:{link_data.from_port} -> {link_data.to_device}:{link_data.to_port}",
                "row": row,
            })
        except Exception as e:
            errors.append({
                "entity": "link",
                "row": row,
                "code": "LINK_CREATE_FAILED",
                "message": str(e),
            })

    return L1LinkBulkResponse(
        success_count=len(created),
        error_count=len(errors),
        created=created,
        errors=errors,
    )
