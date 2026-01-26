"""API endpoint cho import dữ liệu tổng hợp."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.schemas.import_data import ImportRequest, ImportResult
from app.services import import_service
from app.services import project as project_service

router = APIRouter(prefix="/projects/{project_id}", tags=["import"])


@router.post("/import", response_model=ImportResult)
async def import_project_data(
    project_id: str,
    data: ImportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Import dữ liệu tổng hợp vào project."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    if data.mode in {"excel", "csv"}:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Chưa hỗ trợ import excel/csv",
        )

    result = await import_service.import_project_data(
        db=db,
        project=project,
        payload=data.payload,
        options=data.options,
        mode=data.mode,
    )
    return result
