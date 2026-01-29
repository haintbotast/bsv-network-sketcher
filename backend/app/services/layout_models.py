"""
Layout Models - Data structures cho auto-layout.

Chứa LayoutConfig và LayoutResult cho simple layer layout algorithm.
"""

from dataclasses import dataclass


@dataclass
class LayoutConfig:
    """Configuration for layout algorithm."""
    layer_gap: float = 2.0  # Gap between layers (inch)
    node_spacing: float = 0.5  # Spacing between nodes in same layer (inch)
    node_width: float = 1.2  # Default node width (inch)
    node_height: float = 0.5  # Default node height (inch)


@dataclass
class LayoutResult:
    """Result of auto-layout computation."""
    devices: list[dict]  # [{id, x, y, layer}, ...]
    stats: dict  # {total_layers, total_crossings, execution_time_ms, algorithm}
