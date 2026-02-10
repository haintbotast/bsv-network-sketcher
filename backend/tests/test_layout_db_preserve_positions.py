import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.endpoints.layout_db import apply_grouped_layout_to_db
from app.db.base import Base
from app.db.models import Area, Device, Project, User
from app.schemas.layout import AreaLayout, DeviceLayout


async def _seed_base(session):
    user = User(
        email="layout-preserve@example.com",
        hashed_password="hash",
        display_name="Layout Preserve",
        is_active=True,
        is_admin=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    project = Project(name="Layout Preserve Project", owner_id=user.id)
    session.add(project)
    await session.commit()
    await session.refresh(project)

    area = Area(
        project_id=project.id,
        name="Area-1",
        grid_row=1,
        grid_col=1,
        position_x=1.0,
        position_y=1.0,
        width=3.0,
        height=1.5,
    )
    session.add(area)
    await session.commit()
    await session.refresh(area)

    device_existing = Device(
        project_id=project.id,
        area_id=area.id,
        name="SW-EXISTING",
        device_type="Switch",
        position_x=2.0,
        position_y=2.0,
        width=1.2,
        height=0.8,
    )
    device_missing = Device(
        project_id=project.id,
        area_id=area.id,
        name="SW-MISSING",
        device_type="Switch",
        position_x=None,
        position_y=None,
        width=1.2,
        height=0.8,
    )
    session.add_all([device_existing, device_missing])
    await session.commit()
    await session.refresh(device_existing)
    await session.refresh(device_missing)
    return area, device_existing, device_missing


@pytest.mark.asyncio
async def test_apply_grouped_layout_preserve_existing_positions() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        area, device_existing, device_missing = await _seed_base(session)
        await apply_grouped_layout_to_db(
            session,
            device_layouts=[
                DeviceLayout(id=device_existing.id, area_id=area.id, x=7.0, y=7.0, layer=1),
                DeviceLayout(id=device_missing.id, area_id=area.id, x=6.0, y=6.0, layer=1),
            ],
            area_layouts=[
                AreaLayout(id=area.id, name=area.name, x=9.0, y=9.0, width=4.0, height=2.0)
            ],
            layout_scope="project",
            preserve_existing_positions=True,
        )

        updated_existing = (
            await session.execute(select(Device).where(Device.id == device_existing.id))
        ).scalar_one()
        updated_missing = (
            await session.execute(select(Device).where(Device.id == device_missing.id))
        ).scalar_one()
        updated_area = (
            await session.execute(select(Area).where(Area.id == area.id))
        ).scalar_one()

        assert updated_existing.position_x == 2.0
        assert updated_existing.position_y == 2.0
        assert updated_missing.position_x == 6.0
        assert updated_missing.position_y == 6.0
        assert updated_area.position_x == 1.0
        assert updated_area.position_y == 1.0

    await engine.dispose()


@pytest.mark.asyncio
async def test_apply_grouped_layout_overwrites_when_not_preserved() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        area, device_existing, _device_missing = await _seed_base(session)
        await apply_grouped_layout_to_db(
            session,
            device_layouts=[
                DeviceLayout(id=device_existing.id, area_id=area.id, x=7.0, y=7.0, layer=1),
            ],
            area_layouts=[
                AreaLayout(id=area.id, name=area.name, x=9.0, y=9.0, width=4.0, height=2.0)
            ],
            layout_scope="project",
            preserve_existing_positions=False,
        )

        updated_existing = (
            await session.execute(select(Device).where(Device.id == device_existing.id))
        ).scalar_one()
        updated_area = (
            await session.execute(select(Area).where(Area.id == area.id))
        ).scalar_one()

        assert updated_existing.position_x == 7.0
        assert updated_existing.position_y == 7.0
        assert updated_area.position_x == 9.0
        assert updated_area.position_y == 9.0

    await engine.dispose()
