import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import Area, Device, Project, User
from app.schemas.link import L1LinkCreate
from app.services.link import check_link_exists, check_port_in_use, create_link


@pytest.mark.asyncio
async def test_link_exists_and_port_in_use_exclude() -> None:
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

        device_a = Device(
            project_id=project.id,
            area_id=area.id,
            name="SW-A",
            device_type="Switch",
            width=1.2,
            height=0.5,
        )
        device_b = Device(
            project_id=project.id,
            area_id=area.id,
            name="SW-B",
            device_type="Switch",
            width=1.2,
            height=0.5,
        )
        session.add_all([device_a, device_b])
        await session.commit()
        await session.refresh(device_a)
        await session.refresh(device_b)

        link = await create_link(
            session,
            project.id,
            device_a,
            device_b,
            L1LinkCreate(
                from_device="SW-A",
                from_port="Gi 0/1",
                to_device="SW-B",
                to_port="Gi 0/2",
                purpose="LAN",
                line_style="solid",
            ),
        )

        assert await check_link_exists(
            session,
            project.id,
            device_a.id,
            "Gi 0/1",
            device_b.id,
            "Gi 0/2",
        )
        assert not await check_link_exists(
            session,
            project.id,
            device_a.id,
            "Gi 0/1",
            device_b.id,
            "Gi 0/2",
            exclude_link_id=link.id,
        )
        assert not await check_link_exists(
            session,
            project.id,
            device_b.id,
            "Gi 0/2",
            device_a.id,
            "Gi 0/1",
            exclude_link_id=link.id,
        )

        assert await check_port_in_use(session, project.id, device_a.id, "Gi 0/1")
        assert not await check_port_in_use(
            session,
            project.id,
            device_a.id,
            "Gi 0/1",
            exclude_link_id=link.id,
        )

    await engine.dispose()
