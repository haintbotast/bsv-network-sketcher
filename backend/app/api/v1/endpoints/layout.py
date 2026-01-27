"""
Auto-Layout API endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import device as device_service
from app.services import link as link_service
from app.services import area as area_service
from app.services.layout_engine import auto_layout, LayoutConfig
from app.services.layout_cache import get_cache
from app.schemas.layout import (
    AutoLayoutOptions,
    LayoutResult,
    DeviceLayout,
    LayoutStats,
    AreaLayout,
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
    if not links and not options.group_by_area:
        raise HTTPException(status_code=404, detail="No links found in project")
    links = links or []

    areas = []
    if options.group_by_area:
        areas = await area_service.get_areas(db, project_id)
        if not areas:
            raise HTTPException(status_code=404, detail="No areas found in project")

    # Check cache
    cache = get_cache()
    options_hash = {
        "algorithm": options.algorithm,
        "direction": options.direction,
        "layer_gap": options.layer_gap,
        "node_spacing": options.node_spacing,
        "crossing_iterations": options.crossing_iterations,
        "group_by_area": options.group_by_area,
        "layout_scope": options.layout_scope,
    }
    topology_hash = cache.compute_topology_hash(devices, links, options_hash, areas if options.group_by_area else None)

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
        if options.group_by_area:
            response = build_grouped_layout(devices, links, areas, config, options.layout_scope)
        else:
            layout_result = auto_layout(devices, links, config)
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
                "stats": LayoutStats(**layout_result.stats),
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Layout computation failed: {str(e)}"
        )

    # Cache result
    cache.set(project_id, topology_hash, response)

    # Apply to database if requested
    if options.apply_to_db:
        if options.group_by_area:
            await apply_grouped_layout_to_db(db, response["devices"], response.get("areas"), options.layout_scope)
        else:
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


def build_grouped_layout(
    devices: list,
    links: list,
    areas: list,
    config: LayoutConfig,
    layout_scope: str,
) -> dict:
    """Compute layout per-area (macro Area + micro Device)."""
    AREA_MIN_WIDTH = 3.0
    AREA_MIN_HEIGHT = 1.5
    AREA_GAP = 0.6
    AREA_PADDING = 0.15
    LABEL_BAND = 0.25

    # Resolve area sizes
    area_sizes = {
        a.id: {
            "width": a.width if a.width and a.width > 0 else AREA_MIN_WIDTH,
            "height": a.height if a.height and a.height > 0 else AREA_MIN_HEIGHT,
            "grid_row": a.grid_row or 1,
            "grid_col": a.grid_col or 1,
            "x": a.position_x,
            "y": a.position_y,
            "name": a.name,
        }
        for a in areas
    }

    def compute_area_grid_positions() -> dict[str, tuple[float, float]]:
        rows: dict[int, list[str]] = {}
        for area_id, meta in area_sizes.items():
            rows.setdefault(meta["grid_row"], []).append(area_id)

        positions: dict[str, tuple[float, float]] = {}
        current_y = 0.0
        for row in sorted(rows.keys()):
            row_area_ids = rows[row]
            row_area_ids.sort(key=lambda aid: area_sizes[aid]["grid_col"])
            row_height = max(area_sizes[aid]["height"] for aid in row_area_ids)
            current_x = 0.0
            for aid in row_area_ids:
                positions[aid] = (current_x, current_y)
                current_x += area_sizes[aid]["width"] + AREA_GAP
            current_y += row_height + AREA_GAP
        return positions

    area_positions: dict[str, tuple[float, float]] = {}
    grid_positions = compute_area_grid_positions()

    if layout_scope == "project":
        area_positions = grid_positions
    else:
        for area_id, meta in area_sizes.items():
            if meta["x"] is not None and meta["y"] is not None:
                area_positions[area_id] = (meta["x"], meta["y"])
            else:
                area_positions[area_id] = grid_positions.get(area_id, (0.0, 0.0))

    device_layouts: list[DeviceLayout] = []
    area_layouts: list[AreaLayout] = []
    stats_layers = []
    stats_crossings = []
    stats_times = []

    devices_by_area: dict[str, list] = {}
    for device in devices:
        if not device.area_id:
            continue
        devices_by_area.setdefault(device.area_id, []).append(device)

    for area_id, meta in area_sizes.items():
        area_x, area_y = area_positions.get(area_id, (0.0, 0.0))
        area_width = meta["width"]
        area_height = meta["height"]

        area_layouts.append(AreaLayout(
            id=area_id,
            name=meta["name"],
            x=area_x,
            y=area_y,
            width=area_width,
            height=area_height,
        ))

        area_devices = devices_by_area.get(area_id, [])
        if not area_devices:
            continue

        device_ids = {d.id for d in area_devices}
        area_links = [l for l in links if l.from_device_id in device_ids and l.to_device_id in device_ids]

        micro_config = LayoutConfig(
            direction="vertical",  # top-to-bottom per AI Context
            layer_gap=config.layer_gap,
            node_spacing=config.node_spacing,
            crossing_iterations=config.crossing_iterations,
        )
        layout_result = auto_layout(area_devices, area_links, micro_config)

        if layout_result.devices:
            min_x = min(d["x"] for d in layout_result.devices)
            min_y = min(d["y"] for d in layout_result.devices)
            max_x = max(d["x"] for d in layout_result.devices) + micro_config.node_width
            max_y = max(d["y"] for d in layout_result.devices) + micro_config.node_height
        else:
            min_x = min_y = 0.0
            max_x = micro_config.node_width
            max_y = micro_config.node_height

        span_x = max_x - min_x
        span_y = max_y - min_y

        inner_width = max(area_width - AREA_PADDING * 2, micro_config.node_width)
        inner_height = max(area_height - LABEL_BAND - AREA_PADDING * 2, micro_config.node_height)

        scale_x = 1.0
        if span_x > micro_config.node_width and inner_width > micro_config.node_width:
            scale_x = min(1.0, (inner_width - micro_config.node_width) / (span_x - micro_config.node_width))
        scale_y = 1.0
        if span_y > micro_config.node_height and inner_height > micro_config.node_height:
            scale_y = min(1.0, (inner_height - micro_config.node_height) / (span_y - micro_config.node_height))
        scale = min(scale_x, scale_y, 1.0)

        for d in layout_result.devices:
            device_layouts.append(DeviceLayout(
                id=d["id"],
                area_id=area_id,
                x=area_x + AREA_PADDING + (d["x"] - min_x) * scale,
                y=area_y + LABEL_BAND + AREA_PADDING + (d["y"] - min_y) * scale,
                layer=d["layer"],
            ))

        stats_layers.append(layout_result.stats["total_layers"])
        stats_crossings.append(layout_result.stats["total_crossings"])
        stats_times.append(layout_result.stats["execution_time_ms"])

    # Handle devices without area (fallback to global)
    no_area_devices = [d for d in devices if not d.area_id]
    if no_area_devices:
        layout_result = auto_layout(no_area_devices, links, config)
        for d in layout_result.devices:
            device_layouts.append(DeviceLayout(
                id=d["id"],
                area_id=None,
                x=d["x"],
                y=d["y"],
                layer=d["layer"],
            ))
        stats_layers.append(layout_result.stats["total_layers"])
        stats_crossings.append(layout_result.stats["total_crossings"])
        stats_times.append(layout_result.stats["execution_time_ms"])

    stats = LayoutStats(
        total_layers=max(stats_layers) if stats_layers else 0,
        total_crossings=sum(stats_crossings) if stats_crossings else 0,
        execution_time_ms=sum(stats_times) if stats_times else 0,
        algorithm="sugiyama_grouped",
    )

    return {
        "devices": device_layouts,
        "areas": area_layouts,
        "stats": stats,
    }


async def apply_grouped_layout_to_db(
    db: AsyncSession,
    device_layouts: list[DeviceLayout],
    area_layouts: list[AreaLayout] | None,
    layout_scope: str,
) -> None:
    """Apply grouped layout to DB (devices always, areas when scope=project)."""
    from app.db.models import Device, Area
    from sqlalchemy import select

    for layout in device_layouts:
        result = await db.execute(select(Device).where(Device.id == layout.id))
        device = result.scalar_one_or_none()
        if device:
            device.position_x = layout.x
            device.position_y = layout.y

    if layout_scope == "project" and area_layouts:
        for layout in area_layouts:
            result = await db.execute(select(Area).where(Area.id == layout.id))
            area = result.scalar_one_or_none()
            if area:
                area.position_x = layout.x
                area.position_y = layout.y
                area.width = layout.width
                area.height = layout.height

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
