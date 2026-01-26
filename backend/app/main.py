from fastapi import FastAPI

from app.api.router import api_router
from app.db.session import init_db

app = FastAPI(title="BSV Network Sketcher API", version="0.1.0")
app.include_router(api_router)


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()
