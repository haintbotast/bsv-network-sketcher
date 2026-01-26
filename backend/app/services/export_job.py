"""Service cho export jobs."""

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ExportJob


async def create_job(
    db: AsyncSession,
    project_id: str,
    export_type: str,
    options: dict[str, Any],
) -> ExportJob:
    """Tạo export job mới."""
    job = ExportJob(
        project_id=project_id,
        export_type=export_type,
        status="pending",
        progress=0,
        options_json=json.dumps(options) if options else None,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: str) -> Optional[ExportJob]:
    """Lấy export job theo ID."""
    result = await db.execute(select(ExportJob).where(ExportJob.id == job_id))
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession,
    project_id: str,
    skip: int = 0,
    limit: int = 100,
) -> list[ExportJob]:
    """Lấy danh sách export jobs theo project."""
    result = await db.execute(
        select(ExportJob)
        .where(ExportJob.project_id == project_id)
        .order_by(ExportJob.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


def parse_options(options_json: Optional[str]) -> Optional[dict[str, Any]]:
    """Parse options JSON."""
    if not options_json:
        return None
    try:
        return json.loads(options_json)
    except json.JSONDecodeError:
        return None


async def mark_processing(db: AsyncSession, job: ExportJob) -> ExportJob:
    """Chuyển job sang processing."""
    job.status = "processing"
    job.progress = 0
    job.started_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)
    return job


async def mark_completed(
    db: AsyncSession,
    job: ExportJob,
    *,
    file_path: str,
    file_name: str,
    file_size: int,
    message: Optional[str] = None,
) -> ExportJob:
    """Đánh dấu job hoàn thành."""
    job.status = "completed"
    job.progress = 100
    job.message = message
    job.file_path = file_path
    job.file_name = file_name
    job.file_size = file_size
    job.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)
    return job


async def mark_failed(
    db: AsyncSession,
    job: ExportJob,
    *,
    error_message: str,
) -> ExportJob:
    """Đánh dấu job thất bại."""
    job.status = "failed"
    job.error_message = error_message
    job.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)
    return job


async def get_next_pending_job(db: AsyncSession) -> Optional[ExportJob]:
    """Lấy job pending tiếp theo."""
    result = await db.execute(
        select(ExportJob)
        .where(ExportJob.status == "pending")
        .order_by(ExportJob.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()
