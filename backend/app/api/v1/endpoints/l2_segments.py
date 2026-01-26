"""API endpoints cho L2 Segments."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.schemas.l2_segment import (
    L2SegmentBulkCreate,
    L2SegmentBulkResponse,
    L2SegmentCreate,
    L2SegmentResponse,
    L2SegmentUpdate,
)
from app.services import l2_segment as segment_service
from app.services import project as project_service

router = APIRouter(prefix="/projects/{project_id}/l2/segments", tags=["l2-segments"])


@router.get("", response_model=list[L2SegmentResponse])
async def list_segments(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
):
    """Lấy danh sách L2 segments của project."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    segments = await segment_service.get_segments_by_project(db, project_id, skip, limit)
    return [L2SegmentResponse.model_validate(s) for s in segments]


@router.get("/{segment_id}", response_model=L2SegmentResponse)
async def get_segment(
    project_id: str,
    segment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Lấy thông tin L2 segment."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    segment = await segment_service.get_segment(db, segment_id)
    if not segment or segment.project_id != project_id:
        raise HTTPException(status_code=404, detail="L2 segment không tồn tại")

    return L2SegmentResponse.model_validate(segment)


@router.post("", response_model=L2SegmentResponse, status_code=status.HTTP_201_CREATED)
async def create_segment(
    project_id: str,
    data: L2SegmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Tạo L2 segment mới."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    # Check VLAN ID unique trong project
    existing = await segment_service.get_segment_by_vlan(db, project_id, data.vlan_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"VLAN ID {data.vlan_id} đã tồn tại trong project",
        )

    segment = await segment_service.create_segment(db, project_id, data)
    return L2SegmentResponse.model_validate(segment)


@router.post("/bulk", response_model=L2SegmentBulkResponse)
async def bulk_create_segments(
    project_id: str,
    data: L2SegmentBulkCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Tạo nhiều L2 segments cùng lúc."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    created = []
    errors = []

    for idx, segment_data in enumerate(data.segments):
        try:
            existing = await segment_service.get_segment_by_vlan(
                db, project_id, segment_data.vlan_id
            )
            if existing:
                errors.append({
                    "index": idx,
                    "data": segment_data.model_dump(),
                    "error": f"VLAN ID {segment_data.vlan_id} đã tồn tại",
                })
                continue

            segment = await segment_service.create_segment(db, project_id, segment_data)
            created.append({
                "id": segment.id,
                "name": segment.name,
                "vlan_id": segment.vlan_id,
            })
        except Exception as e:
            errors.append({
                "index": idx,
                "data": segment_data.model_dump(),
                "error": str(e),
            })

    return L2SegmentBulkResponse(
        success_count=len(created),
        error_count=len(errors),
        created=created,
        errors=errors,
    )


@router.put("/{segment_id}", response_model=L2SegmentResponse)
async def update_segment(
    project_id: str,
    segment_id: str,
    data: L2SegmentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Cập nhật L2 segment."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    segment = await segment_service.get_segment(db, segment_id)
    if not segment or segment.project_id != project_id:
        raise HTTPException(status_code=404, detail="L2 segment không tồn tại")

    # Check VLAN ID unique nếu thay đổi
    if data.vlan_id is not None and data.vlan_id != segment.vlan_id:
        existing = await segment_service.get_segment_by_vlan(db, project_id, data.vlan_id)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"VLAN ID {data.vlan_id} đã tồn tại trong project",
            )

    segment = await segment_service.update_segment(db, segment, data)
    return L2SegmentResponse.model_validate(segment)


@router.delete("/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_segment(
    project_id: str,
    segment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Xóa L2 segment."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    segment = await segment_service.get_segment(db, segment_id)
    if not segment or segment.project_id != project_id:
        raise HTTPException(status_code=404, detail="L2 segment không tồn tại")

    await segment_service.delete_segment(db, segment)
