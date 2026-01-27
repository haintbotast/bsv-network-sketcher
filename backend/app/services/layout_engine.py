"""
Layout Engine - Sugiyama Layered Graph Drawing Algorithm

Implements topology-aware auto-layout for network diagrams using
the Sugiyama algorithm with network-specific heuristics.

Algorithm phases:
1. Cycle Removal: Convert directed graph to DAG
2. Layer Assignment: Assign hierarchical layers (network-aware)
3. Crossing Reduction: Minimize edge crossings (barycenter heuristic)
4. Coordinate Assignment: Calculate final x,y positions

References:
- Sugiyama et al. "Methods for Visual Understanding of Hierarchical System Structures"
- Network topology hierarchy: Edge → Security → DMZ → Core → Distribution → Access → Servers
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import re


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class GraphNode:
    """Node in the topology graph."""
    id: str
    name: str
    device_type: str
    area_id: str
    layer: int = -1  # Assigned during layer assignment
    position: int = -1  # Position within layer (assigned during crossing reduction)
    x: float = 0.0  # Final X coordinate (inch)
    y: float = 0.0  # Final Y coordinate (inch)


@dataclass
class GraphEdge:
    """Edge in the topology graph."""
    from_node: str
    to_node: str
    purpose: str  # WAN/DMZ/LAN/MGMT/HA/STORAGE/BACKUP/VPN/DEFAULT
    reversed: bool = False  # True if edge was reversed during cycle removal


@dataclass
class Graph:
    """Topology graph representation."""
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)

    def outgoing_edges(self, node_id: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.from_node == node_id and not e.reversed]

    def incoming_edges(self, node_id: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.to_node == node_id and not e.reversed]

    def all_edges_for_node(self, node_id: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.from_node == node_id or e.to_node == node_id]


@dataclass
class LayoutConfig:
    """Configuration for layout algorithm."""
    direction: str = "horizontal"  # "horizontal" (cisco) or "vertical" (iso)
    layer_gap: float = 2.0  # Gap between layers (inch)
    node_spacing: float = 0.5  # Spacing between nodes in same layer (inch)
    node_width: float = 1.2  # Default node width (inch)
    node_height: float = 0.5  # Default node height (inch)
    crossing_iterations: int = 24  # Barycenter iterations


@dataclass
class LayoutResult:
    """Result of auto-layout computation."""
    devices: list[dict]  # [{id, x, y, layer}, ...]
    stats: dict  # {total_layers, total_crossings, execution_time_ms, algorithm}


# ============================================================================
# Helper Functions
# ============================================================================

def detect_role_from_name(device_name: str) -> Optional[str]:
    """
    Detect device role from name using regex patterns.

    Returns: "router" | "firewall" | "core" | "dist" | "access" | "endpoint" | None
    """
    name_lower = device_name.lower()

    patterns = [
        (r"\brtr\b|router|wan|isp|internet|edge", "router"),
        (r"\bfw\b|firewall|waf|ids|ips|vpn", "firewall"),
        (r"\bcore\b|aggregation|\bagg\b", "core"),
        (r"\bdist\b|distribution", "dist"),
        (r"\bacc\b|access|edge-sw", "access"),
        (r"server|\bsrv\b|nas|storage|backup|db|fe|be|app|web|proxy|pc|printer|ap|camera|lock|phone|ipphone|workstation|client", "endpoint"),
    ]

    for pattern, role in patterns:
        if re.search(pattern, name_lower):
            return role

    return None


def build_graph_from_l1(devices: list, l1_links: list) -> Graph:
    """
    Build directed graph from L1 topology.

    Args:
        devices: List of Device model instances
        l1_links: List of L1Link model instances

    Returns:
        Graph with nodes and edges
    """
    graph = Graph()

    # Add nodes
    for device in devices:
        node = GraphNode(
            id=device.id,
            name=device.name,
            device_type=device.device_type,
            area_id=device.area_id,
        )
        graph.add_node(node)

    # Add edges
    for link in l1_links:
        edge = GraphEdge(
            from_node=link.from_device_id,
            to_node=link.to_device_id,
            purpose=link.purpose,
        )
        graph.add_edge(edge)

    return graph


# ============================================================================
# Phase 1: Cycle Removal
# ============================================================================

def remove_cycles(graph: Graph) -> Graph:
    """
    Remove cycles from graph using DFS-based cycle detection.
    Reverses back edges to create a DAG.

    Args:
        graph: Input directed graph

    Returns:
        Graph with cycles removed (back edges reversed)
    """
    visited = set()
    rec_stack = set()

    def dfs(node_id: str) -> None:
        visited.add(node_id)
        rec_stack.add(node_id)

        for edge in graph.outgoing_edges(node_id):
            if edge.to_node not in visited:
                dfs(edge.to_node)
            elif edge.to_node in rec_stack:
                # Back edge detected - reverse it
                edge.reversed = True
                edge.from_node, edge.to_node = edge.to_node, edge.from_node

        rec_stack.remove(node_id)

    # Run DFS from all nodes
    for node_id in graph.nodes:
        if node_id not in visited:
            dfs(node_id)

    return graph


# ============================================================================
# Phase 2: Layer Assignment (Network-Aware)
# ============================================================================

def assign_layers(graph: Graph, devices: list, l1_links: list) -> Graph:
    """
    Assign hierarchical layers to nodes using multi-source heuristics.

    Combines:
    1. Longest path layering (base topology)
    2. L1 link purposes (WAN/DMZ/LAN patterns)
    3. Device name patterns (Router/FW/Core/Dist/Access)
    4. Connectivity degree (high out-degree → higher tier)

    Args:
        graph: DAG (after cycle removal)
        devices: Original device list
        l1_links: Original L1 link list

    Returns:
        Graph with layer assignments
    """

    # Step 1: Longest path layering (base)
    layers = {}
    for node_id in graph.nodes:
        layers[node_id] = 0

    # Compute longest path from sources
    def compute_longest_path(node_id: str) -> int:
        if node_id in layers and layers[node_id] > 0:
            return layers[node_id]

        incoming = graph.incoming_edges(node_id)
        if not incoming:
            layers[node_id] = 0
            return 0

        max_layer = max(compute_longest_path(e.from_node) for e in incoming)
        layers[node_id] = max_layer + 1
        return layers[node_id]

    for node_id in graph.nodes:
        compute_longest_path(node_id)

    # Step 2: Refinement từ L1 link purposes
    purpose_to_layer_hint = {
        "INTERNET": 0,
        "WAN": 0,
        "VPN": 0,
        "DMZ": 2,
        "MGMT": 1,
        "HA": None,  # Don't affect layer
        "LAN": None,
        "STORAGE": None,
        "BACKUP": None,
        "DEFAULT": None,
    }

    for link in l1_links:
        hint = purpose_to_layer_hint.get(link.purpose)
        if hint is not None:
            # Source of WAN/INTERNET/VPN should be at layer 0-1
            if link.purpose in ["INTERNET", "WAN", "VPN"]:
                from_id = link.from_device_id
                if from_id in layers:
                    layers[from_id] = min(layers[from_id], hint)

            # DMZ devices should be around layer 2
            elif link.purpose == "DMZ":
                to_id = link.to_device_id
                if to_id in layers and layers[to_id] > 3:
                    layers[to_id] = max(2, layers[to_id] - 1)

    # Step 3: Refinement từ device names
    role_to_expected_layer = {
        "router": 0,
        "firewall": 1,
        "core": 3,
        "dist": 4,
        "access": 5,
        "endpoint": 6,
    }

    for device in devices:
        role = detect_role_from_name(device.name)
        if role and device.id in layers:
            expected = role_to_expected_layer[role]
            current = layers[device.id]
            # Nudge towards expected layer (not force, to preserve topology)
            if abs(current - expected) > 2:
                layers[device.id] = (current + expected) // 2

    # Nếu không có link hoặc tất cả đều nằm 1 lớp, ép theo role (top-to-bottom)
    if not l1_links or all(layer == 0 for layer in layers.values()):
        for device in devices:
            role = detect_role_from_name(device.name)
            if role and device.id in layers:
                layers[device.id] = role_to_expected_layer[role]

    # Step 4: Refinement từ connectivity degree
    for node_id, node in graph.nodes.items():
        out_degree = len(graph.outgoing_edges(node_id))
        in_degree = len(graph.incoming_edges(node_id))

        # High out-degree → aggregation layer (core/dist)
        if out_degree > in_degree * 2 and layers[node_id] > 3:
            layers[node_id] = min(layers[node_id], 3)  # Push to core

        # Only incoming → endpoint layer
        if out_degree == 0 and in_degree > 0:
            layers[node_id] = max(layers[node_id], 5)  # Push to endpoint

    # Assign layers to graph nodes
    # Normalize layers to 0..N (giữ thứ tự nhưng tránh gap lớn)
    unique_layers = sorted(set(layers.values()))
    layer_remap = {layer: idx for idx, layer in enumerate(unique_layers)}
    for node_id in layers:
        layers[node_id] = layer_remap[layers[node_id]]

    for node_id, layer in layers.items():
        graph.nodes[node_id].layer = layer

    return graph


# ============================================================================
# Phase 3: Crossing Reduction
# ============================================================================

def reduce_crossings(graph: Graph, config: LayoutConfig) -> Graph:
    """
    Reduce edge crossings using barycenter heuristic.

    Iteratively reorders nodes within each layer to minimize crossings
    with adjacent layers.

    Args:
        graph: Layered graph
        config: Layout configuration

    Returns:
        Graph with position assignments
    """

    # Group nodes by layer
    layers_map: dict[int, list[str]] = {}
    for node_id, node in graph.nodes.items():
        layer = node.layer
        if layer not in layers_map:
            layers_map[layer] = []
        layers_map[layer].append(node_id)

    # Sort layers
    sorted_layers = sorted(layers_map.keys())

    def compute_barycenter(node_id: str, adjacent_layer_nodes: list[str]) -> float:
        """Compute barycenter of node's neighbors in adjacent layer."""
        positions = []
        for edge in graph.all_edges_for_node(node_id):
            neighbor = edge.to_node if edge.from_node == node_id else edge.from_node
            if neighbor in adjacent_layer_nodes:
                neighbor_pos = graph.nodes[neighbor].position
                if neighbor_pos >= 0:
                    positions.append(neighbor_pos)

        return sum(positions) / len(positions) if positions else 0.0

    # Barycenter iterations
    for iteration in range(config.crossing_iterations):
        # Forward pass (top to bottom)
        for i in range(len(sorted_layers)):
            layer_idx = sorted_layers[i]
            layer_nodes = layers_map[layer_idx]

            if i > 0:
                prev_layer = layers_map[sorted_layers[i - 1]]
                barycenters = [(node_id, compute_barycenter(node_id, prev_layer)) for node_id in layer_nodes]
                barycenters.sort(key=lambda x: x[1])
                layer_nodes = [node_id for node_id, _ in barycenters]

            # Assign positions
            for pos, node_id in enumerate(layer_nodes):
                graph.nodes[node_id].position = pos

            layers_map[layer_idx] = layer_nodes

        # Backward pass (bottom to top)
        for i in range(len(sorted_layers) - 1, -1, -1):
            layer_idx = sorted_layers[i]
            layer_nodes = layers_map[layer_idx]

            if i < len(sorted_layers) - 1:
                next_layer = layers_map[sorted_layers[i + 1]]
                barycenters = [(node_id, compute_barycenter(node_id, next_layer)) for node_id in layer_nodes]
                barycenters.sort(key=lambda x: x[1])
                layer_nodes = [node_id for node_id, _ in barycenters]

            # Assign positions
            for pos, node_id in enumerate(layer_nodes):
                graph.nodes[node_id].position = pos

            layers_map[layer_idx] = layer_nodes

    return graph


# ============================================================================
# Phase 4: Coordinate Assignment
# ============================================================================

def assign_coordinates(graph: Graph, config: LayoutConfig) -> Graph:
    """
    Assign final x,y coordinates based on layers and positions.

    Args:
        graph: Graph with layers and positions assigned
        config: Layout configuration

    Returns:
        Graph with x,y coordinates
    """

    # Group by layer
    layers_map: dict[int, list[str]] = {}
    for node_id, node in graph.nodes.items():
        layer = node.layer
        if layer not in layers_map:
            layers_map[layer] = []
        layers_map[layer].append(node_id)

    # Sort each layer by position
    for layer_nodes in layers_map.values():
        layer_nodes.sort(key=lambda nid: graph.nodes[nid].position)

    sorted_layers = sorted(layers_map.keys())

    if config.direction == "horizontal":
        # Cisco-style: left → right (layers on X axis, positions on Y axis)
        # Multi-row layout: if layer has > 4 devices, arrange in grid
        MAX_DEVICES_PER_COLUMN = 4  # Max devices in single column

        for layer_idx, layer in enumerate(sorted_layers):
            layer_nodes = layers_map[layer]
            base_x = layer_idx * (config.node_width + config.layer_gap)

            if len(layer_nodes) <= MAX_DEVICES_PER_COLUMN:
                # Single column layout (original behavior)
                for pos_idx, node_id in enumerate(layer_nodes):
                    y = pos_idx * (config.node_height + config.node_spacing)
                    graph.nodes[node_id].x = round(base_x, 2)
                    graph.nodes[node_id].y = round(y, 2)
            else:
                # Multi-column grid layout
                num_cols = (len(layer_nodes) + MAX_DEVICES_PER_COLUMN - 1) // MAX_DEVICES_PER_COLUMN
                col_spacing = config.node_width * 0.8  # Offset between columns within layer

                for pos_idx, node_id in enumerate(layer_nodes):
                    col = pos_idx // MAX_DEVICES_PER_COLUMN
                    row = pos_idx % MAX_DEVICES_PER_COLUMN

                    x = base_x + (col * col_spacing)
                    y = row * (config.node_height + config.node_spacing)

                    graph.nodes[node_id].x = round(x, 2)
                    graph.nodes[node_id].y = round(y, 2)

    else:  # vertical (ISO-style)
        # ISO-style: top → down (layers on Y axis, positions on X axis)
        # Multi-row layout: if layer has > 4 devices, arrange in grid
        MAX_DEVICES_PER_ROW = 4  # Max devices in single row

        for layer_idx, layer in enumerate(sorted_layers):
            layer_nodes = layers_map[layer]
            base_y = layer_idx * (config.node_height + config.layer_gap)

            if len(layer_nodes) <= MAX_DEVICES_PER_ROW:
                # Single row layout (original behavior)
                for pos_idx, node_id in enumerate(layer_nodes):
                    x = pos_idx * (config.node_width + config.node_spacing)
                    graph.nodes[node_id].x = round(x, 2)
                    graph.nodes[node_id].y = round(base_y, 2)
            else:
                # Multi-row grid layout
                num_rows = (len(layer_nodes) + MAX_DEVICES_PER_ROW - 1) // MAX_DEVICES_PER_ROW
                row_spacing = config.node_height * 0.8  # Offset between rows within layer

                for pos_idx, node_id in enumerate(layer_nodes):
                    row = pos_idx // MAX_DEVICES_PER_ROW
                    col = pos_idx % MAX_DEVICES_PER_ROW

                    x = col * (config.node_width + config.node_spacing)
                    y = base_y + (row * row_spacing)

                    graph.nodes[node_id].x = round(x, 2)
                    graph.nodes[node_id].y = round(y, 2)

    return graph


# ============================================================================
# Main Auto-Layout Function
# ============================================================================

def auto_layout(
    devices: list,
    l1_links: list,
    config: LayoutConfig,
) -> LayoutResult:
    """
    Compute auto-layout using Sugiyama algorithm.

    Args:
        devices: List of Device model instances
        l1_links: List of L1Link model instances
        config: Layout configuration

    Returns:
        LayoutResult with device coordinates and stats
    """
    import time
    start_time = time.time()

    # Build graph
    graph = build_graph_from_l1(devices, l1_links)

    # Phase 1: Remove cycles
    graph = remove_cycles(graph)

    # Phase 2: Assign layers (network-aware)
    graph = assign_layers(graph, devices, l1_links)

    # Phase 3: Reduce crossings
    graph = reduce_crossings(graph, config)

    # Phase 4: Assign coordinates
    graph = assign_coordinates(graph, config)

    # Build result
    device_layouts = []
    for node_id, node in graph.nodes.items():
        device_layouts.append({
            "id": node_id,
            "x": node.x,
            "y": node.y,
            "layer": node.layer,
        })

    # Compute stats
    total_layers = len(set(node.layer for node in graph.nodes.values()))

    # Count crossings (simplified - count edge pairs that cross)
    total_crossings = 0
    edges_list = [e for e in graph.edges if not e.reversed]
    for i, e1 in enumerate(edges_list):
        for e2 in edges_list[i + 1:]:
            n1_from = graph.nodes[e1.from_node]
            n1_to = graph.nodes[e1.to_node]
            n2_from = graph.nodes[e2.from_node]
            n2_to = graph.nodes[e2.to_node]

            # Check if edges cross (simplified heuristic)
            if n1_from.layer == n2_from.layer and n1_to.layer == n2_to.layer:
                if (n1_from.position < n2_from.position and n1_to.position > n2_to.position) or \
                   (n1_from.position > n2_from.position and n1_to.position < n2_to.position):
                    total_crossings += 1

    execution_time_ms = int((time.time() - start_time) * 1000)

    return LayoutResult(
        devices=device_layouts,
        stats={
            "total_layers": total_layers,
            "total_crossings": total_crossings,
            "execution_time_ms": execution_time_ms,
            "algorithm": "sugiyama",
        },
    )
