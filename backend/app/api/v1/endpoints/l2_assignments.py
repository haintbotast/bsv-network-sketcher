"""API endpoints cho Interface L2 Assignments."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.schemas.l2_assignment import (
    InterfaceL2AssignmentBulkCreate,
    InterfaceL2AssignmentBulkResponse,
    InterfaceL2AssignmentCreate,
    InterfaceL2AssignmentResponse,
    InterfaceL2AssignmentUpdate,
)
from app.services import l2_assignment as assignment_service
from app.services import l2_segment as segment_service
from app.services import project as project_service

router = APIRouter(prefix="/projects/{project_id}/l2/assignments", tags=["l2-assignments"])


def build_assignment_response(assignment, device_name=None, segment_name=None, vlan_id=None):
    """Build response với thông tin bổ sung."""
    allowed_vlans = assignment_service.parse_allowed_vlans(assignment.allowed_vlans_json)
    return InterfaceL2AssignmentResponse(
        id=assignment.id,
        project_id=assignment.project_id,
        device_id=assignment.device_id,
        device_name=device_name,
        interface_name=assignment.interface_name,
        l2_segment_id=assignment.l2_segment_id,
        l2_segment_name=segment_name,
        vlan_id=vlan_id,
        port_mode=assignment.port_mode,
        native_vlan=assignment.native_vlan,
        allowed_vlans=allowed_vlans,
        created_at=assignment.created_at,
    )


@router.get("", response_model=list[InterfaceL2AssignmentResponse])
async def list_assignments(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
):
    """Lấy danh sách L2 assignments của project."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    assignments = await assignment_service.get_assignments_by_project(db, project_id, skip, limit)

    # Lấy thêm thông tin device và segment
    result = []
    for a in assignments:
        from sqlalchemy import select
        from app.db.models import Device
        device_result = await db.execute(select(Device).where(Device.id == a.device_id))
        device = device_result.scalar_one_or_none()

        segment = await segment_service.get_segment(db, a.l2_segment_id)

        result.append(build_assignment_response(
            a,
            device_name=device.name if device else None,
            segment_name=segment.name if segment else None,
            vlan_id=segment.vlan_id if segment else None,
        ))

    return result


@router.get("/{assignment_id}", response_model=InterfaceL2AssignmentResponse)
async def get_assignment(
    project_id: str,
    assignment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Lấy thông tin L2 assignment."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment or assignment.project_id != project_id:
        raise HTTPException(status_code=404, detail="L2 assignment không tồn tại")

    # Lấy thêm thông tin
    from sqlalchemy import select
    from app.db.models import Device
    device_result = await db.execute(select(Device).where(Device.id == assignment.device_id))
    device = device_result.scalar_one_or_none()
    segment = await segment_service.get_segment(db, assignment.l2_segment_id)

    return build_assignment_response(
        assignment,
        device_name=device.name if device else None,
        segment_name=segment.name if segment else None,
        vlan_id=segment.vlan_id if segment else None,
    )


@router.post("", response_model=InterfaceL2AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    project_id: str,
    data: InterfaceL2AssignmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Tạo L2 assignment mới."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    # Validate device
    device = await assignment_service.get_device_by_name(db, project_id, data.device_name)
    if not device:
        raise HTTPException(
            status_code=400,
            detail=f"Device '{data.device_name}' không tồn tại trong project",
        )

    # Validate segment
    segment = await segment_service.get_segment(db, data.l2_segment_id)
    if not segment or segment.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="L2 segment không tồn tại trong project",
        )

    # Check unique interface
    existing = await assignment_service.get_assignment_by_interface(
        db, project_id, device.id, data.interface_name
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Interface '{data.interface_name}' trên device '{data.device_name}' đã có L2 assignment",
        )

    assignment = await assignment_service.create_assignment(db, project_id, device.id, data)
    return build_assignment_response(
        assignment,
        device_name=device.name,
        segment_name=segment.name,
        vlan_id=segment.vlan_id,
    )


@router.post("/bulk", response_model=InterfaceL2AssignmentBulkResponse)
async def bulk_create_assignments(
    project_id: str,
    data: InterfaceL2AssignmentBulkCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Tạo nhiều L2 assignments cùng lúc."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    created = []
    errors = []

    for idx, assign_data in enumerate(data.assignments):
        try:
            device = await assignment_service.get_device_by_name(
                db, project_id, assign_data.device_name
            )
            if not device:
                errors.append({
                    "index": idx,
                    "data": assign_data.model_dump(),
                    "error": f"Device '{assign_data.device_name}' không tồn tại",
                })
                continue

            segment = await segment_service.get_segment(db, assign_data.l2_segment_id)
            if not segment or segment.project_id != project_id:
                errors.append({
                    "index": idx,
                    "data": assign_data.model_dump(),
                    "error": "L2 segment không tồn tại",
                })
                continue

            existing = await assignment_service.get_assignment_by_interface(
                db, project_id, device.id, assign_data.interface_name
            )
            if existing:
                errors.append({
                    "index": idx,
                    "data": assign_data.model_dump(),
                    "error": f"Interface đã có L2 assignment",
                })
                continue

            assignment = await assignment_service.create_assignment(
                db, project_id, device.id, assign_data
            )
            created.append({
                "id": assignment.id,
                "device_name": device.name,
                "interface_name": assignment.interface_name,
                "vlan_id": segment.vlan_id,
            })
        except Exception as e:
            errors.append({
                "index": idx,
                "data": assign_data.model_dump(),
                "error": str(e),
            })

    return InterfaceL2AssignmentBulkResponse(
        success_count=len(created),
        error_count=len(errors),
        created=created,
        errors=errors,
    )


@router.put("/{assignment_id}", response_model=InterfaceL2AssignmentResponse)
async def update_assignment(
    project_id: str,
    assignment_id: str,
    data: InterfaceL2AssignmentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Cập nhật L2 assignment."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment or assignment.project_id != project_id:
        raise HTTPException(status_code=404, detail="L2 assignment không tồn tại")

    device_id = None
    device_name = None

    # Validate device nếu thay đổi
    if data.device_name:
        device = await assignment_service.get_device_by_name(db, project_id, data.device_name)
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
        device_result = await db.execute(select(Device).where(Device.id == assignment.device_id))
        device = device_result.scalar_one_or_none()
        device_name = device.name if device else None

    # Validate segment nếu thay đổi
    segment_id = data.l2_segment_id or assignment.l2_segment_id
    segment = await segment_service.get_segment(db, segment_id)
    if not segment or segment.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="L2 segment không tồn tại trong project",
        )

    assignment = await assignment_service.update_assignment(db, assignment, data, device_id)
    return build_assignment_response(
        assignment,
        device_name=device_name,
        segment_name=segment.name,
        vlan_id=segment.vlan_id,
    )


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    project_id: str,
    assignment_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Xóa L2 assignment."""
    project = await project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập project")

    assignment = await assignment_service.get_assignment(db, assignment_id)
    if not assignment or assignment.project_id != project_id:
        raise HTTPException(status_code=404, detail="L2 assignment không tồn tại")

    await assignment_service.delete_assignment(db, assignment)
