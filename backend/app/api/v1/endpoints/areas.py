"""Area endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.area import AreaBulkCreate, AreaBulkResponse, AreaCreate, AreaResponse, AreaUpdate
from app.services.area import (
    create_area,
    delete_area,
    get_area_by_id,
    get_area_by_name,
    get_areas,
    parse_area_style,
    update_area,
)
from app.services.project import get_project_by_id

router = APIRouter(tags=["areas"])


async def _verify_project_access(db: DBSession, project_id: str, user_id: str):
    """Verify user có quyền truy cập project."""
    project = await get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project không tồn tại",
        )
    return project


def _area_to_response(area) -> AreaResponse:
    """Convert area model to response."""
    response = AreaResponse.model_validate(area)
    response.style = parse_area_style(area)
    return response


@router.get("/projects/{project_id}/areas", response_model=list[AreaResponse])
async def list_areas(
    project_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> list[AreaResponse]:
    """Lấy danh sách areas của project."""
    await _verify_project_access(db, project_id, current_user.id)
    areas = await get_areas(db, project_id)
    return [_area_to_response(area) for area in areas]


@router.post("/projects/{project_id}/areas", response_model=AreaResponse, status_code=status.HTTP_201_CREATED)
async def create_new_area(
    project_id: str,
    data: AreaCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> AreaResponse:
    """Tạo area mới."""
    await _verify_project_access(db, project_id, current_user.id)

    # Check duplicate name
    existing = await get_area_by_name(db, project_id, data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tên area '{data.name}' đã tồn tại trong project",
        )

    area = await create_area(db, project_id, data)
    return _area_to_response(area)


@router.get("/projects/{project_id}/areas/{area_id}", response_model=AreaResponse)
async def get_area(
    project_id: str,
    area_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> AreaResponse:
    """Lấy thông tin area."""
    await _verify_project_access(db, project_id, current_user.id)

    area = await get_area_by_id(db, area_id)
    if not area or area.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area không tồn tại",
        )
    return _area_to_response(area)


@router.put("/projects/{project_id}/areas/{area_id}", response_model=AreaResponse)
async def update_existing_area(
    project_id: str,
    area_id: str,
    data: AreaUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> AreaResponse:
    """Cập nhật area."""
    await _verify_project_access(db, project_id, current_user.id)

    area = await get_area_by_id(db, area_id)
    if not area or area.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area không tồn tại",
        )

    # Check duplicate name if updating name
    if data.name and data.name != area.name:
        existing = await get_area_by_name(db, project_id, data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tên area '{data.name}' đã tồn tại trong project",
            )

    area = await update_area(db, area, data)
    return _area_to_response(area)


@router.delete("/projects/{project_id}/areas/{area_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_area(
    project_id: str,
    area_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Xóa area."""
    await _verify_project_access(db, project_id, current_user.id)

    area = await get_area_by_id(db, area_id)
    if not area or area.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area không tồn tại",
        )
    await delete_area(db, area)


@router.post("/projects/{project_id}/areas/bulk", response_model=AreaBulkResponse)
async def bulk_create_areas(
    project_id: str,
    data: AreaBulkCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> AreaBulkResponse:
    """Bulk create areas."""
    await _verify_project_access(db, project_id, current_user.id)

    created = []
    errors = []

    for row, area_data in enumerate(data.areas):
        try:
            # Check duplicate
            existing = await get_area_by_name(db, project_id, area_data.name)
            if existing:
                errors.append({
                    "entity": "area",
                    "row": row,
                    "field": "name",
                    "code": "AREA_NAME_DUP",
                    "message": f"Tên area '{area_data.name}' đã tồn tại",
                })
                continue

            area = await create_area(db, project_id, area_data)
            created.append({"id": area.id, "name": area.name, "row": row})
        except Exception as e:
            errors.append({
                "entity": "area",
                "row": row,
                "code": "AREA_CREATE_FAILED",
                "message": str(e),
            })

    return AreaBulkResponse(
        success_count=len(created),
        error_count=len(errors),
        created=created,
        errors=errors,
    )
