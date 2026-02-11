from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import generate_uuid
from app.services.grid_excel import GRID_CELL_UNITS, parse_excel_range, rect_units_to_excel_range

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


async def _backfill_grid_ranges(conn) -> None:
    area_rows = (
        await conn.execute(
            text(
                """
                SELECT id, grid_row, grid_col, position_x, position_y, width, height
                FROM areas
                WHERE grid_range IS NULL OR TRIM(grid_range) = ''
                """
            )
        )
    ).fetchall()

    for row in area_rows:
        grid_row = int(row[1] or 1)
        grid_col = int(row[2] or 1)
        position_x = float(row[3]) if row[3] is not None else (max(1, grid_col) - 1) * GRID_CELL_UNITS
        position_y = float(row[4]) if row[4] is not None else (max(1, grid_row) - 1) * GRID_CELL_UNITS
        width = float(row[5]) if row[5] is not None else GRID_CELL_UNITS
        height = float(row[6]) if row[6] is not None else GRID_CELL_UNITS
        grid_range = rect_units_to_excel_range(position_x, position_y, width, height)
        col_start, row_start, _col_end, _row_end = parse_excel_range(grid_range)
        await conn.execute(
            text(
                """
                UPDATE areas
                SET grid_range = :grid_range,
                    grid_row = :grid_row,
                    grid_col = :grid_col
                WHERE id = :id
                """
            ),
            {
                "id": row[0],
                "grid_range": grid_range,
                "grid_row": row_start,
                "grid_col": col_start,
            },
        )

    device_rows = (
        await conn.execute(
            text(
                """
                SELECT id, position_x, position_y, width, height
                FROM devices
                WHERE grid_range IS NULL OR TRIM(grid_range) = ''
                """
            )
        )
    ).fetchall()

    for row in device_rows:
        position_x = float(row[1]) if row[1] is not None else 0.0
        position_y = float(row[2]) if row[2] is not None else 0.0
        width = float(row[3]) if row[3] is not None else GRID_CELL_UNITS
        height = float(row[4]) if row[4] is not None else GRID_CELL_UNITS
        grid_range = rect_units_to_excel_range(position_x, position_y, width, height)
        await conn.execute(
            text(
                """
                UPDATE devices
                SET grid_range = :grid_range
                WHERE id = :id
                """
            ),
            {
                "id": row[0],
                "grid_range": grid_range,
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
        await _ensure_column(conn, "l1_links", "color_rgb_json", "TEXT")
        await _backfill_grid_ranges(conn)
        await _backfill_device_ports(conn)


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
