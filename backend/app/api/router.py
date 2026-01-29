from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.areas import router as areas_router
from app.api.v1.endpoints.devices import router as devices_router
from app.api.v1.endpoints.links import router as links_router
from app.api.v1.endpoints.l2_segments import router as l2_segments_router
from app.api.v1.endpoints.l2_assignments import router as l2_assignments_router
from app.api.v1.endpoints.l3_addresses import router as l3_addresses_router
from app.api.v1.endpoints.port_channels import router as port_channels_router
from app.api.v1.endpoints.virtual_ports import router as virtual_ports_router
from app.api.v1.endpoints.import_data import router as import_router
from app.api.v1.endpoints.export import router as export_router
from app.api.v1.endpoints.admin_config import router as admin_config_router
from app.api.v1.endpoints.ws import router as ws_router
from app.api.v1.endpoints.layout import router as layout_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(areas_router)
api_router.include_router(devices_router)
api_router.include_router(links_router)
api_router.include_router(l2_segments_router)
api_router.include_router(l2_assignments_router)
api_router.include_router(l3_addresses_router)
api_router.include_router(port_channels_router)
api_router.include_router(virtual_ports_router)
api_router.include_router(import_router)
api_router.include_router(export_router)
api_router.include_router(admin_config_router)
api_router.include_router(ws_router)
api_router.include_router(layout_router)
