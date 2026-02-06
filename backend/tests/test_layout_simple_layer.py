import unittest

from app.services.simple_layer_layout import simple_layer_layout
from app.services.layout_models import LayoutConfig


class DummyDevice:
    def __init__(self, device_id: str, device_type: str, name: str | None = None) -> None:
        self.id = device_id
        self.device_type = device_type
        self.name = name or device_id


class DummyLink:
    def __init__(self, from_id: str, to_id: str) -> None:
        self.from_device_id = from_id
        self.to_device_id = to_id


class SimpleLayerLayoutTests(unittest.TestCase):
    def test_crossing_reduction_orders_layer(self) -> None:
        devices = [
            DummyDevice("A", "Router"),
            DummyDevice("B", "Router"),
            DummyDevice("C", "Switch"),
            DummyDevice("D", "Switch"),
        ]
        links = [
            DummyLink("A", "D"),
            DummyLink("B", "C"),
        ]
        config = LayoutConfig(
            layer_gap=1.0,
            node_spacing=0.5,
            node_width=1.0,
            node_height=1.0,
        )

        result = simple_layer_layout(devices, links, config)
        layer0 = sorted([d for d in result.devices if d["layer"] == 0], key=lambda d: d["x"])
        layer_switch = sorted([d for d in result.devices if d["layer"] == 3], key=lambda d: d["x"])

        self.assertEqual([d["id"] for d in layer0], ["A", "B"])
        self.assertEqual([d["id"] for d in layer_switch], ["D", "C"])
        self.assertGreaterEqual(result.stats["total_crossings"], 0)

    def test_group_same_type_on_row_when_possible(self) -> None:
        devices = [
            DummyDevice("S1", "Server"),
            DummyDevice("S2", "Server"),
            DummyDevice("S3", "Server"),
            DummyDevice("T1", "Storage"),
            DummyDevice("T2", "Storage"),
            DummyDevice("T3", "Storage"),
        ]
        config = LayoutConfig(
            layer_gap=1.0,
            node_spacing=0.5,
            node_width=1.0,
            node_height=1.0,
            max_nodes_per_row=4,
            row_gap=0.2,
            row_stagger=0.0,
        )

        result = simple_layer_layout(devices, [], config)
        rows = {}
        for device in result.devices:
            row_key = round(device["y"], 3)
            rows.setdefault(row_key, []).append(device["id"])

        ordered_rows = [rows[key] for key in sorted(rows.keys())]
        self.assertEqual(ordered_rows[0], ["S1", "S2", "S3"])
        self.assertEqual(ordered_rows[1], ["T1", "T2", "T3"])

    def test_group_by_name_affinity_with_numeric_suffix(self) -> None:
        devices = [
            DummyDevice("C2", "Switch", "HN-SW-CORE-02"),
            DummyDevice("D1", "Switch", "HN-SW-DIST-01"),
            DummyDevice("C1", "Switch", "HN-SW-CORE-01"),
            DummyDevice("D2", "Switch", "HN-SW-DIST-02"),
        ]
        config = LayoutConfig(
            layer_gap=1.0,
            node_spacing=0.5,
            node_width=1.0,
            node_height=1.0,
            max_nodes_per_row=10,
            row_gap=0.2,
            row_stagger=0.0,
        )

        result = simple_layer_layout(devices, [], config)
        layer_core = sorted([d for d in result.devices if d["layer"] == 2], key=lambda d: d["x"])
        layer_dist = sorted([d for d in result.devices if d["layer"] == 3], key=lambda d: d["x"])
        self.assertEqual([d["id"] for d in layer_core], ["C1", "C2"])
        self.assertEqual([d["id"] for d in layer_dist], ["D1", "D2"])

    def test_rows_are_centered_when_split(self) -> None:
        devices = [
            DummyDevice("S1", "Server"),
            DummyDevice("S2", "Server"),
            DummyDevice("S3", "Server"),
        ]
        config = LayoutConfig(
            layer_gap=1.0,
            node_spacing=0.5,
            node_width=1.0,
            node_height=1.0,
            max_nodes_per_row=2,
            row_gap=0.2,
            row_stagger=0.0,
        )

        result = simple_layer_layout(devices, [], config)
        second_row = [d for d in result.devices if round(d["y"], 3) == 1.2]
        self.assertEqual(len(second_row), 1)
        # Row 2 has one device; it must be centered under row 1 (x = 0.75 with config above).
        self.assertAlmostEqual(second_row[0]["x"], 0.75, places=3)


if __name__ == "__main__":
    unittest.main()
