from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import generate_uuid

from app.core.config import DATABASE_URL
from app.db.base import Base

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False, "timeout": 30},
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def _column_exists(conn, table: str, column: str) -> bool:
    result = await conn.execute(text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result.fetchall())


async def _ensure_column(conn, table: str, column: str, definition: str) -> None:
    if await _column_exists(conn, table, column):
        return
    await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


async def _backfill_device_ports(conn) -> None:
    result = await conn.execute(
        text(
            """
            SELECT project_id, from_device_id AS device_id, from_port AS port_name
            FROM l1_links
            WHERE from_port IS NOT NULL AND TRIM(from_port) <> ''
            UNION
            SELECT project_id, to_device_id AS device_id, to_port AS port_name
            FROM l1_links
            WHERE to_port IS NOT NULL AND TRIM(to_port) <> ''
            """
        )
    )
    rows = result.fetchall()
    if not rows:
        return

    for row in rows:
        await conn.execute(
            text(
                """
                INSERT OR IGNORE INTO device_ports (
                    id, project_id, device_id, name, side, offset_ratio, created_at, updated_at
                ) VALUES (
                    :id, :project_id, :device_id, :name, 'bottom', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": generate_uuid(),
                "project_id": row[0],
                "device_id": row[1],
                "name": str(row[2]).strip(),
            },
        )


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA busy_timeout=30000"))
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_column(conn, "areas", "grid_range", "TEXT")
        await _ensure_column(conn, "devices", "grid_range", "TEXT")
        await _backfill_device_ports(conn)


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
