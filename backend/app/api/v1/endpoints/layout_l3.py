"""
L3 layout computation: routers on top, subnet groups below.
"""

import ipaddress

from app.services.layout_models import LayoutConfig
from app.services.simple_layer_layout import simple_layer_layout
from app.schemas.layout import DeviceLayout, SubnetGroupLayout, LayoutStats

from .layout_constants import DEFAULT_DEVICE_WIDTH, DEFAULT_DEVICE_HEIGHT
from .layout_geometry import effective_node_size


def compute_layout_l3(
    devices: list,
    links: list,
    l3_addresses: list,
    config: LayoutConfig,
    layout_tuning: dict | None = None,
) -> dict:
    """Compute L3 layout: routers on top, subnet groups below (NS-like L3 view)."""
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
            ip = ipaddress.ip_interface(f"{addr.ip_address}/{addr.prefix_length}")
            subnet_str = str(ip.network)

            device_subnets.setdefault(addr.device_id, set()).add(subnet_str)
            subnet_devices.setdefault(subnet_str, set()).add(addr.device_id)
        except Exception:
            continue

    # Identify routers (devices with multiple subnets)
    router_ids = [dev_id for dev_id, subnets in device_subnets.items() if len(subnets) > 1]
    endpoint_ids = [dev_id for dev_id, subnets in device_subnets.items() if len(subnets) == 1]

    routers = [d for d in devices if d.id in router_ids]

    router_node_width, router_node_height = effective_node_size(
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
        group_device_ids = [dev_id for dev_id in dev_ids if dev_id in endpoint_ids]
        if not group_device_ids:
            continue

        group_devices = [d for d in devices if d.id in group_device_ids]
        if not group_devices:
            continue

        device_id_set = set(group_device_ids)
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

    router_row_height = router_node_height if routers else 0.0
    max_row_width = 15.0
    current_x = 0.0
    current_y = router_row_height + (GROUP_GAP * 2 if routers else 0.0)
    current_row_height = 0.0

    subnet_group_results: list[SubnetGroupLayout] = []

    for group in subnet_groups_data:
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

        current_x += group_width + GROUP_GAP
        current_row_height = max(current_row_height, group_height)

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
