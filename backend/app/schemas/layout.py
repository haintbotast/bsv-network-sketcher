"""
Schemas for Auto-Layout API.
"""

from pydantic import BaseModel, Field
from typing import Optional


class AutoLayoutOptions(BaseModel):
    """Request schema for auto-layout."""

    algorithm: str = Field(default="sugiyama", description="Layout algorithm to use")
    direction: str = Field(
        default="horizontal",
        description="Layout direction: 'horizontal' (cisco) or 'vertical' (iso)"
    )
    layer_gap: float = Field(
        default=2.0,
        ge=0.5,
        le=5.0,
        description="Gap between layers in inches"
    )
    node_spacing: float = Field(
        default=0.5,
        ge=0.2,
        le=2.0,
        description="Spacing between nodes in same layer (inches)"
    )
    crossing_iterations: int = Field(
        default=24,
        ge=1,
        le=100,
        description="Number of crossing reduction iterations"
    )
    apply_to_db: bool = Field(
        default=False,
        description="If True, apply layout to database. If False, return preview only."
    )
    group_by_area: bool = Field(
        default=True,
        description="If True, layout is computed per-area (macro Area + micro Device)."
    )
    layout_scope: str = Field(
        default="area",
        description="Layout scope: 'area' (device layout inside areas) or 'project' (also reposition areas)."
    )
    anchor_routing: bool = Field(
        default=True,
        description="If True, prefer anchor-based routing for inter-area links (frontend hint)."
    )
    overview_mode: str = Field(
        default="l1-only",
        description="Overview rendering mode hint (frontend)."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "algorithm": "sugiyama",
                "direction": "horizontal",
                "layer_gap": 2.0,
                "node_spacing": 0.5,
                "crossing_iterations": 24,
                "apply_to_db": False,
                "group_by_area": True,
                "layout_scope": "area",
                "anchor_routing": True,
                "overview_mode": "l1-only"
            }
        }


class DeviceLayout(BaseModel):
    """Device layout result."""

    id: str = Field(description="Device ID")
    area_id: Optional[str] = Field(default=None, description="Area ID")
    x: float = Field(description="X coordinate (inches)")
    y: float = Field(description="Y coordinate (inches)")
    layer: int = Field(description="Assigned layer index")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "abc123",
                "area_id": "area123",
                "x": 2.5,
                "y": 1.0,
                "layer": 3
            }
        }


class AreaLayout(BaseModel):
    """Area layout result (future enhancement)."""

    id: str = Field(description="Area ID")
    name: str = Field(description="Area name")
    x: float = Field(description="X coordinate (inches)")
    y: float = Field(description="Y coordinate (inches)")
    width: float = Field(description="Width (inches)")
    height: float = Field(description="Height (inches)")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "area123",
                "name": "Core Network",
                "x": 0.0,
                "y": 0.0,
                "width": 5.0,
                "height": 3.0
            }
        }


class LayoutStats(BaseModel):
    """Layout computation statistics."""

    total_layers: int = Field(description="Number of layers in layout")
    total_crossings: int = Field(description="Number of edge crossings")
    execution_time_ms: int = Field(description="Computation time in milliseconds")
    algorithm: str = Field(description="Algorithm used")

    class Config:
        json_schema_extra = {
            "example": {
                "total_layers": 5,
                "total_crossings": 3,
                "execution_time_ms": 85,
                "algorithm": "sugiyama"
            }
        }


class LayoutResult(BaseModel):
    """Auto-layout result response."""

    devices: list[DeviceLayout] = Field(description="Device layouts")
    areas: Optional[list[AreaLayout]] = Field(
        default=None,
        description="Area layouts (optional)"
    )
    stats: LayoutStats = Field(description="Layout statistics")

    class Config:
        json_schema_extra = {
            "example": {
                "devices": [
                    {"id": "abc123", "x": 2.5, "y": 1.0, "layer": 3},
                    {"id": "def456", "x": 4.5, "y": 1.0, "layer": 3}
                ],
                "areas": None,
                "stats": {
                    "total_layers": 5,
                    "total_crossings": 3,
                    "execution_time_ms": 85,
                    "algorithm": "sugiyama"
                }
            }
        }
