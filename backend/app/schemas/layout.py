"""
Schemas for Auto-Layout API.
"""

from pydantic import BaseModel, Field
from typing import Optional


class AutoLayoutOptions(BaseModel):
    """Request schema for auto-layout."""

    layer_gap: float = Field(
        default=1.0,
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
    view_mode: str = Field(
        default="L1",
        description="View mode: 'L1' (physical), 'L2' (VLAN grouping), or 'L3' (subnet grouping)."
    )
    normalize_topology: bool = Field(
        default=False,
        description="If True, auto-normalize areas/devices (Security/Server/Monitor) before layout."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "layer_gap": 2.0,
                "node_spacing": 0.5,
                "apply_to_db": False,
                "group_by_area": True,
                "layout_scope": "area",
                "anchor_routing": True,
                "overview_mode": "l1-only",
                "normalize_topology": False,
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


class VlanGroupLayout(BaseModel):
    """VLAN group layout result (L2 view)."""

    vlan_id: int = Field(description="VLAN ID")
    name: str = Field(description="VLAN name")
    x: float = Field(description="X coordinate (inches)")
    y: float = Field(description="Y coordinate (inches)")
    width: float = Field(description="Width (inches)")
    height: float = Field(description="Height (inches)")
    device_ids: list[str] = Field(description="List of device IDs in this VLAN")

    class Config:
        json_schema_extra = {
            "example": {
                "vlan_id": 10,
                "name": "VLAN 10",
                "x": 2.0,
                "y": 3.0,
                "width": 4.0,
                "height": 2.5,
                "device_ids": ["dev1", "dev2", "dev3"]
            }
        }


class SubnetGroupLayout(BaseModel):
    """Subnet group layout result (L3 view)."""

    subnet: str = Field(description="Subnet CIDR (e.g., 10.0.0.0/24)")
    name: str = Field(description="Subnet name")
    x: float = Field(description="X coordinate (inches)")
    y: float = Field(description="Y coordinate (inches)")
    width: float = Field(description="Width (inches)")
    height: float = Field(description="Height (inches)")
    device_ids: list[str] = Field(description="List of device IDs in this subnet")
    router_id: Optional[str] = Field(default=None, description="Router device ID for this subnet")

    class Config:
        json_schema_extra = {
            "example": {
                "subnet": "10.0.0.0/24",
                "name": "10.0.0.0/24",
                "x": 0.0,
                "y": 5.0,
                "width": 3.5,
                "height": 2.0,
                "device_ids": ["pc1", "pc2"],
                "router_id": "router1"
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
                "algorithm": "simple_layer_grouped"
            }
        }


class LayoutResult(BaseModel):
    """Auto-layout result response."""

    devices: list[DeviceLayout] = Field(description="Device layouts")
    areas: Optional[list[AreaLayout]] = Field(
        default=None,
        description="Area layouts (optional, L1 view)"
    )
    vlan_groups: Optional[list[VlanGroupLayout]] = Field(
        default=None,
        description="VLAN group layouts (optional, L2 view)"
    )
    subnet_groups: Optional[list[SubnetGroupLayout]] = Field(
        default=None,
        description="Subnet group layouts (optional, L3 view)"
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
                "vlan_groups": None,
                "subnet_groups": None,
                "stats": {
                    "total_layers": 5,
                    "total_crossings": 3,
                    "execution_time_ms": 85,
                    "algorithm": "simple_layer_grouped"
                }
            }
        }
