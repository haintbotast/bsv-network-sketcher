"""
Auto-Layout API endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import device as device_service
from app.services import link as link_service
from app.services import area as area_service
from app.services.admin_config import get_admin_config
from app.services.layout_models import LayoutConfig
from app.services.simple_layer_layout import simple_layer_layout
from app.services.layout_cache import get_cache
from app.services.device_sizing import (
    compute_device_port_counts,
    auto_resize_devices_by_ports,
)
from app.services.grid_sync import sync_device_grid_from_geometry
from app.schemas.layout import (
    AutoLayoutOptions,
    LayoutResult,
    DeviceLayout,
    LayoutStats,
)

from .layout_constants import DEFAULT_DEVICE_WIDTH, DEFAULT_DEVICE_HEIGHT
from .layout_geometry import effective_node_size, collect_device_ports, estimate_label_clearance
from .topology_normalizer import normalize_topology
from .waypoint_manager import create_or_update_waypoint_areas
from .layout_db import apply_layout_to_db, apply_grouped_layout_to_db

# Re-export for backward compatibility (tests import these)
from .layout_l1 import compute_layout_l1  # noqa: F401
from .layout_l2 import compute_layout_l2  # noqa: F401
from .layout_l3 import compute_layout_l3  # noqa: F401


router = APIRouter()


@router.post("/projects/{project_id}/auto-layout", response_model=LayoutResult)
async def compute_auto_layout(
    project_id: str,
    options: AutoLayoutOptions,
    db: AsyncSession = Depends(get_db),
):
    """
    Compute auto-layout for project using simple layer topology-aware algorithm.
    """

    # Load topology data
    devices = await device_service.get_devices(db, project_id)
    if not devices:
        raise HTTPException(status_code=404, detail="No devices found in project")

    links = await link_service.get_links(db, project_id)
    if not links and not options.group_by_area:
        raise HTTPException(status_code=404, detail="No links found in project")
    links = links or []

    # Auto-resize devices based on port count (if enabled)
    if options.auto_resize_devices and options.apply_to_db:
        port_stats = await compute_device_port_counts(db, project_id)
        await auto_resize_devices_by_ports(db, project_id, port_stats)
        devices = await device_service.get_devices(db, project_id)

    admin_config = await get_admin_config(db)
    layout_tuning = admin_config.get("layout_tuning", {}) if isinstance(admin_config, dict) else {}
    render_tuning = admin_config.get("render_tuning", {}) if isinstance(admin_config, dict) else {}

    # Load data based on view_mode
    view_mode = options.view_mode
    areas = []
    l2_assignments = []
    l2_segments = []
    l3_addresses = []

    if view_mode == "L1" and options.group_by_area:
        areas = await area_service.get_areas(db, project_id)
        if not areas:
            raise HTTPException(status_code=404, detail="No areas found in project")
        if options.normalize_topology and options.apply_to_db:
            areas, devices = await normalize_topology(db, project_id, areas, devices, links)
    elif view_mode == "L2":
        from app.db.models import InterfaceL2Assignment, L2Segment
        from sqlalchemy import select

        result = await db.execute(
            select(InterfaceL2Assignment).where(InterfaceL2Assignment.project_id == project_id)
        )
        l2_assignments = result.scalars().all()

        result = await db.execute(
            select(L2Segment).where(L2Segment.project_id == project_id)
        )
        l2_segments = result.scalars().all()

        if not l2_assignments:
            raise HTTPException(status_code=404, detail="No L2 assignments found in project")
    elif view_mode == "L3":
        from app.db.models import L3Address
        from sqlalchemy import select

        result = await db.execute(
            select(L3Address).where(L3Address.project_id == project_id)
        )
        l3_addresses = result.scalars().all()

        if not l3_addresses:
            raise HTTPException(status_code=404, detail="No L3 addresses found in project")

    node_width = DEFAULT_DEVICE_WIDTH
    node_height = DEFAULT_DEVICE_HEIGHT
    port_label_band = 0.0
    label_band = 0.0
    if view_mode == "L1":
        try:
            port_label_band = float(layout_tuning.get("port_label_band", 0.0))
        except (TypeError, ValueError):
            port_label_band = 0.0
        if port_label_band < 0:
            port_label_band = 0.0
    if view_mode in ("L2", "L3"):
        try:
            label_band = float(layout_tuning.get("label_band", 0.45))
        except (TypeError, ValueError):
            label_band = 0.45
        if label_band < 0:
            label_band = 0.0

    extra_width = 0.0
    extra_height = 0.0
    if view_mode == "L1" and port_label_band:
        extra_width = port_label_band * 2
        extra_height = port_label_band * 2
    if view_mode in ("L2", "L3") and label_band:
        extra_height += label_band

    node_width, node_height = effective_node_size(
        devices,
        DEFAULT_DEVICE_WIDTH,
        DEFAULT_DEVICE_HEIGHT,
        extra_width=extra_width,
        extra_height=extra_height,
    )

    # Check cache
    cache = get_cache()
    options_hash = {
        "layer_gap": options.layer_gap,
        "node_spacing": options.node_spacing,
        "group_by_area": options.group_by_area,
        "layout_scope": options.layout_scope,
        "view_mode": options.view_mode,
        "normalize_topology": options.normalize_topology,
        "layout_tuning": layout_tuning,
    }

    if view_mode == "L1":
        topology_hash = cache.compute_topology_hash(devices, links, options_hash, areas if options.group_by_area else None)
    elif view_mode == "L2":
        topology_hash = cache.compute_topology_hash(devices, links, options_hash, l2_assignments)
    elif view_mode == "L3":
        topology_hash = cache.compute_topology_hash(devices, links, options_hash, l3_addresses)
    else:
        topology_hash = cache.compute_topology_hash(devices, links, options_hash, None)

    cached_result = cache.get(project_id, topology_hash)
    if cached_result and not options.apply_to_db:
        return LayoutResult(**cached_result)

    # Compute layout
    config = LayoutConfig(
        layer_gap=options.layer_gap,
        node_spacing=options.node_spacing,
        node_width=node_width,
        node_height=node_height,
    )
    if view_mode == "L1" and not options.group_by_area and port_label_band:
        config = LayoutConfig(
            layer_gap=options.layer_gap + port_label_band,
            node_spacing=options.node_spacing + port_label_band,
            node_width=node_width,
            node_height=node_height,
        )

    try:
        if view_mode == "L1":
            if options.group_by_area:
                non_wp_areas = [a for a in areas if not a.name.endswith("_wp_")]
                response = compute_layout_l1(
                    devices,
                    links,
                    non_wp_areas,
                    config,
                    options.layout_scope,
                    layout_tuning,
                    render_tuning,
                )
            else:
                label_clearance_x, label_clearance_y = estimate_label_clearance(
                    collect_device_ports(links),
                    render_tuning,
                )
                try:
                    row_stagger = float(layout_tuning.get("row_stagger", 0.5))
                except (TypeError, ValueError):
                    row_stagger = 0.5
                row_stagger = max(0.0, min(row_stagger, 1.0))
                config = LayoutConfig(
                    layer_gap=config.layer_gap + label_clearance_y,
                    node_spacing=config.node_spacing + label_clearance_x,
                    node_width=node_width,
                    node_height=node_height,
                    row_gap=max(0.2, (config.node_spacing + label_clearance_x) * 0.6) + label_clearance_y,
                    row_stagger=row_stagger,
                )
                layout_result = simple_layer_layout(devices, links, config)
                response = {
                    "devices": [
                        DeviceLayout(
                            id=d["id"],
                            area_id=None,
                            x=d["x"],
                            y=d["y"],
                            layer=d["layer"],
                        )
                        for d in layout_result.devices
                    ],
                    "areas": None,
                    "vlan_groups": None,
                    "subnet_groups": None,
                    "stats": LayoutStats(**layout_result.stats),
                }
        elif view_mode == "L2":
            response = compute_layout_l2(devices, links, l2_assignments, l2_segments, config, layout_tuning)
            response["areas"] = None
            response["subnet_groups"] = None
        elif view_mode == "L3":
            response = compute_layout_l3(devices, links, l3_addresses, config, layout_tuning)
            response["areas"] = None
            response["vlan_groups"] = None
        else:
            raise HTTPException(status_code=400, detail=f"Unknown view_mode: {view_mode}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Layout computation failed: {str(e)}"
        )

    # Tạo waypoint areas cho inter-area links
    if options.apply_to_db and options.group_by_area and view_mode == "L1":
        await create_or_update_waypoint_areas(
            db, project_id, response, areas, links, devices
        )

    # Cache result
    cache.set(project_id, topology_hash, response)

    # Apply to database if requested
    if options.apply_to_db:
        if view_mode == "L1":
            if options.group_by_area:
                await apply_grouped_layout_to_db(
                    db,
                    response["devices"],
                    response.get("areas"),
                    options.layout_scope,
                    preserve_existing_positions=options.preserve_existing_positions,
                )
            else:
                device_dicts = [
                    {"id": d.id, "x": d.x, "y": d.y, "layer": d.layer}
                    for d in response["devices"]
                ]
                await apply_layout_to_db(
                    db,
                    device_dicts,
                    preserve_existing_positions=options.preserve_existing_positions,
                )
        elif view_mode in ("L2", "L3"):
            for layout in response["devices"]:
                from app.db.models import Device
                from sqlalchemy import select

                result = await db.execute(select(Device).where(Device.id == layout.id))
                device = result.scalar_one_or_none()
                if device:
                    has_existing_position = (
                        device.position_x is not None and device.position_y is not None
                    )
                    if options.preserve_existing_positions and has_existing_position:
                        continue
                    device.position_x = layout.x
                    device.position_y = layout.y
                    sync_device_grid_from_geometry(
                        device,
                        default_width=DEFAULT_DEVICE_WIDTH,
                        default_height=DEFAULT_DEVICE_HEIGHT,
                    )
            await db.commit()

    return LayoutResult(**response)


@router.post("/projects/{project_id}/invalidate-layout-cache")
async def invalidate_layout_cache(project_id: str):
    """
    Invalidate cached layout for project.
    """
    cache = get_cache()
    cache.invalidate(project_id)

    return {"message": "Layout cache invalidated", "project_id": project_id}
