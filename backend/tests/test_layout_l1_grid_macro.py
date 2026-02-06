import unittest

from app.api.v1.endpoints.layout_l1 import compute_layout_l1
from app.services.layout_models import LayoutConfig


class DummyArea:
    def __init__(self, area_id: str, name: str, grid_row: int, grid_col: int) -> None:
        self.id = area_id
        self.name = name
        self.grid_row = grid_row
        self.grid_col = grid_col
        self.position_x = None
        self.position_y = None
        self.width = None
        self.height = None


class DummyDevice:
    def __init__(self, device_id: str, area_id: str, name: str, device_type: str) -> None:
        self.id = device_id
        self.area_id = area_id
        self.name = name
        self.device_type = device_type


class LayoutL1GridMacroTests(unittest.TestCase):
    def test_grid_layout_priority_over_tier_when_grid_is_explicit(self) -> None:
        areas = [
            DummyArea("a1", "Access-Left", grid_row=1, grid_col=1),
            DummyArea("a2", "Access-Right", grid_row=1, grid_col=2),
            DummyArea("a3", "Edge-WAN", grid_row=2, grid_col=1),
        ]
        devices = [
            DummyDevice("d1", "a1", "ACC-SW-1", "Switch"),
            DummyDevice("d2", "a2", "ACC-SW-2", "Switch"),
            DummyDevice("d3", "a3", "RTR-1", "Router"),
        ]
        config = LayoutConfig(
            layer_gap=1.0,
            node_spacing=0.5,
            node_width=1.2,
            node_height=0.8,
        )

        result = compute_layout_l1(
            devices=devices,
            links=[],
            areas=areas,
            config=config,
            layout_scope="project",
            layout_tuning={
                "area_gap": 1.0,
                "area_padding": 0.35,
                "label_band": 0.5,
                "max_row_width_base": 12.0,
            },
            render_tuning={},
        )

        area_pos = {a.id: a for a in result["areas"]}
        self.assertAlmostEqual(area_pos["a1"].y, area_pos["a2"].y, places=6)
        self.assertLess(area_pos["a1"].x, area_pos["a2"].x)
        self.assertLess(area_pos["a1"].y, area_pos["a3"].y)

    def test_grid_column_center_alignment_for_mixed_area_widths(self) -> None:
        areas = [
            DummyArea("a1", "Access-Compact", grid_row=1, grid_col=1),
            DummyArea("a2", "Access-Wide", grid_row=2, grid_col=1),
            DummyArea("a3", "Access-Right", grid_row=1, grid_col=2),
        ]
        devices = [
            DummyDevice("d1", "a1", "ACC-SW-1", "Switch"),
            DummyDevice("d2", "a3", "ACC-SW-2", "Switch"),
            DummyDevice("d3", "a2", "ACC-SW-3", "Switch"),
            DummyDevice("d4", "a2", "ACC-SW-4", "Switch"),
            DummyDevice("d5", "a2", "ACC-SW-5", "Switch"),
            DummyDevice("d6", "a2", "ACC-SW-6", "Switch"),
            DummyDevice("d7", "a2", "ACC-SW-7", "Switch"),
            DummyDevice("d8", "a2", "ACC-SW-8", "Switch"),
        ]
        config = LayoutConfig(
            layer_gap=1.0,
            node_spacing=0.5,
            node_width=1.2,
            node_height=0.8,
        )

        result = compute_layout_l1(
            devices=devices,
            links=[],
            areas=areas,
            config=config,
            layout_scope="project",
            layout_tuning={
                "area_gap": 1.0,
                "area_padding": 0.35,
                "label_band": 0.5,
                "max_row_width_base": 12.0,
            },
            render_tuning={},
        )

        area_pos = {a.id: a for a in result["areas"]}
        # Col 1 has mixed widths: compact area should be centered in column slot (x shifted right vs wide area).
        self.assertGreater(area_pos["a1"].x, area_pos["a2"].x)
        self.assertLess(area_pos["a1"].x, area_pos["a3"].x)


if __name__ == "__main__":
    unittest.main()
