"""WebSocket endpoint cho realtime updates."""

import asyncio
import os
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db.session import async_session_maker
from app.services import export_job as export_job_service
from app.services import project as project_service
from app.services.auth import decode_token, get_user_by_id
from app.services.ws_manager import ws_manager

router = APIRouter()


async def _authenticate_websocket(websocket: WebSocket, project_id: str) -> Optional[str]:
    token = websocket.query_params.get("token")
    if not token:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()

    if not token:
        await websocket.close(code=1008)
        return None

    token_data = decode_token(token)
    if token_data is None:
        await websocket.close(code=1008)
        return None

    async with async_session_maker() as db:
        user = await get_user_by_id(db, token_data.user_id)
        if not user or not user.is_active:
            await websocket.close(code=1008)
            return None
        project = await project_service.get_project_by_id(db, project_id, user.id)
        if not project:
            await websocket.close(code=1008)
            return None
    return token_data.user_id


def _build_export_event(event: str, job) -> dict[str, Any]:
    return {
        "event": event,
        "data": {
            "id": job.id,
            "project_id": job.project_id,
            "export_type": job.export_type,
            "status": job.status,
            "progress": job.progress,
            "message": job.message,
            "file_name": job.file_name,
            "file_size": job.file_size,
            "error_message": job.error_message,
        },
    }


async def _poll_export_jobs(project_id: str, websocket: WebSocket, stop_event: asyncio.Event) -> None:
    poll_interval = float(os.getenv("WS_EXPORT_POLL_INTERVAL", "2"))
    last_snapshot: dict[str, tuple] = {}

    while not stop_event.is_set():
        async with async_session_maker() as db:
            jobs = await export_job_service.list_jobs(db, project_id, skip=0, limit=50)

        for job in jobs:
            snapshot = (
                job.status,
                job.progress,
                job.file_name,
                job.error_message,
            )
            previous = last_snapshot.get(job.id)
            if snapshot == previous:
                continue

            last_snapshot[job.id] = snapshot
            if job.status == "completed":
                event = "export.completed"
            elif job.status == "failed":
                event = "export.failed"
            else:
                event = "export.progress"

            await ws_manager.send_json(websocket, _build_export_event(event, job))

        await asyncio.sleep(poll_interval)


@router.websocket("/ws/projects/{project_id}")
async def websocket_project_updates(websocket: WebSocket, project_id: str) -> None:
    user_id = await _authenticate_websocket(websocket, project_id)
    if not user_id:
        return

    await ws_manager.connect(project_id, websocket)
    stop_event = asyncio.Event()
    poll_task = asyncio.create_task(_poll_export_jobs(project_id, websocket, stop_event))

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        stop_event.set()
        poll_task.cancel()
        ws_manager.disconnect(project_id, websocket)
