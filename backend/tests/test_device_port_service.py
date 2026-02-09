import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import Area, Device, Project, User
from app.schemas.device_port import DevicePortCreate, DevicePortUpdate
from app.services.device_port import (
    create_port,
    delete_port,
    get_port_by_name,
    get_ports_by_device,
    update_port,
)


@pytest.mark.asyncio
async def test_device_port_service_crud() -> None:
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

        project = Project(name="Port Project", owner_id=user.id)
        session.add(project)
        await session.commit()
        await session.refresh(project)

        area = Area(
            project_id=project.id,
            name="Area-1",
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

        created = await create_port(
            session,
            project.id,
            device,
            DevicePortCreate(name="Gi 0/1", side="top", offset_ratio=0.3),
        )
        assert created.device_id == device.id
        assert created.name == "Gi 0/1"
        assert created.side == "top"

        fetched = await get_port_by_name(session, project.id, device.id, "Gi 0/1")
        assert fetched is not None
        assert fetched.id == created.id

        updated = await update_port(
            session,
            fetched,
            DevicePortUpdate(name="Gi 0/2", side="bottom", offset_ratio=0.8),
        )
        assert updated.name == "Gi 0/2"
        assert updated.side == "bottom"
        assert updated.offset_ratio == 0.8

        ports = await get_ports_by_device(session, project.id, device.id)
        assert len(ports) == 1
        assert ports[0].name == "Gi 0/2"

        await delete_port(session, ports[0])
        ports_after_delete = await get_ports_by_device(session, project.id, device.id)
        assert ports_after_delete == []

    await engine.dispose()
