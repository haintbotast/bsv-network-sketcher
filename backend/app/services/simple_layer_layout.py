"""Simple layer layout utilities."""

from __future__ import annotations

from collections import deque
import re
import time

from app.services.layout_models import LayoutConfig, LayoutResult


def simple_layer_layout(devices: list, links: list, config: LayoutConfig) -> LayoutResult:
    """
    Simple layer-based layout with topology-aware positioning and crossing reduction (NS gốc style).

    Replaces Sugiyama algorithm with simple layering based on device_type.
    Devices are arranged in layers (top-to-bottom), with topology-aware ordering
    within each layer to place connected devices close together.

    Layer assignment (from NS gốc analysis):
    - Layer 0 (top): Firewall, Router (core)
    - Layer 1 (middle-top): Switch (distribution/aggregation)
    - Layer 2 (middle-bottom): Server, Storage
    - Layer 3 (bottom): AP, PC, Unknown (endpoints)

    Within each layer, devices are ordered by connectivity, then refined by barycenter sweeps
    to reduce link crossings across layers.

    Args:
        devices: List of Device model instances
        links: List of L1Link model instances (for topology-aware ordering)
        config: LayoutConfig with node_width, node_height, node_spacing

    Returns:
        LayoutResult with devices list and stats dict
    """

    start_time = time.time()

    # Device type to layer mapping (NS gốc style)
    # Layer assignment (top-to-bottom):
    # 0: Router (edge/WAN)
    # 1: Firewall/Security
    # 2: Core switch
    # 3: Distribution/Access switch
    # 4: Server switch
    # 5: Server/Storage
    # 6: Endpoints (AP/PC/Unknown)
    device_type_layers = {
        "Router": 0,
        "Cloud": 0,
        "Cloud-Network": 0,
        "Cloud-Security": 0,
        "Cloud-Service": 0,
        "Firewall": 1,
        "Server": 5,
        "Storage": 5,
        "AP": 6,
        "PC": 6,
        "Unknown": 6,
    }

    def normalize_name(value: str | None) -> str:
        return (value or "").upper()

    core_token_re = re.compile(r"(?:^|[^A-Z0-9])CR\d*(?:$|[^A-Z0-9])")
    dist_token_re = re.compile(r"(?:^|[^A-Z0-9])DS\d*(?:$|[^A-Z0-9])")
    server_token_re = re.compile(r"(?:^|[^A-Z0-9])SV\d*(?:$|[^A-Z0-9])")

    def detect_switch_layer(device_name: str) -> int:
        if core_token_re.search(device_name):
            return 2
        if dist_token_re.search(device_name):
            return 3
        if server_token_re.search(device_name):
            return 4
        if "CORE" in device_name:
            return 2
        if "DIST" in device_name or "DISTR" in device_name:
            return 3
        if "SRV" in device_name or "SERVER" in device_name or "STORAGE" in device_name or "NAS" in device_name or "SAN" in device_name:
            return 4
        if "ACC" in device_name or "ACCESS" in device_name:
            return 3
        return 3

    # Group devices by layer
    layers: dict[int, list] = {}
    device_id_to_device = {d.id: d for d in devices}

    for device in devices:
        device_type = getattr(device, "device_type", "Unknown")
        if device_type == "Switch":
            layer_idx = detect_switch_layer(normalize_name(getattr(device, "name", "")))
        else:
            layer_idx = device_type_layers.get(device_type, 5)
        layers.setdefault(layer_idx, []).append(device)

    # Build adjacency graph for topology-aware ordering
    adjacency: dict[str, set[str]] = {d.id: set() for d in devices}
    edges: list[tuple[str, str]] = []
    for link in links:
        if link.from_device_id in adjacency and link.to_device_id in adjacency:
            adjacency[link.from_device_id].add(link.to_device_id)
            adjacency[link.to_device_id].add(link.from_device_id)
            edges.append((link.from_device_id, link.to_device_id))

    def topology_aware_order(layer_devices: list, prev_layer_devices: list | None = None) -> list:
        """
        Order devices within a layer based on connectivity.

        If prev_layer_devices is provided, prioritize connections to previous layer.
        Otherwise, use BFS from most connected device.
        """
        if len(layer_devices) <= 1:
            return layer_devices

        device_ids = {d.id for d in layer_devices}
        visited = set()
        ordered = []

        # Find starting device (most connected to previous layer, or most connected overall)
        if prev_layer_devices:
            prev_layer_ids = {d.id for d in prev_layer_devices}
            # Start with device most connected to previous layer
            start_device = max(
                layer_devices,
                key=lambda d: len(adjacency[d.id] & prev_layer_ids)
            )
        else:
            # Start with most connected device
            start_device = max(
                layer_devices,
                key=lambda d: len(adjacency[d.id] & device_ids)
            )

        # BFS traversal to order devices
        queue = deque([start_device])
        visited.add(start_device.id)

        while queue:
            current = queue.popleft()
            ordered.append(current)

            # Find neighbors in same layer, sort by connection count
            neighbors = [
                device_id_to_device[neighbor_id]
                for neighbor_id in adjacency[current.id]
                if neighbor_id in device_ids and neighbor_id not in visited
            ]

            # Sort neighbors by connection count (descending)
            neighbors.sort(key=lambda d: len(adjacency[d.id] & device_ids), reverse=True)

            for neighbor in neighbors:
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    queue.append(neighbor)

        # Add any unconnected devices at the end
        for device in layer_devices:
            if device.id not in visited:
                ordered.append(device)
                visited.add(device.id)

        return ordered

    # Initial ordering per layer (top-to-bottom) using topology-aware BFS
    layer_indices = sorted(layers.keys())
    layer_orders: dict[int, list] = {}
    prev_layer_devices = None
    for layer_idx in layer_indices:
        layer_devices = layers[layer_idx]
        ordered_devices = topology_aware_order(layer_devices, prev_layer_devices)
        layer_orders[layer_idx] = ordered_devices
        prev_layer_devices = ordered_devices

    name_token_re = re.compile(r"[^A-Za-z0-9]+")
    trailing_num_re = re.compile(r"^([A-Z]+)(\d+)$")
    reserved_site_tokens = {
        "SW",
        "SWITCH",
        "RTR",
        "ROUTER",
        "FW",
        "FIREWALL",
        "CORE",
        "DIST",
        "DISTRIBUTION",
        "ACCESS",
        "ACC",
        "EDGE",
        "WAN",
        "DMZ",
        "SERVER",
        "SRV",
        "STORAGE",
        "NAS",
        "SAN",
        "AP",
        "PC",
    }

    def tokenize_name(raw: str) -> list[str]:
        return [token for token in name_token_re.split(raw.upper()) if token]

    def is_site_token(token: str) -> bool:
        if token in reserved_site_tokens:
            return False
        if not (2 <= len(token) <= 5):
            return False
        if not token.isalnum():
            return False
        return True

    def extract_name_affinity(raw: str) -> tuple[str, str, int | None]:
        tokens = tokenize_name(raw)
        if not tokens:
            return "", raw.strip().upper(), None
        site = tokens[0] if is_site_token(tokens[0]) else ""
        suffix = None
        stem_tokens = list(tokens)
        if stem_tokens:
            last = stem_tokens[-1]
            if last.isdigit():
                suffix = int(last)
                stem_tokens = stem_tokens[:-1]
            else:
                match = trailing_num_re.match(last)
                if match:
                    stem_tokens = stem_tokens[:-1] + [match.group(1)]
                    suffix = int(match.group(2))
        if not stem_tokens:
            stem_tokens = tokens
        stem = "-".join(stem_tokens)
        return site, stem, suffix

    def build_position_map() -> dict[int, dict[str, int]]:
        return {
            layer_idx: {device.id: idx for idx, device in enumerate(layer_orders[layer_idx])}
            for layer_idx in layer_indices
        }

    def order_by_barycenter(
        layer_idx: int,
        target_layers: list[int],
        position_map: dict[int, dict[str, int]],
    ) -> list:
        """Order devices by weighted barycenter of neighbors in target layers."""
        devices_in_layer = layer_orders[layer_idx]
        if len(devices_in_layer) <= 1 or not target_layers:
            return devices_in_layer

        current_positions = position_map[layer_idx]

        def barycenter(device) -> float | None:
            weighted_sum = 0.0
            weight_total = 0.0
            for target_layer in target_layers:
                target_positions = position_map[target_layer]
                layer_distance = abs(layer_idx - target_layer)
                if layer_distance == 0:
                    continue
                weight = 1.0 / layer_distance
                for neighbor_id in adjacency[device.id]:
                    if neighbor_id in target_positions:
                        weighted_sum += target_positions[neighbor_id] * weight
                        weight_total += weight
            if weight_total == 0:
                return None
            return weighted_sum / weight_total

        scored = []
        for device in devices_in_layer:
            score = barycenter(device)
            scored.append((device, score, current_positions.get(device.id, 0)))

        scored.sort(
            key=lambda item: (
                item[1] if item[1] is not None else item[2],
                item[2],
            )
        )
        return [device for device, _, _ in scored]

    def reduce_crossings(iterations: int) -> None:
        if len(layer_indices) <= 1:
            return
        for _ in range(iterations):
            # Downward sweep
            position_map = build_position_map()
            for idx in range(1, len(layer_indices)):
                layer_idx = layer_indices[idx]
                target_layers = layer_indices[:idx]
                layer_orders[layer_idx] = order_by_barycenter(layer_idx, target_layers, position_map)

            # Upward sweep
            position_map = build_position_map()
            for idx in range(len(layer_indices) - 2, -1, -1):
                layer_idx = layer_indices[idx]
                target_layers = layer_indices[idx + 1:]
                layer_orders[layer_idx] = order_by_barycenter(layer_idx, target_layers, position_map)

    # Run barycenter crossing reduction (12 iterations is empirically good)
    reduce_crossings(12)

    def normalize_device_type(device) -> str:
        dtype = getattr(device, "device_type", None) or "Unknown"
        return str(dtype).strip().lower() or "unknown"

    def affinity_group_key(device) -> tuple[str, str]:
        name = getattr(device, "name", None) or getattr(device, "id", "")
        site, stem, _ = extract_name_affinity(str(name))
        return (site, stem or str(name).strip().upper())

    def affinity_sort_key(device, fallback_index: int) -> tuple[int, int, int]:
        name = getattr(device, "name", None) or getattr(device, "id", "")
        _, _, suffix = extract_name_affinity(str(name))
        if suffix is None:
            return (1, fallback_index, fallback_index)
        return (0, suffix, fallback_index)

    def cluster_by_affinity(ordered: list) -> list:
        if len(ordered) <= 1:
            return ordered
        groups: dict[tuple[str, str], list] = {}
        group_order: list[tuple[str, str]] = []
        for device in ordered:
            key = affinity_group_key(device)
            if key not in groups:
                groups[key] = []
                group_order.append(key)
            groups[key].append(device)

        clustered: list = []
        for key in group_order:
            group = groups[key]
            if len(group) > 1:
                indexed = list(enumerate(group))
                indexed.sort(key=lambda item: affinity_sort_key(item[1], item[0]))
                group = [device for _, device in indexed]
            clustered.extend(group)
        return clustered

    def apply_affinity_order(layer_devices: list) -> list:
        if len(layer_devices) <= 1:
            return layer_devices
        blocks: list[list] = []
        current_type: str | None = None
        current_block: list = []
        for device in layer_devices:
            dtype = normalize_device_type(device)
            if current_type is None or dtype == current_type:
                current_block.append(device)
                current_type = dtype
            else:
                blocks.append(current_block)
                current_block = [device]
                current_type = dtype
        if current_block:
            blocks.append(current_block)

        result: list = []
        for block in blocks:
            result.extend(cluster_by_affinity(block))
        return result

    for layer_idx in layer_indices:
        layer_orders[layer_idx] = apply_affinity_order(layer_orders[layer_idx])

    def split_rows_by_type(ordered: list, max_nodes: int) -> list[list]:
        if max_nodes <= 0:
            return [ordered]

        # Group contiguous blocks by device type (preserve barycenter order)
        blocks: list[tuple[str, list]] = []
        current_type: str | None = None
        current_block: list = []

        for device in ordered:
            dtype = normalize_device_type(device)
            if current_type is None or dtype == current_type:
                current_block.append(device)
                current_type = dtype
            else:
                blocks.append((current_type, current_block))
                current_type = dtype
                current_block = [device]

        if current_block:
            blocks.append((current_type or "unknown", current_block))

        rows: list[list] = []
        current_row: list = []

        for _dtype, block in blocks:
            if len(block) > max_nodes:
                if current_row:
                    rows.append(current_row)
                    current_row = []
                for i in range(0, len(block), max_nodes):
                    rows.append(block[i:i + max_nodes])
                continue

            if len(current_row) + len(block) <= max_nodes:
                current_row.extend(block)
            else:
                if current_row:
                    rows.append(current_row)
                current_row = list(block)

        if current_row:
            rows.append(current_row)

        return rows

    def compute_crossings() -> int:
        position_map = build_position_map()
        device_layer = {
            device.id: layer_idx
            for layer_idx, devices_in_layer in layer_orders.items()
            for device in devices_in_layer
        }
        edges_by_pair: dict[tuple[int, int], list[tuple[str, str]]] = {}
        for from_id, to_id in edges:
            if from_id not in device_layer or to_id not in device_layer:
                continue
            from_layer = device_layer[from_id]
            to_layer = device_layer[to_id]
            if from_layer == to_layer:
                continue
            if from_layer > to_layer:
                from_id, to_id = to_id, from_id
                from_layer, to_layer = to_layer, from_layer
            edges_by_pair.setdefault((from_layer, to_layer), []).append((from_id, to_id))

        total = 0
        for (from_layer, to_layer), pair_edges in edges_by_pair.items():
            for i in range(len(pair_edges)):
                a_from, a_to = pair_edges[i]
                a_from_pos = position_map[from_layer][a_from]
                a_to_pos = position_map[to_layer][a_to]
                for j in range(i + 1, len(pair_edges)):
                    b_from, b_to = pair_edges[j]
                    b_from_pos = position_map[from_layer][b_from]
                    b_to_pos = position_map[to_layer][b_to]
                    if (a_from_pos - b_from_pos) * (a_to_pos - b_to_pos) < 0:
                        total += 1
        return total

    # Layout devices layer by layer (top-to-bottom) with final ordering
    device_layouts = []
    current_y = 0.0
    layer_gap = config.layer_gap
    node_spacing = config.node_spacing
    node_width = config.node_width
    node_height = config.node_height
    row_gap = config.row_gap if config.row_gap is not None else max(0.2, node_spacing * 0.6)
    row_stagger = max(0.0, min(config.row_stagger or 0.0, 1.0))

    for layer_idx in layer_indices:
        ordered_devices = layer_orders[layer_idx]
        if not ordered_devices:
            continue

        max_nodes_per_row = config.max_nodes_per_row or len(ordered_devices)
        if max_nodes_per_row <= 0:
            max_nodes_per_row = len(ordered_devices)

        rows = split_rows_by_type(ordered_devices, max_nodes_per_row)
        row_widths = [
            (len(row_devices) * node_width) + max(0, len(row_devices) - 1) * node_spacing
            for row_devices in rows
        ]
        max_row_width = max(row_widths) if row_widths else node_width

        row_step_x = node_width + node_spacing
        for row_idx, row_devices in enumerate(rows):
            row_y = current_y + row_idx * (node_height + row_gap)
            row_width = row_widths[row_idx]
            center_offset_x = max(0.0, (max_row_width - row_width) / 2.0)

            stagger_offset = 0.0
            if len(rows) > 1 and row_stagger > 0:
                stagger_delta = row_step_x * row_stagger * 0.5
                stagger_offset = stagger_delta if row_idx % 2 == 1 else -stagger_delta

            current_x = center_offset_x + stagger_offset
            for device in row_devices:
                device_layouts.append({
                    "id": device.id,
                    "x": current_x,
                    "y": row_y,
                    "layer": layer_idx,
                })
                current_x += row_step_x

        total_layer_height = len(rows) * node_height + max(0, len(rows) - 1) * row_gap
        current_y += total_layer_height + layer_gap

    # Compute stats
    execution_time_ms = int((time.time() - start_time) * 1000)
    total_layers = len(layers)
    total_crossings = compute_crossings()

    stats = {
        "total_layers": total_layers,
        "total_crossings": total_crossings,
        "execution_time_ms": execution_time_ms,
        "algorithm": "simple_layer_topology_aware",
    }

    return LayoutResult(
        devices=device_layouts,
        stats=stats,
    )
