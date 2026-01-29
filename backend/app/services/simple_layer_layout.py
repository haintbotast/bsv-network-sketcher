"""Simple layer layout utilities."""

from __future__ import annotations

from collections import deque
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
    device_type_layers = {
        "Firewall": 0,
        "Router": 0,
        "Switch": 1,
        "Server": 2,
        "Storage": 2,
        "AP": 3,
        "PC": 3,
        "Unknown": 3,
    }

    # Group devices by layer
    layers: dict[int, list] = {}
    device_id_to_device = {d.id: d for d in devices}

    for device in devices:
        device_type = getattr(device, "device_type", "Unknown")
        layer_idx = device_type_layers.get(device_type, 3)
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

    for layer_idx in layer_indices:
        ordered_devices = layer_orders[layer_idx]
        current_x = 0.0

        for device in ordered_devices:
            device_layouts.append({
                "id": device.id,
                "x": current_x,
                "y": current_y,
                "layer": layer_idx,
            })
            current_x += node_width + node_spacing

        # Move to next layer
        current_y += node_height + layer_gap

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
