"""
Layout Models - Data structures cho auto-layout.

Chứa LayoutConfig và LayoutResult cho simple layer layout algorithm.
"""

from dataclasses import dataclass


@dataclass
class LayoutConfig:
    """Configuration for layout algorithm."""
    layer_gap: float = 1.5  # Gap between layers (inch)
    node_spacing: float = 0.8  # Spacing between nodes in same layer (inch)
    node_width: float = 1.2  # Default node width (inch)
    node_height: float = 0.5  # Default node height (inch)
    max_nodes_per_row: int | None = None  # Max nodes per row inside a layer
    row_gap: float = 0.5  # Vertical gap between rows inside a layer (inch)
    row_stagger: float = 0.5  # Stagger ratio for alternating rows (0-1)


@dataclass
class LayoutResult:
    """Result of auto-layout computation."""
    devices: list[dict]  # [{id, x, y, layer}, ...]
    stats: dict  # {total_layers, total_crossings, execution_time_ms, algorithm}
