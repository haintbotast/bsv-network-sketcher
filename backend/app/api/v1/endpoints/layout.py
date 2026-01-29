"""
Auto-Layout API endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import device as device_service
from app.services import link as link_service
from app.services import area as area_service
from app.services.layout_models import LayoutConfig
from app.services.simple_layer_layout import simple_layer_layout
from app.services.layout_cache import get_cache
from app.schemas.layout import (
    AutoLayoutOptions,
    LayoutResult,
    DeviceLayout,
    LayoutStats,
    AreaLayout,
    VlanGroupLayout,
    SubnetGroupLayout,
)


router = APIRouter()


@router.post("/projects/{project_id}/auto-layout", response_model=LayoutResult)
async def compute_auto_layout(
    project_id: str,
    options: AutoLayoutOptions,
    db: AsyncSession = Depends(get_db),
):
    """
    Compute auto-layout for project using simple layer topology-aware algorithm.

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
    elif view_mode == "L2":
        # Load L2 assignments and segments
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
        # Load L3 addresses
        from app.db.models import L3Address
        from sqlalchemy import select

        result = await db.execute(
            select(L3Address).where(L3Address.project_id == project_id)
        )
        l3_addresses = result.scalars().all()

        if not l3_addresses:
            raise HTTPException(status_code=404, detail="No L3 addresses found in project")

    # Check cache
    cache = get_cache()
    options_hash = {
        "layer_gap": options.layer_gap,
        "node_spacing": options.node_spacing,
        "group_by_area": options.group_by_area,
        "layout_scope": options.layout_scope,
        "view_mode": options.view_mode,
    }

    # Different cache keys for different views
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
        # Return cached result for preview
        return LayoutResult(**cached_result)

    # Compute layout
    config = LayoutConfig(
        layer_gap=options.layer_gap,
        node_spacing=options.node_spacing,
    )

    try:
        if view_mode == "L1":
            if options.group_by_area:
                response = compute_layout_l1(devices, links, areas, config, options.layout_scope)
            else:
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
            response = compute_layout_l2(devices, links, l2_assignments, l2_segments, config)
            response["areas"] = None
            response["subnet_groups"] = None
        elif view_mode == "L3":
            response = compute_layout_l3(devices, links, l3_addresses, config)
            response["areas"] = None
            response["vlan_groups"] = None
        else:
            raise HTTPException(status_code=400, detail=f"Unknown view_mode: {view_mode}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Layout computation failed: {str(e)}"
        )

    # Cache result
    cache.set(project_id, topology_hash, response)

    # Apply to database if requested
    if options.apply_to_db:
        if view_mode == "L1":
            if options.group_by_area:
                await apply_grouped_layout_to_db(db, response["devices"], response.get("areas"), options.layout_scope)
            else:
                # Convert DeviceLayout to dict for apply_layout_to_db
                device_dicts = [
                    {"id": d.id, "x": d.x, "y": d.y, "layer": d.layer}
                    for d in response["devices"]
                ]
                await apply_layout_to_db(db, device_dicts)
        elif view_mode in ("L2", "L3"):
            # For L2/L3 views, only apply device positions (no areas)
            for layout in response["devices"]:
                from app.db.models import Device
                from sqlalchemy import select

                result = await db.execute(select(Device).where(Device.id == layout.id))
                device = result.scalar_one_or_none()
                if device:
                    device.position_x = layout.x
                    device.position_y = layout.y
            await db.commit()

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


def compute_layout_l1(
    devices: list,
    links: list,
    areas: list,
    config: LayoutConfig,
    layout_scope: str,
) -> dict:
    """Compute L1 layout: area-based with minimized area visuals (compact spacing)."""
    AREA_MIN_WIDTH = 3.0
    AREA_MIN_HEIGHT = 1.5
    AREA_GAP = 0.5  # Reduced from 0.8 for compactness
    AREA_PADDING = 0.15  # Reduced from 0.25 for compactness
    LABEL_BAND = 0.35
    MAX_ROW_WIDTH_BASE = 12.0

    # Tier characteristics for enhanced layout (11 tiers: 0-10)
    TIER_CHARACTERISTICS = {
        0: {"max_areas_per_row": 2, "width_factor": 1.5, "priority": "wide"},
        1: {"max_areas_per_row": 2, "width_factor": 1.5, "priority": "wide"},
        2: {"max_areas_per_row": 2, "width_factor": 1.3, "priority": "wide"},
        3: {"max_areas_per_row": 2, "width_factor": 1.4, "priority": "wide"},
        4: {"max_areas_per_row": 2, "width_factor": 1.3, "priority": "wide"},
        5: {"max_areas_per_row": 3, "width_factor": 1.2, "priority": "medium"},
        6: {"max_areas_per_row": 3, "width_factor": 1.1, "priority": "medium"},
        7: {"max_areas_per_row": 4, "width_factor": 1.0, "priority": "narrow"},
        8: {"max_areas_per_row": 4, "width_factor": 1.0, "priority": "narrow"},
        9: {"max_areas_per_row": 4, "width_factor": 1.0, "priority": "narrow"},
        10: {"max_areas_per_row": 3, "width_factor": 1.2, "priority": "medium"},
    }

    def normalize(text: str | None) -> str:
        return (text or "").strip().lower()

    def detect_area_tier(name: str | None) -> int | None:
        """Detect area tier with enhanced granularity (0-10)."""
        label = normalize(name)
        tier_hints = [
            # Tier 0: Edge/WAN
            (0, ["edge", "wan", "internet", "isp"]),
            # Tier 1: Security
            (1, ["security", "firewall", "fw", "ids", "ips", "waf", "vpn"]),
            # Tier 2: DMZ
            (2, ["dmz", "proxy"]),
            # Tier 3: Core
            (3, ["core"]),
            # Tier 4: Distribution
            (4, ["distribution", "dist"]),
            # Tier 5: Campus (large sites)
            (5, ["campus", "hq", "headquarters", "main"]),
            # Tier 6: Branch (remote sites)
            (6, ["branch", "site", "remote"]),
            # Tier 7: Office (floor-level)
            (7, ["office", "floor", "building"]),
            # Tier 8: Department
            (8, ["department", "dept"]),
            # Tier 9: Project
            (9, ["project", "proj", "it"]),
            # Tier 10: Servers
            (10, ["server", "servers", "storage", "nas", "dc", "data center", "datacenter"]),
        ]
        for tier, keywords in tier_hints:
            if any(keyword in label for keyword in keywords):
                return tier
        return None  # Will fallback to device tier or default tier 7

    def detect_device_tier(device) -> int:
        """Detect device tier with enhanced granularity (0-10)."""
        name = normalize(getattr(device, "name", ""))
        dtype = normalize(getattr(device, "device_type", ""))
        tier_keywords = [
            (0, ["edge", "wan", "internet", "isp"]),
            (1, ["firewall", "fw", "ids", "ips", "waf", "security", "vpn"]),
            (2, ["dmz", "proxy"]),
            (3, ["core"]),
            (4, ["distribution", "dist"]),
            (5, ["campus"]),
            (6, ["branch"]),
            (7, ["office", "floor"]),
            (8, ["department", "dept"]),
            (9, ["project", "proj"]),
            (10, ["server", "storage", "nas", "san", "datacenter", "dc"]),
        ]
        for tier, keywords in tier_keywords:
            if any(keyword in name for keyword in keywords):
                return tier
        # Fallback by device_type
        if dtype == "firewall":
            return 1
        if dtype == "router":
            return 0
        if dtype == "switch":
            return 4
        if dtype in {"server", "storage"}:
            return 10
        if dtype == "ap":
            return 7  # Access points typically at office level
        if dtype in {"pc", "printer", "camera", "ipphone", "phone", "endpoint"}:
            return 10  # Endpoints grouped with servers for simplicity
        return 7  # Default: office tier

    def compute_max_row_width_per_tier(area_ids: list[str], tier: int) -> float:
        """
        Compute max row width tailored to tier characteristics.

        Strategy:
        1. Ensure 2 widest areas can fit in one row
        2. Apply tier-specific width factor
        3. Optimize for target columns per tier
        """
        if not area_ids:
            return MAX_ROW_WIDTH_BASE

        # Get tier characteristics
        tier_config = TIER_CHARACTERISTICS.get(tier, {
            "max_areas_per_row": 3,
            "width_factor": 1.0,
            "priority": "medium"
        })

        widths = [area_meta[aid]["computed_width"] for aid in area_ids]
        widths_sorted = sorted(widths, reverse=True)

        # Strategy 1: Ensure 2 widest areas can fit
        if len(widths_sorted) >= 2:
            min_width_for_two = widths_sorted[0] + widths_sorted[1] + AREA_GAP
        else:
            min_width_for_two = widths_sorted[0] if widths_sorted else AREA_MIN_WIDTH

        # Strategy 2: Apply tier-specific factor
        base_width = MAX_ROW_WIDTH_BASE * tier_config["width_factor"]

        # Strategy 3: Optimize for target columns
        avg_width = sum(widths) / len(widths)
        target_cols = min(tier_config["max_areas_per_row"], len(area_ids))
        suggested_width = avg_width * target_cols + AREA_GAP * (target_cols - 1)

        # Return max of all strategies
        return max(base_width, min_width_for_two, suggested_width)

    def pack_rows(area_ids: list[str], tier: int) -> list[list[str]]:
        """Pack areas into rows using tier-specific max width."""
        max_width = compute_max_row_width_per_tier(area_ids, tier)
        rows: list[list[str]] = []
        current: list[str] = []
        current_width = 0.0
        for aid in area_ids:
            width = area_meta[aid]["computed_width"]
            if current and current_width + AREA_GAP + width > max_width:
                rows.append(current)
                current = [aid]
                current_width = width
            else:
                if current:
                    current_width += AREA_GAP + width
                else:
                    current_width = width
                current.append(aid)
        if current:
            rows.append(current)
        return rows

    def row_width(row: list[str]) -> float:
        if not row:
            return 0.0
        return sum(area_meta[aid]["computed_width"] for aid in row) + AREA_GAP * (len(row) - 1)

    def row_height(row: list[str]) -> float:
        if not row:
            return 0.0
        return max(area_meta[aid]["computed_height"] for aid in row)

    def compute_macro_positions(area_tiers: dict[int, list[str]]) -> dict[str, tuple[float, float]]:
        positions: dict[str, tuple[float, float]] = {}
        ordered_tiers = sorted(area_tiers.keys())

        # Layout luôn là top-to-bottom (vertical) theo NS gốc
        current_y = 0.0
        for tier in ordered_tiers:
            area_ids = area_tiers[tier]
            rows = pack_rows(area_ids, tier)  # Pass tier parameter
            row_heights = [row_height(row) for row in rows]
            row_y = current_y
            for row, height in zip(rows, row_heights):
                current_row_x = 0.0
                for aid in row:
                    positions[aid] = (current_row_x, row_y)
                    current_row_x += area_meta[aid]["computed_width"] + AREA_GAP
                row_y += height + AREA_GAP
            tier_height = sum(row_heights) + AREA_GAP * max(0, len(row_heights) - 1)
            current_y += tier_height + AREA_GAP

        return positions

    area_meta = {
        a.id: {
            "width": a.width if a.width and a.width > 0 else AREA_MIN_WIDTH,
            "height": a.height if a.height and a.height > 0 else AREA_MIN_HEIGHT,
            "grid_row": a.grid_row or 1,
            "grid_col": a.grid_col or 1,
            "x": a.position_x,
            "y": a.position_y,
            "name": a.name,
            "extra_padding": 0.0,
        }
        for a in areas
    }

    devices_by_area: dict[str, list] = {}
    device_area_map: dict[str, str] = {}
    for device in devices:
        if not device.area_id:
            continue
        devices_by_area.setdefault(device.area_id, []).append(device)
        device_area_map[device.id] = device.area_id

    # Area connectivity graph (used for ordering and sizing)
    area_link_weights: dict[str, dict[str, int]] = {aid: {} for aid in area_meta}
    area_external_links: dict[str, int] = {aid: 0 for aid in area_meta}
    for link in links:
        from_area = device_area_map.get(link.from_device_id)
        to_area = device_area_map.get(link.to_device_id)
        if not from_area or not to_area or from_area == to_area:
            continue
        area_link_weights[from_area][to_area] = area_link_weights[from_area].get(to_area, 0) + 1
        area_link_weights[to_area][from_area] = area_link_weights[to_area].get(from_area, 0) + 1
        area_external_links[from_area] += 1
        area_external_links[to_area] += 1

    # Micro layout config (top-to-bottom per AI Context)
    micro_config = LayoutConfig(
        layer_gap=config.layer_gap,
        node_spacing=config.node_spacing,
    )

    micro_results: dict[str, dict] = {}
    for area_id, meta in area_meta.items():
        area_devices = devices_by_area.get(area_id, [])
        if not area_devices:
            if layout_scope == "project":
                meta["computed_width"] = AREA_MIN_WIDTH
                meta["computed_height"] = AREA_MIN_HEIGHT
            else:
                meta["computed_width"] = meta["width"]
                meta["computed_height"] = meta["height"]
            continue

        device_ids = {d.id for d in area_devices}
        area_links = [
            l for l in links
            if l.from_device_id in device_ids and l.to_device_id in device_ids
        ]

        layout_result = simple_layer_layout(area_devices, area_links, micro_config)

        if layout_result.devices:
            min_x = min(d["x"] for d in layout_result.devices)
            min_y = min(d["y"] for d in layout_result.devices)
            max_x = max(d["x"] for d in layout_result.devices) + micro_config.node_width
            max_y = max(d["y"] for d in layout_result.devices) + micro_config.node_height
        else:
            min_x = min_y = 0.0
            max_x = micro_config.node_width
            max_y = micro_config.node_height

        external_links = area_external_links.get(area_id, 0)
        device_count = len(area_devices)
        link_padding = min(0.04 * external_links, 0.4)
        density_padding = min(0.015 * max(device_count - 6, 0), 0.2)
        extra_padding = min(link_padding + density_padding, 0.5)
        meta["extra_padding"] = extra_padding

        padding = AREA_PADDING + extra_padding
        required_width = (max_x - min_x) + padding * 2
        required_height = (max_y - min_y) + padding * 2 + LABEL_BAND

        if layout_scope == "project":
            meta["computed_width"] = max(required_width, AREA_MIN_WIDTH)
            meta["computed_height"] = max(required_height, AREA_MIN_HEIGHT)
        else:
            meta["computed_width"] = max(meta["width"], required_width, AREA_MIN_WIDTH)
            meta["computed_height"] = max(meta["height"], required_height, AREA_MIN_HEIGHT)

        micro_results[area_id] = {
            "layout": layout_result,
            "min_x": min_x,
            "min_y": min_y,
        }

    area_tiers: dict[int, list[str]] = {}
    for area_id, meta in area_meta.items():
        area_hint = detect_area_tier(meta["name"])
        device_tiers = [detect_device_tier(d) for d in devices_by_area.get(area_id, [])]
        device_hint = min(device_tiers) if device_tiers else None

        if area_hint is not None and device_hint is not None:
            tier = min(area_hint, device_hint)
        elif area_hint is not None:
            tier = area_hint
        elif device_hint is not None:
            tier = device_hint
        else:
            tier = 7  # Default: office tier (most common)

        area_tiers.setdefault(tier, []).append(area_id)

    def order_areas_by_connectivity(area_ids: list[str], prev_tier_ids: list[str]) -> list[str]:
        if len(area_ids) <= 1:
            return area_ids
        area_set = set(area_ids)
        prev_set = set(prev_tier_ids)

        def weight_to_prev(aid: str) -> int:
            if not prev_set:
                return 0
            return sum(weight for neighbor, weight in area_link_weights.get(aid, {}).items() if neighbor in prev_set)

        def degree_in_set(aid: str) -> int:
            return sum(weight for neighbor, weight in area_link_weights.get(aid, {}).items() if neighbor in area_set)

        def name_key(aid: str) -> str:
            return normalize(area_meta[aid]["name"])

        def sort_key(aid: str) -> tuple[int, int, str]:
            return (-weight_to_prev(aid), -degree_in_set(aid), name_key(aid))

        start = min(area_ids, key=sort_key)
        ordered: list[str] = []
        visited = set()
        queue = [start]
        visited.add(start)

        while queue:
            current = queue.pop(0)
            ordered.append(current)
            neighbors = [
                n for n in area_link_weights.get(current, {})
                if n in area_set and n not in visited
            ]
            neighbors.sort(key=sort_key)
            for neighbor in neighbors:
                visited.add(neighbor)
                queue.append(neighbor)

        remaining = [aid for aid in area_ids if aid not in visited]
        remaining.sort(key=sort_key)
        ordered.extend(remaining)
        return ordered

    ordered_tiers = sorted(area_tiers.keys())
    prev_tier_ids: list[str] = []
    for tier in ordered_tiers:
        area_ids = area_tiers[tier]
        area_tiers[tier] = order_areas_by_connectivity(area_ids, prev_tier_ids)
        prev_tier_ids = area_tiers[tier]

    macro_positions = compute_macro_positions(area_tiers)

    area_positions: dict[str, tuple[float, float]] = {}
    if layout_scope == "project":
        area_positions = macro_positions
    else:
        for area_id, meta in area_meta.items():
            if meta["x"] is not None and meta["y"] is not None:
                area_positions[area_id] = (meta["x"], meta["y"])
            else:
                area_positions[area_id] = macro_positions.get(area_id, (0.0, 0.0))

    device_layouts: list[DeviceLayout] = []
    area_layouts: list[AreaLayout] = []
    stats_layers = []
    stats_crossings = []
    stats_times = []

    if layout_scope == "project":
        for area_id, meta in area_meta.items():
            area_x, area_y = area_positions.get(area_id, (0.0, 0.0))
            area_layouts.append(AreaLayout(
                id=area_id,
                name=meta["name"],
                x=area_x,
                y=area_y,
                width=meta["computed_width"],
                height=meta["computed_height"],
            ))

    for area_id, result in micro_results.items():
        area_x, area_y = area_positions.get(area_id, (0.0, 0.0))
        area_width = area_meta[area_id]["computed_width"]
        area_height = area_meta[area_id]["computed_height"]

        layout_result = result["layout"]
        min_x = result["min_x"]
        min_y = result["min_y"]

        padding = AREA_PADDING + area_meta[area_id].get("extra_padding", 0.0)
        span_x = max(0.0, (area_width - padding * 2) - micro_config.node_width)
        span_y = max(0.0, (area_height - LABEL_BAND - padding * 2) - micro_config.node_height)

        layout_span_x = max(
            micro_config.node_width,
            max((d["x"] - min_x) for d in layout_result.devices) + micro_config.node_width
        )
        layout_span_y = max(
            micro_config.node_height,
            max((d["y"] - min_y) for d in layout_result.devices) + micro_config.node_height
        )

        scale_x = 1.0
        if layout_span_x > micro_config.node_width and span_x > 0:
            scale_x = min(1.0, span_x / (layout_span_x - micro_config.node_width))
        scale_y = 1.0
        if layout_span_y > micro_config.node_height and span_y > 0:
            scale_y = min(1.0, span_y / (layout_span_y - micro_config.node_height))
        scale = min(scale_x, scale_y, 1.0)

        for d in layout_result.devices:
            device_layouts.append(DeviceLayout(
                id=d["id"],
                area_id=area_id,
                x=area_x + padding + (d["x"] - min_x) * scale,
                y=area_y + LABEL_BAND + padding + (d["y"] - min_y) * scale,
                layer=d["layer"],
            ))

        stats_layers.append(layout_result.stats["total_layers"])
        stats_crossings.append(layout_result.stats["total_crossings"])
        stats_times.append(layout_result.stats["execution_time_ms"])

    # Handle devices without area (fallback to global)
    no_area_devices = [d for d in devices if not d.area_id]
    if no_area_devices:
        # Get links for no-area devices
        no_area_device_ids = {d.id for d in no_area_devices}
        no_area_links = [
            l for l in links
            if l.from_device_id in no_area_device_ids and l.to_device_id in no_area_device_ids
        ]
        layout_result = simple_layer_layout(no_area_devices, no_area_links, config)
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
        algorithm="simple_layer_grouped",
    )

    return {
        "devices": device_layouts,
        "areas": area_layouts if area_layouts else None,
        "stats": stats,
    }


def compute_layout_l2(
    devices: list,
    links: list,
    l2_assignments: list,
    l2_segments: list,
    config: LayoutConfig,
) -> dict:
    """Compute L2 layout: VLAN grouping boxes (NS-like L2 view)."""
    GROUP_MIN_WIDTH = 3.0
    GROUP_MIN_HEIGHT = 1.5
    GROUP_GAP = 0.5
    GROUP_PADDING = 0.15
    LABEL_BAND = 0.35

    # Create VLAN mapping
    vlan_map = {seg.id: {"vlan_id": seg.vlan_id, "name": seg.name} for seg in l2_segments}

    # Group devices by VLAN ID (from L2 assignments)
    vlan_devices: dict[int, set[str]] = {}
    for assignment in l2_assignments:
        segment = vlan_map.get(assignment.l2_segment_id)
        if not segment:
            continue
        vlan_id = segment["vlan_id"]
        vlan_devices.setdefault(vlan_id, set()).add(assignment.device_id)

    # Convert sets to lists
    vlan_device_lists = {vlan_id: list(dev_set) for vlan_id, dev_set in vlan_devices.items()}

    # Layout devices within each VLAN group
    vlan_group_layouts: list[dict] = []
    device_layouts: list[DeviceLayout] = []
    stats_layers = []
    stats_crossings = []
    stats_times = []

    for vlan_id, device_ids in vlan_device_lists.items():
        if not device_ids:
            continue

        # Get devices for this VLAN
        group_devices = [d for d in devices if d.id in device_ids]
        if not group_devices:
            continue

        # Get links within this VLAN
        device_id_set = set(device_ids)
        group_links = [
            l for l in links
            if l.from_device_id in device_id_set and l.to_device_id in device_id_set
        ]

        # Layout devices using simple layer layout (NS gốc style)
        layout_result = simple_layer_layout(group_devices, group_links, config)

        # Compute bounding box
        if layout_result.devices:
            min_x = min(d["x"] for d in layout_result.devices)
            min_y = min(d["y"] for d in layout_result.devices)
            max_x = max(d["x"] for d in layout_result.devices) + config.node_width
            max_y = max(d["y"] for d in layout_result.devices) + config.node_height
        else:
            min_x = min_y = 0.0
            max_x = config.node_width
            max_y = config.node_height

        group_width = max(GROUP_MIN_WIDTH, (max_x - min_x) + GROUP_PADDING * 2)
        group_height = max(GROUP_MIN_HEIGHT, (max_y - min_y) + GROUP_PADDING * 2 + LABEL_BAND)

        # Find VLAN name
        vlan_name = next(
            (seg["name"] for seg in vlan_map.values() if seg["vlan_id"] == vlan_id),
            f"VLAN {vlan_id}"
        )

        vlan_group_layouts.append({
            "vlan_id": vlan_id,
            "name": vlan_name,
            "width": group_width,
            "height": group_height,
            "device_ids": device_ids,
            "layout": layout_result,
            "min_x": min_x,
            "min_y": min_y,
        })

        stats_layers.append(layout_result.stats["total_layers"])
        stats_crossings.append(layout_result.stats["total_crossings"])
        stats_times.append(layout_result.stats["execution_time_ms"])

    # Pack VLAN groups (simple grid packing)
    vlan_group_layouts.sort(key=lambda g: g["vlan_id"])

    max_row_width = 15.0  # Wider for VLAN groups
    current_x = 0.0
    current_y = 0.0
    current_row_height = 0.0

    vlan_group_results: list[VlanGroupLayout] = []

    for group in vlan_group_layouts:
        group_width = group["width"]
        group_height = group["height"]

        # Check if need new row
        if current_x > 0 and current_x + GROUP_GAP + group_width > max_row_width:
            # New row
            current_y += current_row_height + GROUP_GAP
            current_x = 0.0
            current_row_height = 0.0

        group_x = current_x
        group_y = current_y

        # Place devices within this group
        for d in group["layout"].devices:
            device_layouts.append(DeviceLayout(
                id=d["id"],
                area_id=None,
                x=group_x + GROUP_PADDING + (d["x"] - group["min_x"]),
                y=group_y + LABEL_BAND + GROUP_PADDING + (d["y"] - group["min_y"]),
                layer=d["layer"],
            ))

        # Record VLAN group position
        vlan_group_results.append(VlanGroupLayout(
            vlan_id=group["vlan_id"],
            name=group["name"],
            x=group_x,
            y=group_y,
            width=group_width,
            height=group_height,
            device_ids=group["device_ids"],
        ))

        # Advance position
        current_x += group_width + GROUP_GAP
        current_row_height = max(current_row_height, group_height)

    stats = LayoutStats(
        total_layers=max(stats_layers) if stats_layers else 0,
        total_crossings=sum(stats_crossings) if stats_crossings else 0,
        execution_time_ms=sum(stats_times) if stats_times else 0,
        algorithm="simple_layer_vlan_grouped",
    )

    return {
        "devices": device_layouts,
        "vlan_groups": vlan_group_results,
        "stats": stats,
    }


def compute_layout_l3(
    devices: list,
    links: list,
    l3_addresses: list,
    config: LayoutConfig,
) -> dict:
    """Compute L3 layout: routers on top, subnet groups below (NS-like L3 view)."""
    import ipaddress

    GROUP_MIN_WIDTH = 3.0
    GROUP_MIN_HEIGHT = 1.5
    GROUP_GAP = 0.5
    GROUP_PADDING = 0.15
    LABEL_BAND = 0.35
    ROUTER_GAP = 1.0

    # Map device_id -> subnets
    device_subnets: dict[str, set[str]] = {}
    subnet_devices: dict[str, set[str]] = {}

    for addr in l3_addresses:
        try:
            # Compute subnet base
            ip = ipaddress.ip_interface(f"{addr.ip_address}/{addr.prefix_length}")
            subnet_str = str(ip.network)

            device_subnets.setdefault(addr.device_id, set()).add(subnet_str)
            subnet_devices.setdefault(subnet_str, set()).add(addr.device_id)
        except Exception:
            # Skip invalid IPs
            continue

    # Identify routers (devices with multiple subnets)
    router_ids = [dev_id for dev_id, subnets in device_subnets.items() if len(subnets) > 1]
    endpoint_ids = [dev_id for dev_id, subnets in device_subnets.items() if len(subnets) == 1]

    # Get router devices
    routers = [d for d in devices if d.id in router_ids]

    # Layout routers horizontally at the top
    router_x = 0.0
    router_y = 0.0
    router_layouts: list[DeviceLayout] = []

    for router in routers:
        router_layouts.append(DeviceLayout(
            id=router.id,
            area_id=None,
            x=router_x,
            y=router_y,
            layer=0,
        ))
        router_x += config.node_width + ROUTER_GAP

    # Group endpoints by subnet (exclude routers from subnet groups)
    subnet_groups_data: list[dict] = []
    device_layouts: list[DeviceLayout] = []
    stats_layers = []
    stats_crossings = []
    stats_times = []

    for subnet, dev_ids in subnet_devices.items():
        # Filter out routers (they're in top row)
        group_device_ids = [dev_id for dev_id in dev_ids if dev_id in endpoint_ids]
        if not group_device_ids:
            continue

        group_devices = [d for d in devices if d.id in group_device_ids]
        if not group_devices:
            continue

        # Get links within this subnet
        device_id_set = set(group_device_ids)
        group_links = [
            l for l in links
            if l.from_device_id in device_id_set and l.to_device_id in device_id_set
        ]

        # Layout devices using simple layer layout (NS gốc style)
        layout_result = simple_layer_layout(group_devices, group_links, config)

        # Compute bounding box
        if layout_result.devices:
            min_x = min(d["x"] for d in layout_result.devices)
            min_y = min(d["y"] for d in layout_result.devices)
            max_x = max(d["x"] for d in layout_result.devices) + config.node_width
            max_y = max(d["y"] for d in layout_result.devices) + config.node_height
        else:
            min_x = min_y = 0.0
            max_x = config.node_width
            max_y = config.node_height

        group_width = max(GROUP_MIN_WIDTH, (max_x - min_x) + GROUP_PADDING * 2)
        group_height = max(GROUP_MIN_HEIGHT, (max_y - min_y) + GROUP_PADDING * 2 + LABEL_BAND)

        # Find router for this subnet (first router with this subnet)
        router_id = None
        for rid in router_ids:
            if subnet in device_subnets.get(rid, set()):
                router_id = rid
                break

        subnet_groups_data.append({
            "subnet": subnet,
            "name": subnet,
            "width": group_width,
            "height": group_height,
            "device_ids": group_device_ids,
            "router_id": router_id,
            "layout": layout_result,
            "min_x": min_x,
            "min_y": min_y,
        })

        stats_layers.append(layout_result.stats["total_layers"])
        stats_crossings.append(layout_result.stats["total_crossings"])
        stats_times.append(layout_result.stats["execution_time_ms"])

    # Pack subnet groups below routers
    subnet_groups_data.sort(key=lambda g: g["subnet"])

    # Start below routers
    router_row_height = config.node_height if routers else 0.0
    max_row_width = 15.0
    current_x = 0.0
    current_y = router_row_height + (GROUP_GAP * 2 if routers else 0.0)
    current_row_height = 0.0

    subnet_group_results: list[SubnetGroupLayout] = []

    for group in subnet_groups_data:
        group_width = group["width"]
        group_height = group["height"]

        # Check if need new row
        if current_x > 0 and current_x + GROUP_GAP + group_width > max_row_width:
            # New row
            current_y += current_row_height + GROUP_GAP
            current_x = 0.0
            current_row_height = 0.0

        group_x = current_x
        group_y = current_y

        # Place devices within this group
        for d in group["layout"].devices:
            device_layouts.append(DeviceLayout(
                id=d["id"],
                area_id=None,
                x=group_x + GROUP_PADDING + (d["x"] - group["min_x"]),
                y=group_y + LABEL_BAND + GROUP_PADDING + (d["y"] - group["min_y"]),
                layer=d["layer"],
            ))

        # Record subnet group position
        subnet_group_results.append(SubnetGroupLayout(
            subnet=group["subnet"],
            name=group["name"],
            x=group_x,
            y=group_y,
            width=group_width,
            height=group_height,
            device_ids=group["device_ids"],
            router_id=group["router_id"],
        ))

        # Advance position
        current_x += group_width + GROUP_GAP
        current_row_height = max(current_row_height, group_height)

    # Combine router layouts and device layouts
    all_device_layouts = router_layouts + device_layouts

    stats = LayoutStats(
        total_layers=max(stats_layers) if stats_layers else 0,
        total_crossings=sum(stats_crossings) if stats_crossings else 0,
        execution_time_ms=sum(stats_times) if stats_times else 0,
        algorithm="simple_layer_subnet_grouped",
    )

    return {
        "devices": all_device_layouts,
        "subnet_groups": subnet_group_results,
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
