import unittest

from app.api.v1.endpoints.layout_l1 import compute_layout_l1
from app.services.layout_models import LayoutConfig


class DummyArea:
    def __init__(self, area_id: str, name: str) -> None:
        self.id = area_id
        self.name = name
        self.grid_row = 1
        self.grid_col = 1
        self.position_x = None
        self.position_y = None
        self.width = None
        self.height = None


class DummyDevice:
    def __init__(self, device_id: str, area_id: str, name: str, device_type: str = "Switch") -> None:
        self.id = device_id
        self.area_id = area_id
        self.name = name
        self.device_type = device_type


class DummyLink:
    def __init__(
        self,
        from_device_id: str,
        to_device_id: str,
        from_port: str = "Gi 0/1",
        to_port: str = "Gi 0/1",
    ) -> None:
        self.from_device_id = from_device_id
        self.to_device_id = to_device_id
        self.from_port = from_port
        self.to_port = to_port


class LayoutL1InterAreaSpacingTests(unittest.TestCase):
    def _build_base(self):
        areas = [
            DummyArea("a1", "Access-CH"),
            DummyArea("a2", "Access-TK"),
            DummyArea("a3", "Access-PMJ"),
        ]
        devices = [
            DummyDevice("d1", "a1", "SW-CH-1"),
            DummyDevice("d2", "a2", "SW-TK-1"),
            DummyDevice("d3", "a3", "SW-PMJ-1"),
        ]
        config = LayoutConfig(
            layer_gap=1.0,
            node_spacing=0.5,
            node_width=1.2,
            node_height=0.8,
        )
        return areas, devices, config

    def test_dense_inter_area_links_expand_gap(self) -> None:
        areas, devices, config = self._build_base()

        dense_links = [DummyLink("d1", "d2", "Gi 0/1", "Gi 0/1") for _ in range(8)]
        dense = compute_layout_l1(
            devices=devices,
            links=dense_links,
            areas=areas,
            config=config,
            layout_scope="project",
            layout_tuning={
                "area_gap": 0.8,
                "adaptive_area_gap_factor": 0.06,
                "adaptive_area_gap_cap": 0.8,
                "inter_area_gap_per_link": 0.05,
                "inter_area_gap_cap": 0.5,
            },
            render_tuning={},
        )
        pos = {a.id: a for a in dense["areas"]}

        def edge_gap(left_id: str, right_id: str) -> float:
            left = pos[left_id]
            right = pos[right_id]
            if left.x <= right.x:
                return right.x - (left.x + left.width)
            return left.x - (right.x + right.width)

        connected_gap = edge_gap("a1", "a2")
        unconnected_gap = edge_gap("a2", "a3")
        self.assertGreater(connected_gap, unconnected_gap)

    def test_cloud_area_prefers_upper_tier(self) -> None:
        areas = [
            DummyArea("a1", "VPN-Cloud"),
            DummyArea("a2", "Access-HTM"),
        ]
        devices = [
            DummyDevice("d1", "a1", "CMC-VPN", "Unknown"),
            DummyDevice("d2", "a2", "TK-HTH-1", "Switch"),
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
            layout_tuning={"area_gap": 0.8},
            render_tuning={},
        )
        pos = {a.id: a for a in result["areas"]}
        self.assertLess(pos["a1"].y, pos["a2"].y)


if __name__ == "__main__":
    unittest.main()
