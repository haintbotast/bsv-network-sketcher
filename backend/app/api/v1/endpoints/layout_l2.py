"""
L2 layout computation: VLAN grouping boxes.
"""

from app.services.layout_models import LayoutConfig
from app.services.simple_layer_layout import simple_layer_layout
from app.schemas.layout import DeviceLayout, VlanGroupLayout, LayoutStats

from .layout_constants import DEFAULT_DEVICE_WIDTH, DEFAULT_DEVICE_HEIGHT
from .layout_geometry import effective_node_size


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

        group_devices = [d for d in devices if d.id in device_ids]
        if not group_devices:
            continue

        device_id_set = set(device_ids)
        group_links = [
            l for l in links
            if l.from_device_id in device_id_set and l.to_device_id in device_id_set
        ]

        group_node_width, group_node_height = effective_node_size(
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

        layout_result = simple_layer_layout(group_devices, group_links, group_config)

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

    max_row_width = 15.0
    current_x = 0.0
    current_y = 0.0
    current_row_height = 0.0

    vlan_group_results: list[VlanGroupLayout] = []

    for group in vlan_group_layouts:
        group_width = group["width"]
        group_height = group["height"]

        if current_x > 0 and current_x + GROUP_GAP + group_width > max_row_width:
            current_y += current_row_height + GROUP_GAP
            current_x = 0.0
            current_row_height = 0.0

        group_x = current_x
        group_y = current_y

        for d in group["layout"].devices:
            device_layouts.append(DeviceLayout(
                id=d["id"],
                area_id=None,
                x=group_x + GROUP_PADDING + (d["x"] - group["min_x"]),
                y=group_y + LABEL_BAND + GROUP_PADDING + (d["y"] - group["min_y"]),
                layer=d["layer"],
            ))

        vlan_group_results.append(VlanGroupLayout(
            vlan_id=group["vlan_id"],
            name=group["name"],
            x=group_x,
            y=group_y,
            width=group_width,
            height=group_height,
            device_ids=group["device_ids"],
        ))

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
