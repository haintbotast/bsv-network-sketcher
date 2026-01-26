"""Project endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project import (
    create_project,
    delete_project,
    duplicate_project,
    get_project_by_id,
    get_project_stats,
    get_projects,
    update_project,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(current_user: CurrentUser, db: DBSession) -> list[ProjectResponse]:
    """Lấy danh sách projects của user."""
    projects = await get_projects(db, current_user.id)
    result = []
    for project in projects:
        stats = await get_project_stats(db, project.id)
        response = ProjectResponse.model_validate(project)
        response.stats = stats
        result.append(response)
    return result


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_new_project(
    data: ProjectCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> ProjectResponse:
    """Tạo project mới."""
    project = await create_project(db, current_user.id, data)
    stats = await get_project_stats(db, project.id)
    response = ProjectResponse.model_validate(project)
    response.stats = stats
    return response


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> ProjectResponse:
    """Lấy thông tin project."""
    project = await get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project không tồn tại",
        )
    stats = await get_project_stats(db, project.id)
    response = ProjectResponse.model_validate(project)
    response.stats = stats
    return response


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_existing_project(
    project_id: str,
    data: ProjectUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> ProjectResponse:
    """Cập nhật project."""
    project = await get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project không tồn tại",
        )
    project = await update_project(db, project, data)
    stats = await get_project_stats(db, project.id)
    response = ProjectResponse.model_validate(project)
    response.stats = stats
    return response


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_project(
    project_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Xóa project."""
    project = await get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project không tồn tại",
        )
    await delete_project(db, project)


@router.post("/{project_id}/duplicate", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_existing_project(
    project_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> ProjectResponse:
    """Duplicate project."""
    project = await get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project không tồn tại",
        )
    new_project = await duplicate_project(db, project, f"{project.name} (Copy)")
    stats = await get_project_stats(db, new_project.id)
    response = ProjectResponse.model_validate(new_project)
    response.stats = stats
    return response
