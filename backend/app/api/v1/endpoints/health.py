from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    status = "healthy"
    db_status = "connected"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        status = "degraded"
        db_status = "error"

    return {
        "status": status,
        "database": db_status,
        "version": "0.1.0",
    }
