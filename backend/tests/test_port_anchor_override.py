import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

from app.db.base import Base
from app.db.models import Project, Area, Device, User
from app.services.port_anchor_override import (
    get_override_by_port,
    upsert_override,
    delete_override,
)
from app.schemas.port_anchor_override import PortAnchorOverrideCreate


@pytest.mark.asyncio
async def test_port_anchor_override_crud() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        user = User(
            email="tester@example.com",
            hashed_password="hash",
            display_name="Tester",
            is_active=True,
            is_admin=False,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        project = Project(name="Test Project", owner_id=user.id)
        session.add(project)
        await session.commit()
        await session.refresh(project)

        area = Area(
            project_id=project.id,
            name="Test Area",
            grid_row=1,
            grid_col=1,
            width=3.0,
            height=1.5,
        )
        session.add(area)
        await session.commit()
        await session.refresh(area)

        device = Device(
            project_id=project.id,
            area_id=area.id,
            name="SW-1",
            device_type="Switch",
            width=1.2,
            height=0.5,
        )
        session.add(device)
        await session.commit()
        await session.refresh(device)

        created = await upsert_override(
            session,
            project.id,
            PortAnchorOverrideCreate(
                device_id=device.id,
                port_name="Gi 0/1",
                side="left",
                offset_ratio=0.25,
            ),
        )
        assert created.device_id == device.id
        assert created.port_name == "Gi 0/1"
        assert created.side == "left"
        assert created.offset_ratio == 0.25

        updated = await upsert_override(
            session,
            project.id,
            PortAnchorOverrideCreate(
                device_id=device.id,
                port_name="Gi 0/1",
                side="right",
                offset_ratio=0.75,
            ),
        )
        assert updated.id == created.id
        assert updated.side == "right"
        assert updated.offset_ratio == 0.75

        fetched = await get_override_by_port(session, project.id, device.id, "Gi 0/1")
        assert fetched is not None
        assert fetched.side == "right"

        await delete_override(session, fetched)
        removed = await get_override_by_port(session, project.id, device.id, "Gi 0/1")
        assert removed is None

    await engine.dispose()
