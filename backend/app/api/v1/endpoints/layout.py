"""
Auto-Layout API endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import device as device_service
from app.services import link as link_service
from app.services.layout_engine import auto_layout, LayoutConfig
from app.services.layout_cache import get_cache
from app.schemas.layout import (
    AutoLayoutOptions,
    LayoutResult,
    DeviceLayout,
    LayoutStats,
)


router = APIRouter()


@router.post("/projects/{project_id}/auto-layout", response_model=LayoutResult)
async def compute_auto_layout(
    project_id: str,
    options: AutoLayoutOptions,
    db: AsyncSession = Depends(get_db),
):
    """
    Compute auto-layout for project using Sugiyama algorithm.

    Args:
        project_id: Project ID
        options: Layout options
        db: Database session

    Returns:
        LayoutResult with device coordinates and stats

    Raises:
        HTTPException: If project not found or computation fails
    """

    # Load topology data
    devices = await device_service.get_devices(db, project_id)
    if not devices:
        raise HTTPException(status_code=404, detail="No devices found in project")

    links = await link_service.get_links(db, project_id)
    if not links:
        raise HTTPException(status_code=404, detail="No links found in project")

    # Check cache
    cache = get_cache()
    topology_hash = cache.compute_topology_hash(devices, links)

    cached_result = cache.get(project_id, topology_hash)
    if cached_result and not options.apply_to_db:
        # Return cached result for preview
        return LayoutResult(**cached_result)

    # Compute layout
    config = LayoutConfig(
        direction=options.direction,
        layer_gap=options.layer_gap,
        node_spacing=options.node_spacing,
        crossing_iterations=options.crossing_iterations,
    )

    try:
        layout_result = auto_layout(devices, links, config)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Layout computation failed: {str(e)}"
        )

    # Build response
    response = {
        "devices": [
            DeviceLayout(
                id=d["id"],
                x=d["x"],
                y=d["y"],
                layer=d["layer"],
            )
            for d in layout_result.devices
        ],
        "areas": None,  # Future enhancement
        "stats": LayoutStats(**layout_result.stats),
    }

    # Cache result
    cache.set(project_id, topology_hash, response)

    # Apply to database if requested
    if options.apply_to_db:
        await apply_layout_to_db(db, layout_result.devices)

    return LayoutResult(**response)


async def apply_layout_to_db(db: AsyncSession, device_layouts: list[dict]) -> None:
    """
    Apply layout coordinates to database.

    Args:
        db: Database session
        device_layouts: List of device layout dicts

    Updates device.position_x and device.position_y in database.
    Also updates area positions based on device bounds.
    """
    from app.db.models import Device, Area
    from sqlalchemy import select
    from collections import defaultdict

    # Update device positions
    area_devices = defaultdict(list)

    for layout in device_layouts:
        device_id = layout["id"]
        x = layout["x"]
        y = layout["y"]

        # Load device
        result = await db.execute(
            select(Device).where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()

        if device:
            device.position_x = x
            device.position_y = y

            # Track devices by area for bounds calculation
            if device.area_id:
                area_devices[device.area_id].append({
                    "x": x,
                    "y": y,
                    "width": 1.2,  # Default device width in inches
                    "height": 0.8   # Default device height in inches
                })

    # Update area positions based on device bounds
    AREA_PADDING = 0.3  # Padding around devices in inches

    for area_id, devices in area_devices.items():
        if not devices:
            continue

        # Calculate bounds
        min_x = min(d["x"] for d in devices)
        min_y = min(d["y"] for d in devices)
        max_x = max(d["x"] + d["width"] for d in devices)
        max_y = max(d["y"] + d["height"] for d in devices)

        # Apply padding
        area_x = min_x - AREA_PADDING
        area_y = min_y - AREA_PADDING
        area_width = (max_x - min_x) + 2 * AREA_PADDING
        area_height = (max_y - min_y) + 2 * AREA_PADDING

        # Update area
        result = await db.execute(
            select(Area).where(Area.id == area_id)
        )
        area = result.scalar_one_or_none()

        if area:
            area.position_x = area_x
            area.position_y = area_y
            area.width = area_width
            area.height = area_height

    await db.commit()


@router.post("/projects/{project_id}/invalidate-layout-cache")
async def invalidate_layout_cache(project_id: str):
    """
    Invalidate cached layout for project.

    Use this after topology changes (add/remove devices or links).

    Args:
        project_id: Project ID

    Returns:
        Success message
    """
    cache = get_cache()
    cache.invalidate(project_id)

    return {"message": "Layout cache invalidated", "project_id": project_id}
