import math

from app.api.v1.endpoints.layout import compute_layout_l1, compute_layout_l2, compute_layout_l3
from app.services.layout_models import LayoutConfig


class DummyArea:
    def __init__(self, area_id: str, name: str) -> None:
        self.id = area_id
        self.name = name
        self.grid_row = 1
        self.grid_col = 1
        self.position_x = None
        self.position_y = None
        self.width = 12.0
        self.height = 8.0


class DummyDevice:
    def __init__(self, device_id: str, area_id: str, name: str, device_type: str) -> None:
        self.id = device_id
        self.area_id = area_id
        self.name = name
        self.device_type = device_type


class DummyL2Segment:
    def __init__(self, seg_id: str, vlan_id: int, name: str) -> None:
        self.id = seg_id
        self.vlan_id = vlan_id
        self.name = name


class DummyL2Assignment:
    def __init__(self, device_id: str, seg_id: str) -> None:
        self.device_id = device_id
        self.l2_segment_id = seg_id
        self.port_mode = "access"


class DummyL3Address:
    def __init__(self, device_id: str, ip: str, prefix: int) -> None:
        self.device_id = device_id
        self.ip_address = ip
        self.prefix_length = prefix


def _compute_row_gap(port_label_band: float) -> float:
    area = DummyArea("A1", "Office")
    devices = [
        DummyDevice("D1", area.id, "HN-SW-1", "Switch"),
        DummyDevice("D2", area.id, "HN-SW-2", "Switch"),
    ]
    config = LayoutConfig(
        layer_gap=1.0,
        node_spacing=0.4,
        node_width=1.0,
        node_height=1.0,
    )
    layout_tuning = {
        "max_nodes_per_row": 1,
        "row_gap": 0.2,
        "row_stagger": 0.0,
        "port_label_band": port_label_band,
    }

    result = compute_layout_l1(
        devices,
        [],
        [area],
        config,
        layout_scope="area",
        layout_tuning=layout_tuning,
    )
    positions = sorted([d for d in result["devices"] if d.area_id == area.id], key=lambda d: d.y)
    return positions[1].y - positions[0].y


def test_port_label_band_increases_row_gap() -> None:
    base_gap = _compute_row_gap(0.0)
    band_gap = _compute_row_gap(0.3)
    assert math.isclose(band_gap - base_gap, 0.3, abs_tol=1e-6)


def _compute_l2_device_y(label_band: float) -> float:
    device = DummyDevice("D1", area_id=None, name="HN-SW-01", device_type="Switch")
    segment = DummyL2Segment("S1", vlan_id=10, name="VLAN 10")
    assignment = DummyL2Assignment(device.id, segment.id)
    config = LayoutConfig(
        layer_gap=1.0,
        node_spacing=0.4,
        node_width=1.0,
        node_height=1.0,
    )
    result = compute_layout_l2(
        [device],
        [],
        [assignment],
        [segment],
        config,
        layout_tuning={"label_band": label_band},
    )
    layout = next(d for d in result["devices"] if d.id == device.id)
    return layout.y


def test_label_band_offsets_l2_device_positions() -> None:
    base_y = _compute_l2_device_y(0.0)
    band_y = _compute_l2_device_y(0.4)
    assert math.isclose(band_y - base_y, 0.4, abs_tol=1e-6)


def _compute_l3_device_y(label_band: float) -> float:
    device = DummyDevice("D1", area_id=None, name="HN-SRV-01", device_type="Server")
    addr = DummyL3Address(device.id, "10.0.0.10", 24)
    config = LayoutConfig(
        layer_gap=1.0,
        node_spacing=0.4,
        node_width=1.0,
        node_height=1.0,
    )
    result = compute_layout_l3(
        [device],
        [],
        [addr],
        config,
        layout_tuning={"label_band": label_band},
    )
    layout = next(d for d in result["devices"] if d.id == device.id)
    return layout.y


def test_label_band_offsets_l3_device_positions() -> None:
    base_y = _compute_l3_device_y(0.0)
    band_y = _compute_l3_device_y(0.4)
    assert math.isclose(band_y - base_y, 0.4, abs_tol=1e-6)
