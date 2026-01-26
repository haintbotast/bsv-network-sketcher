"""API endpoints cho export jobs."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.schemas.export_job import ExportJobResponse, ExportRequest
from app.services import export_job as export_job_service
from app.services import project as project_service

router = APIRouter(prefix="/projects/{project_id}/export", tags=["export"])


def _build_options(export_type: str, data: ExportRequest | None) -> dict:
    options = data.model_dump(exclude_none=True) if data else {}
    if "format" not in options:
        if export_type in {"device_file", "master_file"}:
            options["format"] = "xlsx"
        else:
            options["format"] = "pptx"
    return options


def _build_response(job) -> ExportJobResponse:
    response = ExportJobResponse.model_validate(job)
    response.options = export_job_service.parse_options(job.options_json)
    return response


async def _ensure_project_access(
    db: AsyncSession,
    project_id: str,
    current_user: User,
) -> None:
    project = await project_service.get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project không tồn tại")


async def _ensure_export_data(db: AsyncSession, project_id: str) -> None:
    stats = await project_service.get_project_stats(db, project_id)
    if stats.device_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Project không có dữ liệu để xuất",
        )


@router.post("/l1-diagram", response_model=ExportJobResponse, status_code=status.HTTP_201_CREATED)
async def export_l1_diagram(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    data: ExportRequest | None = None,
):
    """Tạo export job L1 diagram."""
    await _ensure_project_access(db, project_id, current_user)
    await _ensure_export_data(db, project_id)
    options = _build_options("l1_diagram", data)
    job = await export_job_service.create_job(db, project_id, "l1_diagram", options)
    return _build_response(job)


@router.post("/l2-diagram", response_model=ExportJobResponse, status_code=status.HTTP_201_CREATED)
async def export_l2_diagram(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    data: ExportRequest | None = None,
):
    """Tạo export job L2 diagram."""
    await _ensure_project_access(db, project_id, current_user)
    await _ensure_export_data(db, project_id)
    options = _build_options("l2_diagram", data)
    job = await export_job_service.create_job(db, project_id, "l2_diagram", options)
    return _build_response(job)


@router.post("/l3-diagram", response_model=ExportJobResponse, status_code=status.HTTP_201_CREATED)
async def export_l3_diagram(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    data: ExportRequest | None = None,
):
    """Tạo export job L3 diagram."""
    await _ensure_project_access(db, project_id, current_user)
    await _ensure_export_data(db, project_id)
    options = _build_options("l3_diagram", data)
    job = await export_job_service.create_job(db, project_id, "l3_diagram", options)
    return _build_response(job)


@router.post("/device-file", response_model=ExportJobResponse, status_code=status.HTTP_201_CREATED)
async def export_device_file(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    data: ExportRequest | None = None,
):
    """Tạo export job device file."""
    await _ensure_project_access(db, project_id, current_user)
    await _ensure_export_data(db, project_id)
    options = _build_options("device_file", data)
    job = await export_job_service.create_job(db, project_id, "device_file", options)
    return _build_response(job)


@router.post("/master-file", response_model=ExportJobResponse, status_code=status.HTTP_201_CREATED)
async def export_master_file(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    data: ExportRequest | None = None,
):
    """Tạo export job master file."""
    await _ensure_project_access(db, project_id, current_user)
    await _ensure_export_data(db, project_id)
    options = _build_options("master_file", data)
    job = await export_job_service.create_job(db, project_id, "master_file", options)
    return _build_response(job)


@router.get("/jobs", response_model=list[ExportJobResponse])
async def list_export_jobs(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
):
    """Lấy danh sách export jobs của project."""
    await _ensure_project_access(db, project_id, current_user)
    jobs = await export_job_service.list_jobs(db, project_id, skip, limit)
    return [_build_response(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=ExportJobResponse)
async def get_export_job(
    project_id: str,
    job_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Lấy chi tiết export job."""
    await _ensure_project_access(db, project_id, current_user)
    job = await export_job_service.get_job(db, job_id)
    if not job or job.project_id != project_id:
        raise HTTPException(status_code=404, detail="Export job không tồn tại")
    return _build_response(job)
