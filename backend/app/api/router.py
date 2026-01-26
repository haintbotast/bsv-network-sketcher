from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.areas import router as areas_router
from app.api.v1.endpoints.devices import router as devices_router
from app.api.v1.endpoints.links import router as links_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(areas_router)
api_router.include_router(devices_router)
api_router.include_router(links_router)
