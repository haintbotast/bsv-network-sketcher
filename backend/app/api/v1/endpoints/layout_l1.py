"""
L1 layout computation: area-based with tier-aware packing.
"""

import re

from app.services.layout_models import LayoutConfig
from app.services.simple_layer_layout import simple_layer_layout
from app.schemas.layout import DeviceLayout, AreaLayout, LayoutStats

from .layout_constants import DEFAULT_DEVICE_WIDTH, DEFAULT_DEVICE_HEIGHT, normalize_text
from .layout_geometry import (
    effective_node_size,
    collect_device_ports,
    estimate_label_clearance,
    estimate_device_rendered_size,
    safe_dim,
)
from .device_classifier import is_distribution_switch


def compute_layout_l1(
    devices: list,
    links: list,
    areas: list,
    config: LayoutConfig,
    layout_scope: str,
    layout_tuning: dict | None = None,
    render_tuning: dict | None = None,
) -> dict:
    """Compute L1 layout: area-based with minimized area visuals (compact spacing)."""
    tuning = layout_tuning or {}
    render_cfg = render_tuning or {}
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
    ADAPTIVE_AREA_GAP_FACTOR = max(0.0, float(tuning.get("adaptive_area_gap_factor", 0.06)))
    ADAPTIVE_AREA_GAP_CAP = max(0.0, float(tuning.get("adaptive_area_gap_cap", 0.8)))
    INTER_AREA_GAP_PER_LINK = max(0.0, float(tuning.get("inter_area_gap_per_link", 0.04)))
    INTER_AREA_GAP_CAP = max(0.0, float(tuning.get("inter_area_gap_cap", 0.35)))
    macro_area_gap = AREA_GAP

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
        floor_marker_re = re.compile(r"(?:^|[^a-z0-9])(?:b?\d{1,2}\s*f)(?:$|[^a-z0-9])")
        tier_hints = [
            (0, ["router", "rtr", "edge", "wan", "internet", "isp", "cloud", "office365", "o365", "saas", "external"]),
            (1, ["security", "firewall", "fw", "ids", "ips", "waf", "vpn", "soc"]),
            (2, ["dmz", "proxy", "datacenter", "data center", "dc"]),
            (3, ["core"]),
            (4, ["distribution", "dist"]),
            (5, ["campus", "hq", "headquarters", "main"]),
            (6, ["branch", "site", "remote"]),
            (7, ["office", "floor", "building", "access", "backoffice", "back office"]),
            (8, ["department", "dept"]),
            (9, ["project", "proj", "it"]),
            (10, ["server", "servers", "storage", "nas"]),
        ]
        for tier, keywords in tier_hints:
            if any(keyword in label for keyword in keywords):
                return tier
        if floor_marker_re.search(label):
            return 7
        return None

    core_token_re = re.compile(r"(?:^|[^a-z0-9])cr\d*(?:$|[^a-z0-9])")
    dist_token_re = re.compile(r"(?:^|[^a-z0-9])ds\d*(?:$|[^a-z0-9])")
    server_sw_token_re = re.compile(r"(?:^|[^a-z0-9])sv\d*(?:$|[^a-z0-9])")

    def detect_device_tier(device) -> int:
        """Detect device tier with enhanced granularity (0-10)."""
        name = normalize(getattr(device, "name", ""))
        dtype = normalize(getattr(device, "device_type", ""))
        if dtype in {"cloud", "cloud-network", "cloud-security", "cloud-service"}:
            return 0
        if dtype == "switch":
            if core_token_re.search(name):
                return 3
            if dist_token_re.search(name):
                return 4
            if server_sw_token_re.search(name):
                return 4
        tier_keywords = [
            (0, ["router", "rtr", "edge", "wan", "internet", "isp", "cloud", "office365", "o365", "saas", "external"]),
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
        if is_distribution_switch(device):
            return 4
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
            return 7
        if dtype in {"pc", "printer", "camera", "ipphone", "phone", "endpoint"}:
            return 10
        return 7

    def dynamic_area_gap(left_area_id: str | None = None, right_area_id: str | None = None) -> float:
        gap = macro_area_gap
        if left_area_id and right_area_id and left_area_id != right_area_id:
            weight = area_link_weights.get(left_area_id, {}).get(right_area_id, 0)
            gap += min(weight * INTER_AREA_GAP_PER_LINK, INTER_AREA_GAP_CAP)
        return gap

    def compute_max_row_width_per_tier(area_ids: list[str], tier: int) -> float:
        if not area_ids:
            return MAX_ROW_WIDTH_BASE

        tier_config = TIER_CHARACTERISTICS.get(tier, {
            "max_areas_per_row": 3,
            "width_factor": 1.0,
            "priority": "medium"
        })

        widths = [area_meta[aid]["computed_width"] for aid in area_ids]
        widths_sorted = sorted(widths, reverse=True)

        if len(widths_sorted) >= 2:
            min_width_for_two = widths_sorted[0] + widths_sorted[1] + macro_area_gap
        else:
            min_width_for_two = widths_sorted[0] if widths_sorted else AREA_MIN_WIDTH

        base_width = MAX_ROW_WIDTH_BASE * tier_config["width_factor"]

        avg_width = sum(widths) / len(widths)
        target_cols = min(tier_config["max_areas_per_row"], len(area_ids))
        suggested_width = avg_width * target_cols + macro_area_gap * (target_cols - 1)

        return max(base_width, min_width_for_two, suggested_width)

    def pack_rows(area_ids: list[str], tier: int) -> list[list[str]]:
        max_width = compute_max_row_width_per_tier(area_ids, tier)
        rows: list[list[str]] = []
        current: list[str] = []
        current_width = 0.0
        for aid in area_ids:
            width = area_meta[aid]["computed_width"]
            gap = dynamic_area_gap(current[-1], aid) if current else 0.0
            if current and current_width + gap + width > max_width:
                rows.append(current)
                current = [aid]
                current_width = width
            else:
                if current:
                    current_width += gap + width
                else:
                    current_width = width
                current.append(aid)
        if current:
            rows.append(current)
        return rows

    def row_width(row: list[str]) -> float:
        if not row:
            return 0.0
        total = sum(area_meta[aid]["computed_width"] for aid in row)
        if len(row) <= 1:
            return total
        for idx in range(len(row) - 1):
            total += dynamic_area_gap(row[idx], row[idx + 1])
        return total

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
            elif 0 in ordered:
                insert_at = ordered.index(0) + 1
            else:
                insert_at = 0
            ordered.insert(insert_at, 10)
        return ordered

    def compute_macro_positions(area_tiers: dict[int, list[str]]) -> dict[str, tuple[float, float]]:
        positions: dict[str, tuple[float, float]] = {}
        ordered_tiers = order_tiers(area_tiers)

        current_y = 0.0
        for tier in ordered_tiers:
            area_ids = area_tiers[tier]
            rows = pack_rows(area_ids, tier)
            row_heights = [row_height(row) for row in rows]
            row_y = current_y
            for row, height in zip(rows, row_heights):
                current_row_x = 0.0
                for idx, aid in enumerate(row):
                    positions[aid] = (current_row_x, row_y)
                    current_row_x += area_meta[aid]["computed_width"]
                    if idx < len(row) - 1:
                        current_row_x += dynamic_area_gap(aid, row[idx + 1])
                row_y += height + macro_area_gap
            tier_height = sum(row_heights) + macro_area_gap * max(0, len(row_heights) - 1)
            current_y += tier_height + macro_area_gap

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

    inter_area_densities = sorted(v for v in area_external_links.values() if v > 0)
    if inter_area_densities:
        p75_idx = min(len(inter_area_densities) - 1, int(round((len(inter_area_densities) - 1) * 0.75)))
        p75_density = inter_area_densities[p75_idx]
        adaptive_extra = min(p75_density * ADAPTIVE_AREA_GAP_FACTOR, ADAPTIVE_AREA_GAP_CAP)
        macro_area_gap = AREA_GAP + adaptive_extra

    # Micro layout config
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
        area_port_links = [
            l for l in links
            if l.from_device_id in device_ids or l.to_device_id in device_ids
        ]

        ports_by_device = collect_device_ports(area_port_links)

        # Compute max rendered size accounting for frontend port band expansion
        max_rendered_w = DEFAULT_DEVICE_WIDTH
        max_rendered_h = DEFAULT_DEVICE_HEIGHT
        for device in area_devices:
            body_w = safe_dim(getattr(device, "width", None), DEFAULT_DEVICE_WIDTH)
            body_h = safe_dim(getattr(device, "height", None), DEFAULT_DEVICE_HEIGHT)
            device_ports = sorted(ports_by_device.get(device.id, set()))
            r_w, r_h = estimate_device_rendered_size(body_w, body_h, device_ports)
            max_rendered_w = max(max_rendered_w, r_w)
            max_rendered_h = max(max_rendered_h, r_h)
        area_node_width = max_rendered_w + max(0.0, label_extra)
        area_node_height = max_rendered_h + max(0.0, label_extra)
        # Keep a minimum spacing proportional to rendered node size to avoid overlap after port-band expansion.
        min_node_spacing = max(0.45, area_node_width * 0.16)
        # Keep rows farther apart for dense link bundles between adjacent layers.
        min_row_gap = max(0.75, area_node_height * 0.24)
        # Port labels render as band cells inside device — no extra label clearance needed.
        area_micro_config = LayoutConfig(
            layer_gap=max(micro_config.layer_gap, area_node_height * 0.28),
            node_spacing=max(micro_config.node_spacing, min_node_spacing),
            node_width=area_node_width,
            node_height=area_node_height,
            max_nodes_per_row=micro_config.max_nodes_per_row,
            row_gap=max(micro_config.row_gap, min_row_gap),
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

    def should_use_grid_macro_positions() -> bool:
        if layout_scope != "project":
            return False
        if len(area_meta) < 2:
            return False
        row_values = sorted({int(meta["grid_row"]) for meta in area_meta.values() if meta.get("grid_row") is not None})
        col_values = sorted({int(meta["grid_col"]) for meta in area_meta.values() if meta.get("grid_col") is not None})
        if len(row_values) < 2 or len(col_values) < 2:
            return False
        row_span = row_values[-1] - row_values[0]
        col_span = col_values[-1] - col_values[0]
        # Chỉ bật grid macro khi placement map có phân bố đủ rõ ràng.
        return row_span >= 1 and col_span >= 1

    def percentile(values: list[float], q: float) -> float:
        """Compute linear-interpolated percentile for stable slot sizing."""
        if not values:
            return 0.0
        ordered = sorted(values)
        if len(ordered) == 1:
            return ordered[0]
        q = max(0.0, min(1.0, q))
        position = (len(ordered) - 1) * q
        low = int(position)
        high = min(low + 1, len(ordered) - 1)
        if low == high:
            return ordered[low]
        ratio = position - low
        return ordered[low] * (1.0 - ratio) + ordered[high] * ratio

    def compute_macro_positions_from_grid() -> dict[str, tuple[float, float]]:
        positions: dict[str, tuple[float, float]] = {}
        row_values = sorted({int(meta["grid_row"]) for meta in area_meta.values()})
        col_values = sorted({int(meta["grid_col"]) for meta in area_meta.values()})

        if not row_values or not col_values:
            return positions

        col_slot_widths: dict[int, float] = {}
        for col in col_values:
            ids = [aid for aid, meta in area_meta.items() if int(meta["grid_col"]) == col]
            if not ids:
                col_slot_widths[col] = AREA_MIN_WIDTH
            else:
                widths = [area_meta[aid]["computed_width"] for aid in ids]
                # Use median slot width to avoid one dense area pulling the whole column too far away.
                col_slot_widths[col] = max(AREA_MIN_WIDTH, percentile(widths, 0.5))

        row_heights: dict[int, float] = {}
        for row in row_values:
            ids = [aid for aid, meta in area_meta.items() if int(meta["grid_row"]) == row]
            if not ids:
                row_heights[row] = AREA_MIN_HEIGHT
            else:
                row_heights[row] = max(area_meta[aid]["computed_height"] for aid in ids)

        col_centers: dict[int, float] = {}
        cursor_x = 0.0
        for col in col_values:
            slot_width = col_slot_widths[col]
            col_centers[col] = cursor_x + (slot_width / 2.0)
            cursor_x += slot_width + macro_area_gap

        row_offsets: dict[int, float] = {}
        cursor_y = 0.0
        for row in row_values:
            row_offsets[row] = cursor_y
            cursor_y += row_heights[row] + macro_area_gap

        occupied_cell_counts: dict[tuple[int, int], int] = {}
        area_ids_sorted = sorted(
            area_meta.keys(),
            key=lambda aid: (
                int(area_meta[aid]["grid_row"]),
                int(area_meta[aid]["grid_col"]),
                normalize(area_meta[aid]["name"]),
            ),
        )

        for aid in area_ids_sorted:
            row = int(area_meta[aid]["grid_row"])
            col = int(area_meta[aid]["grid_col"])
            cell = (row, col)
            index_in_cell = occupied_cell_counts.get(cell, 0)
            occupied_cell_counts[cell] = index_in_cell + 1

            area_w = area_meta[aid]["computed_width"]
            area_h = area_meta[aid]["computed_height"]

            # Center each area around its grid column center.
            x = col_centers[col] - (area_w / 2.0)
            if index_in_cell > 0:
                # Cell trùng nhau: dàn nhẹ theo đường chéo để tránh chồng lấn tuyệt đối.
                x += index_in_cell * macro_area_gap * 0.35
            # Căn giữa dọc trong row nếu area thấp hơn row height.
            y_offset = (row_heights[row] - area_h) / 2 if area_h < row_heights[row] else 0
            y = row_offsets[row] + y_offset
            if index_in_cell > 0:
                y += index_in_cell * macro_area_gap * 0.35
            positions[aid] = (x, y)

        # Final pass: prevent overlap between neighboring columns in the same row.
        row_area_ids: dict[int, list[str]] = {}
        for aid in positions:
            row = int(area_meta[aid]["grid_row"])
            row_area_ids.setdefault(row, []).append(aid)

        for row, ids in row_area_ids.items():
            ids_sorted = sorted(ids, key=lambda aid: positions[aid][0])
            min_gap = macro_area_gap * 0.2
            prev_right = None
            for aid in ids_sorted:
                x, y = positions[aid]
                width = area_meta[aid]["computed_width"]
                if prev_right is not None and x < prev_right + min_gap:
                    x = prev_right + min_gap
                    positions[aid] = (x, y)
                prev_right = positions[aid][0] + width

        return positions

    area_tiers: dict[int, list[str]] = {}
    for area_id, meta in area_meta.items():
        area_hint = detect_area_tier(meta["name"])
        device_tiers = [detect_device_tier(d) for d in devices_by_area.get(area_id, [])]
        device_hint = min(device_tiers) if device_tiers else None

        if area_hint is not None and device_hint is not None:
            # Router (tier 0) always takes highest priority
            if device_hint == 0:
                tier = 0
            elif area_hint in {1, 2, 10}:
                tier = area_hint
            elif area_hint >= 5:
                # Với area nghiệp vụ (campus/branch/office/dept/project):
                # giữ tier theo area để access switch không kéo area lên quá cao.
                tier = area_hint
            else:
                tier = min(area_hint, device_hint)
        elif area_hint is not None:
            tier = area_hint
        elif device_hint is not None:
            tier = device_hint
        else:
            tier = 7

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

    for _ in range(REFINE_TIER_PASSES):
        index_map = build_index_map(area_tiers)
        for tier in ordered_tiers:
            area_tiers[tier] = refine_tier_by_barycenter(area_tiers[tier], index_map)
            index_map = build_index_map(area_tiers)
        index_map = build_index_map(area_tiers)
        for tier in reversed(ordered_tiers):
            area_tiers[tier] = refine_tier_by_barycenter(area_tiers[tier], index_map)
            index_map = build_index_map(area_tiers)

    use_grid_macro = should_use_grid_macro_positions()
    if use_grid_macro:
        macro_positions = compute_macro_positions_from_grid()
    else:
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
        no_area_device_ids = {d.id for d in no_area_devices}
        no_area_links = [
            l for l in links
            if l.from_device_id in no_area_device_ids and l.to_device_id in no_area_device_ids
        ]
        no_area_port_links = [
            l for l in links
            if l.from_device_id in no_area_device_ids or l.to_device_id in no_area_device_ids
        ]
        ports_by_device = collect_device_ports(no_area_port_links)
        label_clearance_x, label_clearance_y = estimate_label_clearance(ports_by_device, render_cfg)

        no_area_node_width, no_area_node_height = effective_node_size(
            no_area_devices,
            DEFAULT_DEVICE_WIDTH,
            DEFAULT_DEVICE_HEIGHT,
            extra_width=label_extra,
            extra_height=label_extra,
        )
        no_area_config = LayoutConfig(
            layer_gap=micro_config.layer_gap + label_clearance_y,
            node_spacing=micro_config.node_spacing + label_clearance_x,
            node_width=no_area_node_width,
            node_height=no_area_node_height,
            max_nodes_per_row=micro_config.max_nodes_per_row,
            row_gap=micro_config.row_gap + label_clearance_y,
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
