"""
Auto-Layout API endpoint.
"""

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import device as device_service
from app.services import link as link_service
from app.services import area as area_service
from app.services.admin_config import get_admin_config
from app.schemas.area import AreaCreate
from app.services.layout_models import LayoutConfig
from app.services.simple_layer_layout import simple_layer_layout
from app.services.layout_cache import get_cache
from app.services.device_sizing import (
    compute_device_port_counts,
    auto_resize_devices_by_ports,
)
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

AREA_PREFIX_RE = re.compile(r"^([A-Za-z0-9]{2,6})(\s*-\s*)")
SECURITY_AREA_KEYWORDS = ["security", "firewall", "fw", "ids", "ips", "vpn", "soc"]
SERVER_AREA_KEYWORDS = ["server", "servers", "storage", "nas", "san"]
DMZ_AREA_KEYWORDS = ["dmz", "proxy"]
DATACENTER_AREA_KEYWORDS = ["datacenter", "data center", "dc"]

SECURITY_DEVICE_KEYWORDS = ["firewall", "fw", "ids", "ips", "vpn", "security"]
ROUTER_DEVICE_KEYWORDS = ["router", "rtr"]
SERVER_DEVICE_KEYWORDS = ["server", "srv", "app", "web", "db", "backup"]
STORAGE_DEVICE_KEYWORDS = ["storage", "nas", "san"]
MONITOR_DEVICE_KEYWORDS = ["monitor", "monitoring", "noc", "nms"]
SERVER_SWITCH_KEYWORDS = ["server", "srv", "storage", "nas"]
ACCESS_SWITCH_KEYWORDS = ["access", "acc"]
DMZ_DEVICE_KEYWORDS = ["dmz", "waf", "proxy"]

DEPT_AREA_KEYWORDS = ["department", "dept"]
PROJECT_AREA_KEYWORDS = ["project", "proj"]
IT_AREA_KEYWORDS = ["it"]
HO_AREA_KEYWORDS = ["head office", "hq", "office", "headquarter", "headquarters"]

# UI uses 120px per logical unit (inch) when mapping to canvas.
UNIT_PX = 120.0
LABEL_CHAR_WIDTH_PX = 6.0
LABEL_PADDING_PX = 8.0
LABEL_MIN_WIDTH_PX = 24.0
LABEL_HEIGHT_PX = 16.0
DEFAULT_DEVICE_WIDTH = 1.2
DEFAULT_DEVICE_HEIGHT = 0.5


def _safe_dim(value: float | None, fallback: float) -> float:
    try:
        return float(value) if value is not None else fallback
    except (TypeError, ValueError):
        return fallback


def _compute_max_device_size(devices: list, base_width: float, base_height: float) -> tuple[float, float]:
    max_width = base_width
    max_height = base_height
    for device in devices:
        max_width = max(max_width, _safe_dim(getattr(device, "width", None), base_width))
        max_height = max(max_height, _safe_dim(getattr(device, "height", None), base_height))
    return max_width, max_height


def _effective_node_size(
    devices: list,
    base_width: float,
    base_height: float,
    extra_width: float = 0.0,
    extra_height: float = 0.0,
) -> tuple[float, float]:
    max_width, max_height = _compute_max_device_size(devices, base_width, base_height)
    return max_width + max(0.0, extra_width), max_height + max(0.0, extra_height)


def _normalize(text: str | None) -> str:
    return (text or "").strip().lower()


def _infer_area_prefix(areas: list) -> str:
    counts: dict[str, int] = {}
    for area in areas:
        match = AREA_PREFIX_RE.match(area.name or "")
        if not match:
            continue
        prefix = f"{match.group(1)}{match.group(2)}"
        counts[prefix] = counts.get(prefix, 0) + 1
    if not counts:
        return ""
    return max(counts.items(), key=lambda item: item[1])[0]


def _find_area_by_keywords(areas: list, keywords: list[str]) -> object | None:
    for area in areas:
        label = _normalize(area.name)
        if any(keyword in label for keyword in keywords):
            return area
    return None


def _find_best_access_area(areas: list, device_name: str) -> object | None:
    name = _normalize(device_name)
    if any(keyword in name for keyword in ["dept", "department"]):
        return _find_area_by_keywords(areas, DEPT_AREA_KEYWORDS)
    if any(keyword in name for keyword in ["project", "proj"]):
        return _find_area_by_keywords(areas, PROJECT_AREA_KEYWORDS)
    if " it" in f" {name} " or name.endswith("it") or name.startswith("it"):
        return _find_area_by_keywords(areas, IT_AREA_KEYWORDS)
    if any(keyword in name for keyword in ["ho", "hq", "head"]):
        return _find_area_by_keywords(areas, HO_AREA_KEYWORDS)
    return None


def _classify_area_kind(name: str | None) -> str | None:
    label = _normalize(name)
    if any(keyword in label for keyword in DATACENTER_AREA_KEYWORDS):
        return "datacenter"
    if any(keyword in label for keyword in SERVER_AREA_KEYWORDS):
        return "server"
    if any(keyword in label for keyword in SECURITY_AREA_KEYWORDS):
        return "security"
    if any(keyword in label for keyword in DMZ_AREA_KEYWORDS):
        return "dmz"
    if any(keyword in label for keyword in ["edge", "wan", "internet", "isp"]):
        return "edge"
    return None


def _is_monitor_device(device) -> bool:
    name = _normalize(getattr(device, "name", ""))
    return any(keyword in name for keyword in MONITOR_DEVICE_KEYWORDS)


def _is_server_device(device) -> bool:
    dtype = _normalize(getattr(device, "device_type", ""))
    name = _normalize(getattr(device, "name", ""))
    if dtype in {"server", "storage"}:
        return True
    if any(keyword in name for keyword in SERVER_DEVICE_KEYWORDS + STORAGE_DEVICE_KEYWORDS):
        return True
    if "sw" in name and any(keyword in name for keyword in SERVER_DEVICE_KEYWORDS + STORAGE_DEVICE_KEYWORDS):
        return True
    return False


def _is_security_device(device) -> bool:
    dtype = _normalize(getattr(device, "device_type", ""))
    name = _normalize(getattr(device, "name", ""))
    if "waf" in name:
        return False
    if dtype == "firewall":
        return True
    return any(keyword in name for keyword in SECURITY_DEVICE_KEYWORDS)


def _is_dmz_device(device) -> bool:
    name = _normalize(getattr(device, "name", ""))
    return any(keyword in name for keyword in DMZ_DEVICE_KEYWORDS)


def _is_router_device(device) -> bool:
    dtype = _normalize(getattr(device, "device_type", ""))
    name = _normalize(getattr(device, "name", ""))
    if dtype == "router":
        return True
    return any(keyword in name for keyword in ROUTER_DEVICE_KEYWORDS)


def _is_access_switch(device) -> bool:
    dtype = _normalize(getattr(device, "device_type", ""))
    name = _normalize(getattr(device, "name", ""))
    if dtype == "switch" and any(keyword in name for keyword in ACCESS_SWITCH_KEYWORDS):
        return True
    return False


def _is_distribution_switch(device) -> bool:
    dtype = _normalize(getattr(device, "device_type", ""))
    name = _normalize(getattr(device, "name", ""))
    if dtype != "switch":
        return False
    if "dist" in name or "distribution" in name:
        return True
    if "core" in name:
        return True
    if any(keyword in name for keyword in SERVER_SWITCH_KEYWORDS):
        return True
    return False


async def _ensure_area(
    db: AsyncSession,
    project_id: str,
    areas: list,
    name: str,
    next_row: int,
) -> tuple[object, int]:
    existing = next((area for area in areas if _normalize(area.name) == _normalize(name)), None)
    if existing:
        return existing, next_row
    area = await area_service.create_area(
        db,
        project_id,
        AreaCreate(name=name, grid_row=next_row, grid_col=1),
    )
    areas.append(area)
    return area, next_row + 1


async def _normalize_topology(
    db: AsyncSession,
    project_id: str,
    areas: list,
    devices: list,
    links: list,
) -> tuple[list, list]:
    if not areas or not devices:
        return areas, devices

    prefix = _infer_area_prefix(areas)
    datacenter_area = _find_area_by_keywords(areas, DATACENTER_AREA_KEYWORDS)
    server_area = _find_area_by_keywords(areas, SERVER_AREA_KEYWORDS)
    it_area = _find_area_by_keywords(areas, IT_AREA_KEYWORDS)

    next_row = max((area.grid_row for area in areas), default=1) + 1

    if not datacenter_area:
        has_infra = any(
            _is_security_device(device) or _is_router_device(device) or _is_distribution_switch(device)
            for device in devices
        )
        if has_infra:
            datacenter_area, next_row = await _ensure_area(
                db,
                project_id,
                areas,
                f"{prefix}Data Center" if prefix else "Data Center",
                next_row,
            )
    if not server_area:
        server_area, next_row = await _ensure_area(
            db,
            project_id,
            areas,
            f"{prefix}Servers" if prefix else "Servers",
            next_row,
        )
    if not it_area:
        it_area, next_row = await _ensure_area(
            db,
            project_id,
            areas,
            f"{prefix}IT" if prefix else "IT",
            next_row,
        )

    area_by_id = {area.id: area for area in areas}
    device_by_id = {device.id: device for device in devices}
    device_area_id = {device.id: device.area_id for device in devices}
    area_kind_by_id = {
        area_id: _classify_area_kind(area.name) for area_id, area in area_by_id.items()
    }
    neighbor_area_index: dict[str, dict[str, int]] = {}
    for link in links:
        from_id = getattr(link, "from_device_id", None)
        to_id = getattr(link, "to_device_id", None)
        if not from_id or not to_id:
            continue
        from_area = device_area_id.get(from_id)
        to_area = device_area_id.get(to_id)
        if not from_area or not to_area:
            continue
        neighbor_area_index.setdefault(from_id, {})
        neighbor_area_index.setdefault(to_id, {})
        neighbor_area_index[from_id][to_area] = neighbor_area_index[from_id].get(to_area, 0) + 1
        neighbor_area_index[to_id][from_area] = neighbor_area_index[to_id].get(from_area, 0) + 1
    updated = False

    for device in devices:
        current_area = area_by_id.get(device.area_id)
        area_kind = _classify_area_kind(current_area.name if current_area else None)
        target_area = None

        if _is_monitor_device(device):
            target_area = it_area
        elif _is_server_device(device):
            target_area = server_area
        elif _is_access_switch(device):
            target_area = _find_best_access_area(areas, device.name)
            if not target_area:
                neighbors = neighbor_area_index.get(device.id, {})
                if neighbors:
                    sorted_neighbors = sorted(
                        neighbors.items(),
                        key=lambda item: item[1],
                        reverse=True,
                    )
                    for area_id, _count in sorted_neighbors:
                        kind = area_kind_by_id.get(area_id)
                        if kind not in {"datacenter", "server"}:
                            target_area = area_by_id.get(area_id)
                            break
        elif datacenter_area and (
            _is_security_device(device)
            or _is_router_device(device)
            or _is_distribution_switch(device)
            or _is_dmz_device(device)
            or "core" in _normalize(getattr(device, "name", ""))
        ):
            target_area = datacenter_area
        elif datacenter_area and area_kind == "datacenter":
            target_area = None

        if target_area and device.area_id != target_area.id:
            device.area_id = target_area.id
            updated = True

    if updated:
        await db.commit()

    # Remove empty areas (no devices) after normalization
    area_ids_in_use = {device.area_id for device in devices}
    removed = False
    for area in list(area_by_id.values()):
        if area.id not in area_ids_in_use:
            await db.delete(area)
            removed = True
    if removed:
        await db.commit()

    areas = await area_service.get_areas(db, project_id)
    devices = await device_service.get_devices(db, project_id)
    return areas, devices


def _collect_device_ports(links: list, l2_assignments: list | None = None) -> dict[str, set[str]]:
    ports: dict[str, set[str]] = {}

    def add(device_id: str | None, port: str | None) -> None:
        if not device_id or not port:
            return
        cleaned = port.strip()
        if not cleaned:
            return
        ports.setdefault(device_id, set()).add(cleaned)

    for link in links:
        add(getattr(link, "from_device_id", None), getattr(link, "from_port", None))
        add(getattr(link, "to_device_id", None), getattr(link, "to_port", None))

    if l2_assignments:
        for assignment in l2_assignments:
            add(getattr(assignment, "device_id", None), getattr(assignment, "interface_name", None))

    return ports


def _estimate_label_clearance(ports_by_device: dict[str, set[str]], render_tuning: dict | None) -> tuple[float, float]:
    if not ports_by_device:
        return 0.0, 0.0

    max_len = 0
    for ports in ports_by_device.values():
        for port in ports:
            max_len = max(max_len, len(port))

    if max_len <= 0:
        return 0.0, 0.0

    tuning = render_tuning or {}
    label_gap_x = float(tuning.get("label_gap_x", 8))
    label_gap_y = float(tuning.get("label_gap_y", 6))
    label_offset = float(tuning.get("port_label_offset", 12))

    label_width_px = max(max_len * LABEL_CHAR_WIDTH_PX + LABEL_PADDING_PX, LABEL_MIN_WIDTH_PX)
    label_width_px += label_gap_x + label_offset
    label_height_px = LABEL_HEIGHT_PX + label_gap_y + label_offset

    return label_width_px / UNIT_PX, label_height_px / UNIT_PX


def _rect_bounds(layout: AreaLayout) -> tuple[float, float, float, float]:
    left = layout.x
    top = layout.y
    right = layout.x + layout.width
    bottom = layout.y + layout.height
    return left, top, right, bottom


def _point_in_rect(px: float, py: float, rect: tuple[float, float, float, float]) -> bool:
    left, top, right, bottom = rect
    return left <= px <= right and top <= py <= bottom


def _compute_waypoint_center(
    la: AreaLayout,
    lb: AreaLayout,
    wp_width: float,
    wp_height: float,
    clearance: float = 0.15,
) -> tuple[float, float]:
    left_a, top_a, right_a, bottom_a = _rect_bounds(la)
    left_b, top_b, right_b, bottom_b = _rect_bounds(lb)

    overlap_x = min(right_a, right_b) - max(left_a, left_b)
    overlap_y = min(bottom_a, bottom_b) - max(top_a, top_b)

    if right_a <= left_b:
        cx = (right_a + left_b) / 2
    elif right_b <= left_a:
        cx = (right_b + left_a) / 2
    else:
        cx = (max(left_a, left_b) + min(right_a, right_b)) / 2

    if bottom_a <= top_b:
        cy = (bottom_a + top_b) / 2
    elif bottom_b <= top_a:
        cy = (bottom_b + top_a) / 2
    else:
        cy = (max(top_a, top_b) + min(bottom_a, bottom_b)) / 2

    acx = (left_a + right_a) / 2
    acy = (top_a + bottom_a) / 2
    bcx = (left_b + right_b) / 2
    bcy = (top_b + bottom_b) / 2
    dx = bcx - acx
    dy = bcy - acy

    if overlap_x > 0 and overlap_y > 0:
        if abs(dx) >= abs(dy):
            if dx >= 0:
                cx = max(right_a, right_b) + wp_width / 2 + clearance
            else:
                cx = min(left_a, left_b) - wp_width / 2 - clearance
            cy = (acy + bcy) / 2
        else:
            if dy >= 0:
                cy = max(bottom_a, bottom_b) + wp_height / 2 + clearance
            else:
                cy = min(top_a, top_b) - wp_height / 2 - clearance
            cx = (acx + bcx) / 2

    if _point_in_rect(cx, cy, (left_a, top_a, right_a, bottom_a)) or _point_in_rect(cx, cy, (left_b, top_b, right_b, bottom_b)):
        if abs(dx) >= abs(dy):
            if dx >= 0:
                cx = max(right_a, right_b) + wp_width / 2 + clearance
            else:
                cx = min(left_a, left_b) - wp_width / 2 - clearance
            cy = (acy + bcy) / 2
        else:
            if dy >= 0:
                cy = max(bottom_a, bottom_b) + wp_height / 2 + clearance
            else:
                cy = min(top_a, top_b) - wp_height / 2 - clearance
            cx = (acx + bcx) / 2

    return cx, cy


async def _create_or_update_waypoint_areas(
    db: AsyncSession,
    project_id: str,
    response: dict,
    areas: list,
    links: list,
    devices: list,
) -> None:
    """Tạo/cập nhật waypoint areas cho inter-area links."""
    import json
    from sqlalchemy import select
    from app.db.models import Area, generate_uuid

    # Build device→area map
    device_area = {d.id: d.area_id for d in devices if d.area_id}
    area_name_map = {a.id: a.name for a in areas}

    # Tìm unique inter-area pairs
    inter_pairs: set[tuple[str, str]] = set()
    for link in links:
        fa = device_area.get(link.from_device_id)
        ta = device_area.get(link.to_device_id)
        if fa and ta and fa != ta:
            pair = tuple(sorted([fa, ta]))
            inter_pairs.add(pair)

    if not inter_pairs:
        return

    # Area layout lookup (từ compute_layout_l1)
    area_layouts = response.get("areas") or []
    area_layout_map = {a.id: a for a in area_layouts}

    # Load existing waypoints (idempotency)
    existing_result = await db.execute(
        select(Area).where(Area.project_id == project_id, Area.name.like("%_wp_"))
    )
    existing_wp = {a.name: a for a in existing_result.scalars().all()}

    wp_style = json.dumps({
        "fill_color_rgb": [245, 245, 245],
        "stroke_color_rgb": [180, 180, 180],
        "stroke_width": 0.5,
    })

    wp_width = 0.6
    wp_height = 0.4

    for aid_a, aid_b in inter_pairs:
        names = sorted([area_name_map.get(aid_a, ""), area_name_map.get(aid_b, "")])
        wp_name = f"{names[0]}_{names[1]}_wp_"

        la = area_layout_map.get(aid_a)
        lb = area_layout_map.get(aid_b)
        if not la or not lb:
            continue

        # Waypoint đặt ở hành lang giữa 2 area (ưu tiên giữa biên)
        center_x, center_y = _compute_waypoint_center(la, lb, wp_width, wp_height)
        mid_x = center_x - wp_width / 2
        mid_y = center_y - wp_height / 2

        if wp_name in existing_wp:
            wp = existing_wp[wp_name]
            wp.position_x = mid_x
            wp.position_y = mid_y
            wp_id = wp.id
        else:
            wp_id = generate_uuid()
            wp = Area(
                id=wp_id,
                project_id=project_id,
                name=wp_name,
                grid_row=99,
                grid_col=99,
                position_x=mid_x,
                position_y=mid_y,
                width=wp_width,
                height=wp_height,
                style_json=wp_style,
            )
            db.add(wp)

        area_layouts.append(AreaLayout(
            id=wp_id, name=wp_name, x=mid_x, y=mid_y, width=wp_width, height=wp_height,
        ))

    await db.flush()


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

    # Auto-resize devices based on port count (if enabled)
    if options.auto_resize_devices and options.apply_to_db:
        port_counts = await compute_device_port_counts(db, project_id)
        await auto_resize_devices_by_ports(db, project_id, port_counts)
        # Reload devices after resize
        devices = await device_service.get_devices(db, project_id)

    admin_config = await get_admin_config(db)
    layout_tuning = admin_config.get("layout_tuning", {}) if isinstance(admin_config, dict) else {}

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
            areas, devices = await _normalize_topology(db, project_id, areas, devices, links)
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

    node_width, node_height = _effective_node_size(
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
                # Lọc bỏ waypoint areas (_wp_) - chúng sẽ được tạo/cập nhật riêng
                non_wp_areas = [a for a in areas if not a.name.endswith("_wp_")]
                response = compute_layout_l1(devices, links, non_wp_areas, config, options.layout_scope, layout_tuning)
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

    # Tạo waypoint areas cho inter-area links (trước cache và apply_to_db)
    if options.apply_to_db and options.group_by_area and view_mode == "L1":
        await _create_or_update_waypoint_areas(
            db, project_id, response, areas, links, devices
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
    AREA_PADDING = 0.35  # Padding around devices in inches

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
    layout_tuning: dict | None = None,
) -> dict:
    """Compute L1 layout: area-based with minimized area visuals (compact spacing)."""
    tuning = layout_tuning or {}
    port_label_band = 0.0
    try:
        port_label_band = float(tuning.get("port_label_band", 0.0))
    except (TypeError, ValueError):
        port_label_band = 0.0
    if port_label_band < 0:
        port_label_band = 0.0
    AREA_MIN_WIDTH = 3.0
    AREA_MIN_HEIGHT = 1.5
    AREA_GAP = float(tuning.get("area_gap", 0.9))
    AREA_PADDING = float(tuning.get("area_padding", 0.3))
    LABEL_BAND = float(tuning.get("label_band", 0.45))
    MAX_ROW_WIDTH_BASE = float(tuning.get("max_row_width_base", 12.0))

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
            (1, ["security", "firewall", "fw", "ids", "ips", "waf", "vpn", "soc"]),
            # Tier 2: DMZ
            (2, ["dmz", "proxy", "datacenter", "data center", "dc"]),
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
            (10, ["server", "servers", "storage", "nas"]),
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
            (1, ["firewall", "fw", "ids", "ips", "waf", "security", "vpn", "soc"]),
            (2, ["dmz", "proxy"]),
            (3, ["core"]),
            (4, ["distribution", "dist"]),
            (5, ["campus"]),
            (6, ["branch"]),
            (7, ["office", "floor"]),
            (8, ["department", "dept"]),
            (9, ["project", "proj"]),
            (10, ["server", "storage", "nas", "san"]),
        ]
        for tier, keywords in tier_keywords:
            if any(keyword in name for keyword in keywords):
                return tier
        if _is_distribution_switch(device):
            return 4
        # Fallback by device_type
        if dtype == "firewall":
            return 1
        if dtype == "vpn":
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

    def order_tiers(area_tiers: dict[int, list[str]]) -> list[int]:
        ordered = sorted(area_tiers.keys())
        if 10 in ordered:
            ordered.remove(10)
            if 2 in ordered:
                insert_at = ordered.index(2) + 1
            elif 1 in ordered:
                insert_at = ordered.index(1) + 1
            else:
                insert_at = 0
            ordered.insert(insert_at, 10)
        return ordered

    def compute_macro_positions(area_tiers: dict[int, list[str]]) -> dict[str, tuple[float, float]]:
        positions: dict[str, tuple[float, float]] = {}
        ordered_tiers = order_tiers(area_tiers)

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
    layer_gap = max(0.0, config.layer_gap + port_label_band)
    node_spacing = max(0.0, config.node_spacing + port_label_band)
    max_nodes_per_row = tuning.get("max_nodes_per_row")
    try:
        max_nodes_per_row = int(max_nodes_per_row) if max_nodes_per_row is not None else None
    except (TypeError, ValueError):
        max_nodes_per_row = None

    row_gap = tuning.get("row_gap")
    try:
        if row_gap is not None:
            row_gap = float(row_gap) + port_label_band
        else:
            row_gap = max(0.2, node_spacing * 0.6)
    except (TypeError, ValueError):
        row_gap = max(0.2, node_spacing * 0.6)
    row_gap = max(0.0, row_gap)

    row_stagger = tuning.get("row_stagger")
    try:
        row_stagger = float(row_stagger) if row_stagger is not None else 0.5
    except (TypeError, ValueError):
        row_stagger = 0.5

    base_node_width = config.node_width
    base_node_height = config.node_height
    label_extra = port_label_band * 2

    micro_config = LayoutConfig(
        layer_gap=layer_gap,
        node_spacing=node_spacing,
        node_width=base_node_width,
        node_height=base_node_height,
        max_nodes_per_row=max_nodes_per_row,
        row_gap=row_gap,
        row_stagger=row_stagger,
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

        area_node_width, area_node_height = _effective_node_size(
            area_devices,
            DEFAULT_DEVICE_WIDTH,
            DEFAULT_DEVICE_HEIGHT,
            extra_width=label_extra,
            extra_height=label_extra,
        )
        area_micro_config = LayoutConfig(
            layer_gap=micro_config.layer_gap,
            node_spacing=micro_config.node_spacing,
            node_width=area_node_width,
            node_height=area_node_height,
            max_nodes_per_row=micro_config.max_nodes_per_row,
            row_gap=micro_config.row_gap,
            row_stagger=micro_config.row_stagger,
        )

        layout_result = simple_layer_layout(area_devices, area_links, area_micro_config)

        if layout_result.devices:
            min_x = min(d["x"] for d in layout_result.devices)
            min_y = min(d["y"] for d in layout_result.devices)
            max_x = max(d["x"] for d in layout_result.devices) + area_micro_config.node_width
            max_y = max(d["y"] for d in layout_result.devices) + area_micro_config.node_height
        else:
            min_x = min_y = 0.0
            max_x = area_micro_config.node_width
            max_y = area_micro_config.node_height

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
            "node_width": area_micro_config.node_width,
            "node_height": area_micro_config.node_height,
        }

    area_tiers: dict[int, list[str]] = {}
    for area_id, meta in area_meta.items():
        area_hint = detect_area_tier(meta["name"])
        device_tiers = [detect_device_tier(d) for d in devices_by_area.get(area_id, [])]
        device_hint = min(device_tiers) if device_tiers else None

        if area_hint is not None and device_hint is not None:
            if area_hint in {1, 2, 10}:
                tier = area_hint
            else:
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

    def build_index_map(area_tiers_map: dict[int, list[str]]) -> dict[str, int]:
        index_map: dict[str, int] = {}
        for tier_ids in area_tiers_map.values():
            for idx, aid in enumerate(tier_ids):
                index_map[aid] = idx
        return index_map

    def area_order_cost(aid: str, index_map: dict[str, int]) -> float:
        cost = 0.0
        for neighbor, weight in area_link_weights.get(aid, {}).items():
            if neighbor not in index_map:
                continue
            cost += weight * abs(index_map[aid] - index_map[neighbor])
        return cost

    REFINE_TIER_PASSES = 3
    LOCAL_SWAP_PASSES = 4

    def refine_tier_by_barycenter(area_ids: list[str], index_map: dict[str, int]) -> list[str]:
        if len(area_ids) <= 1:
            return area_ids

        base_positions = {aid: idx for idx, aid in enumerate(area_ids)}

        def barycenter(aid: str) -> float | None:
            total = 0.0
            weight_sum = 0.0
            for neighbor, weight in area_link_weights.get(aid, {}).items():
                if neighbor not in index_map:
                    continue
                total += index_map[neighbor] * weight
                weight_sum += weight
            if weight_sum == 0:
                return None
            return total / weight_sum

        def sort_key(aid: str) -> tuple[float, int, str]:
            score = barycenter(aid)
            return (
                score if score is not None else base_positions[aid],
                base_positions[aid],
                normalize(area_meta[aid]["name"]),
            )

        ordered = sorted(area_ids, key=sort_key)

        # Local swap refinement to reduce weighted distance
        for _ in range(LOCAL_SWAP_PASSES):
            index_map_local = {aid: idx for idx, aid in enumerate(ordered)}
            swapped = False
            for idx in range(len(ordered) - 1):
                a_id = ordered[idx]
                b_id = ordered[idx + 1]
                cost_before = area_order_cost(a_id, index_map_local) + area_order_cost(b_id, index_map_local)
                index_map_local[a_id], index_map_local[b_id] = index_map_local[b_id], index_map_local[a_id]
                cost_after = area_order_cost(a_id, index_map_local) + area_order_cost(b_id, index_map_local)
                if cost_after + 1e-6 < cost_before:
                    ordered[idx], ordered[idx + 1] = ordered[idx + 1], ordered[idx]
                    swapped = True
                else:
                    index_map_local[a_id], index_map_local[b_id] = index_map_local[b_id], index_map_local[a_id]
            if not swapped:
                break

        return ordered

    ordered_tiers = order_tiers(area_tiers)
    prev_tier_ids: list[str] = []
    for tier in ordered_tiers:
        area_ids = area_tiers[tier]
        area_tiers[tier] = order_areas_by_connectivity(area_ids, prev_tier_ids)
        prev_tier_ids = area_tiers[tier]

    # Refine area order within each tier using barycenter + local swaps
    for _ in range(REFINE_TIER_PASSES):
        index_map = build_index_map(area_tiers)
        for tier in ordered_tiers:
            area_tiers[tier] = refine_tier_by_barycenter(area_tiers[tier], index_map)
            index_map = build_index_map(area_tiers)
        index_map = build_index_map(area_tiers)
        for tier in reversed(ordered_tiers):
            area_tiers[tier] = refine_tier_by_barycenter(area_tiers[tier], index_map)
            index_map = build_index_map(area_tiers)

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
        node_width = float(result.get("node_width", micro_config.node_width))
        node_height = float(result.get("node_height", micro_config.node_height))

        padding = AREA_PADDING + area_meta[area_id].get("extra_padding", 0.0)
        span_x = max(0.0, (area_width - padding * 2) - node_width)
        span_y = max(0.0, (area_height - LABEL_BAND - padding * 2) - node_height)

        layout_span_x = max(
            node_width,
            max((d["x"] - min_x) for d in layout_result.devices) + node_width
        )
        layout_span_y = max(
            node_height,
            max((d["y"] - min_y) for d in layout_result.devices) + node_height
        )

        scale_x = 1.0
        if layout_span_x > node_width and span_x > 0:
            scale_x = min(1.0, span_x / (layout_span_x - node_width))
        scale_y = 1.0
        if layout_span_y > node_height and span_y > 0:
            scale_y = min(1.0, span_y / (layout_span_y - node_height))
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
        no_area_node_width, no_area_node_height = _effective_node_size(
            no_area_devices,
            DEFAULT_DEVICE_WIDTH,
            DEFAULT_DEVICE_HEIGHT,
            extra_width=label_extra,
            extra_height=label_extra,
        )
        no_area_config = LayoutConfig(
            layer_gap=micro_config.layer_gap,
            node_spacing=micro_config.node_spacing,
            node_width=no_area_node_width,
            node_height=no_area_node_height,
            max_nodes_per_row=micro_config.max_nodes_per_row,
            row_gap=micro_config.row_gap,
            row_stagger=micro_config.row_stagger,
        )
        layout_result = simple_layer_layout(no_area_devices, no_area_links, no_area_config)
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
    layout_tuning: dict | None = None,
) -> dict:
    """Compute L2 layout: VLAN grouping boxes (NS-like L2 view)."""
    tuning = layout_tuning or {}
    GROUP_MIN_WIDTH = 3.0
    GROUP_MIN_HEIGHT = 1.5
    GROUP_GAP = 0.5
    GROUP_PADDING = 0.15
    try:
        LABEL_BAND = float(tuning.get("label_band", 0.45))
    except (TypeError, ValueError):
        LABEL_BAND = 0.45
    if LABEL_BAND < 0:
        LABEL_BAND = 0.0

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

        group_node_width, group_node_height = _effective_node_size(
            group_devices,
            DEFAULT_DEVICE_WIDTH,
            DEFAULT_DEVICE_HEIGHT,
            extra_width=0.0,
            extra_height=LABEL_BAND,
        )
        group_config = LayoutConfig(
            layer_gap=config.layer_gap,
            node_spacing=config.node_spacing,
            node_width=group_node_width,
            node_height=group_node_height,
            max_nodes_per_row=config.max_nodes_per_row,
            row_gap=config.row_gap,
            row_stagger=config.row_stagger,
        )

        # Layout devices using simple layer layout (NS gốc style)
        layout_result = simple_layer_layout(group_devices, group_links, group_config)

        # Compute bounding box
        if layout_result.devices:
            min_x = min(d["x"] for d in layout_result.devices)
            min_y = min(d["y"] for d in layout_result.devices)
            max_x = max(d["x"] for d in layout_result.devices) + group_config.node_width
            max_y = max(d["y"] for d in layout_result.devices) + group_config.node_height
        else:
            min_x = min_y = 0.0
            max_x = group_config.node_width
            max_y = group_config.node_height

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
    layout_tuning: dict | None = None,
) -> dict:
    """Compute L3 layout: routers on top, subnet groups below (NS-like L3 view)."""
    import ipaddress

    tuning = layout_tuning or {}
    GROUP_MIN_WIDTH = 3.0
    GROUP_MIN_HEIGHT = 1.5
    GROUP_GAP = 0.5
    GROUP_PADDING = 0.15
    try:
        LABEL_BAND = float(tuning.get("label_band", 0.45))
    except (TypeError, ValueError):
        LABEL_BAND = 0.45
    if LABEL_BAND < 0:
        LABEL_BAND = 0.0
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

    router_node_width, router_node_height = _effective_node_size(
        routers,
        DEFAULT_DEVICE_WIDTH,
        DEFAULT_DEVICE_HEIGHT,
        extra_width=0.0,
        extra_height=LABEL_BAND,
    )

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
        router_x += router_node_width + ROUTER_GAP

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

        group_node_width, group_node_height = _effective_node_size(
            group_devices,
            DEFAULT_DEVICE_WIDTH,
            DEFAULT_DEVICE_HEIGHT,
            extra_width=0.0,
            extra_height=LABEL_BAND,
        )
        group_config = LayoutConfig(
            layer_gap=config.layer_gap,
            node_spacing=config.node_spacing,
            node_width=group_node_width,
            node_height=group_node_height,
            max_nodes_per_row=config.max_nodes_per_row,
            row_gap=config.row_gap,
            row_stagger=config.row_stagger,
        )

        # Layout devices using simple layer layout (NS gốc style)
        layout_result = simple_layer_layout(group_devices, group_links, group_config)

        # Compute bounding box
        if layout_result.devices:
            min_x = min(d["x"] for d in layout_result.devices)
            min_y = min(d["y"] for d in layout_result.devices)
            max_x = max(d["x"] for d in layout_result.devices) + group_config.node_width
            max_y = max(d["y"] for d in layout_result.devices) + group_config.node_height
        else:
            min_x = min_y = 0.0
            max_x = group_config.node_width
            max_y = group_config.node_height

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
    router_row_height = router_node_height if routers else 0.0
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
