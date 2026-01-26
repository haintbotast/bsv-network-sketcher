"""Project service."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Area, Device, L1Link, Project
from app.schemas.project import ProjectCreate, ProjectStats, ProjectUpdate


async def get_projects(db: AsyncSession, owner_id: str) -> list[Project]:
    """Lấy danh sách projects của user."""
    result = await db.execute(
        select(Project).where(Project.owner_id == owner_id).order_by(Project.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_project_by_id(db: AsyncSession, project_id: str, owner_id: Optional[str] = None) -> Optional[Project]:
    """Lấy project theo ID."""
    query = select(Project).where(Project.id == project_id)
    if owner_id:
        query = query.where(Project.owner_id == owner_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_project_stats(db: AsyncSession, project_id: str) -> ProjectStats:
    """Lấy thống kê project."""
    area_count = await db.scalar(
        select(func.count(Area.id)).where(Area.project_id == project_id)
    )
    device_count = await db.scalar(
        select(func.count(Device.id)).where(Device.project_id == project_id)
    )
    link_count = await db.scalar(
        select(func.count(L1Link.id)).where(L1Link.project_id == project_id)
    )
    return ProjectStats(
        area_count=area_count or 0,
        device_count=device_count or 0,
        link_count=link_count or 0,
    )


async def create_project(db: AsyncSession, owner_id: str, data: ProjectCreate) -> Project:
    """Tạo project mới."""
    project = Project(
        name=data.name,
        description=data.description,
        owner_id=owner_id,
        layout_mode=data.layout_mode,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def update_project(db: AsyncSession, project: Project, data: ProjectUpdate) -> Project:
    """Cập nhật project."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project: Project) -> None:
    """Xóa project."""
    await db.delete(project)
    await db.commit()


async def duplicate_project(db: AsyncSession, project: Project, new_name: str) -> Project:
    """Duplicate project."""
    new_project = Project(
        name=new_name,
        description=project.description,
        owner_id=project.owner_id,
        layout_mode=project.layout_mode,
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    # TODO: Copy areas, devices, links...
    return new_project
