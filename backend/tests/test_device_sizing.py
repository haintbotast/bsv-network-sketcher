"""
Tests cho port-band-aware device sizing (layout_geometry).
"""

import math
import unittest

from app.api.v1.endpoints.layout_geometry import (
    _estimate_band_width_px,
    estimate_device_rendered_size,
)
from app.api.v1.endpoints.layout_constants import (
    UNIT_PX,
    PORT_CELL_MIN_WIDTH_PX,
    PORT_CELL_HEIGHT_PX,
    PORT_CELL_GAP_PX,
    PORT_BAND_PADDING_X_PX,
    PORT_BAND_PADDING_Y_PX,
    PORT_FONT_SIZE_PX,
    PORT_CELL_TEXT_PADDING_PX,
    DEVICE_LABEL_MIN_HEIGHT_PX,
    DEVICE_STANDARD_TOTAL_HEIGHT_PX,
    DEVICE_MIN_WIDTH_PX,
)


class TestEstimateBandWidthPx(unittest.TestCase):
    def test_empty_ports(self):
        self.assertEqual(_estimate_band_width_px([]), 0.0)

    def test_single_short_port(self):
        # "Gi1" → 3 chars → ceil(3*6.2+10) = ceil(28.6) = 29 < 30 → min 30
        result = _estimate_band_width_px(["Gi1"])
        expected = PORT_BAND_PADDING_X_PX * 2 + PORT_CELL_MIN_WIDTH_PX
        self.assertAlmostEqual(result, expected)

    def test_single_long_port(self):
        # "Ge0/0/1" → 7 chars → ceil(7*6.2+10) = ceil(53.4) = 54
        char_width = PORT_FONT_SIZE_PX * 0.62
        cell_w = max(PORT_CELL_MIN_WIDTH_PX, math.ceil(7 * char_width + PORT_CELL_TEXT_PADDING_PX))
        result = _estimate_band_width_px(["Ge0/0/1"])
        expected = PORT_BAND_PADDING_X_PX * 2 + cell_w
        self.assertAlmostEqual(result, expected)

    def test_multiple_ports(self):
        ports = ["Gi1", "Gi2", "Gi3"]
        result = _estimate_band_width_px(ports)
        cells = PORT_CELL_MIN_WIDTH_PX * 3
        gaps = PORT_CELL_GAP_PX * 2
        expected = PORT_BAND_PADDING_X_PX * 2 + cells + gaps
        self.assertAlmostEqual(result, expected)


class TestEstimateDeviceRenderedSize(unittest.TestCase):
    def test_no_ports(self):
        w, h = estimate_device_rendered_size(1.2, 0.8, [])
        self.assertAlmostEqual(w, max(1.2 * UNIT_PX, DEVICE_MIN_WIDTH_PX) / UNIT_PX)
        self.assertAlmostEqual(h, max(0.8 * UNIT_PX, DEVICE_STANDARD_TOTAL_HEIGHT_PX) / UNIT_PX)

    def test_single_port_top_band_only(self):
        w, h = estimate_device_rendered_size(1.2, 0.8, ["Gi1"])
        # 1 port → ceil(1/2)=1 on side_a, 0 on side_b → top band only
        band_h = PORT_CELL_HEIGHT_PX + PORT_BAND_PADDING_Y_PX * 2
        base_total_px = max(0.8 * UNIT_PX, DEVICE_STANDARD_TOTAL_HEIGHT_PX)
        body_px = max(base_total_px - band_h, DEVICE_LABEL_MIN_HEIGHT_PX)
        expected_h = (band_h + body_px) / UNIT_PX
        self.assertAlmostEqual(h, expected_h)

    def test_two_ports_both_bands(self):
        w, h = estimate_device_rendered_size(1.2, 0.8, ["Gi1", "Gi2"])
        band_h = PORT_CELL_HEIGHT_PX + PORT_BAND_PADDING_Y_PX * 2
        base_total_px = max(0.8 * UNIT_PX, DEVICE_STANDARD_TOTAL_HEIGHT_PX)
        body_px = max(base_total_px - band_h - band_h, DEVICE_LABEL_MIN_HEIGHT_PX)
        expected_h = (band_h + body_px + band_h) / UNIT_PX
        self.assertAlmostEqual(h, expected_h)

    def test_many_ports_width_expands(self):
        ports = [f"Ge0/0/{i}" for i in range(10)]
        w, h = estimate_device_rendered_size(1.2, 0.8, ports)
        self.assertGreater(w, 1.2)

    def test_six_ports_symmetric(self):
        ports = ["Gi1", "Gi2", "Gi3", "Gi4", "Gi5", "Gi6"]
        w, h = estimate_device_rendered_size(1.2, 0.8, ports)
        band_h = PORT_CELL_HEIGHT_PX + PORT_BAND_PADDING_Y_PX * 2
        base_total_px = max(0.8 * UNIT_PX, DEVICE_STANDARD_TOTAL_HEIGHT_PX)
        body_px = max(base_total_px - band_h - band_h, DEVICE_LABEL_MIN_HEIGHT_PX)
        expected_h = (band_h + body_px + band_h) / UNIT_PX
        self.assertAlmostEqual(h, expected_h)
        self.assertGreaterEqual(w, 1.2)

    def test_twelve_long_ports(self):
        ports = [f"GigabitEthernet0/0/{i}" for i in range(12)]
        w, h = estimate_device_rendered_size(1.2, 0.8, ports)
        self.assertGreater(w, 2.0)
        band_h = PORT_CELL_HEIGHT_PX + PORT_BAND_PADDING_Y_PX * 2
        base_total_px = max(0.8 * UNIT_PX, DEVICE_STANDARD_TOTAL_HEIGHT_PX)
        body_px = max(base_total_px - band_h - band_h, DEVICE_LABEL_MIN_HEIGHT_PX)
        expected_h = (band_h + body_px + band_h) / UNIT_PX
        self.assertAlmostEqual(h, expected_h)

    def test_height_always_greater_with_ports(self):
        """Device with ports should always be taller than without."""
        _, h_no_ports = estimate_device_rendered_size(1.2, 0.8, [])
        _, h_with_ports = estimate_device_rendered_size(1.2, 0.8, ["Gi1", "Gi2"])
        self.assertGreaterEqual(h_with_ports, h_no_ports)

    def test_small_body_height_uses_standard_total_baseline(self):
        _, h_no_ports = estimate_device_rendered_size(1.2, 0.5, [])
        _, h_with_ports = estimate_device_rendered_size(1.2, 0.5, ["Gi1", "Gi2"])
        self.assertAlmostEqual(h_no_ports, DEVICE_STANDARD_TOTAL_HEIGHT_PX / UNIT_PX)
        expected_with_ports_px = (PORT_CELL_HEIGHT_PX + PORT_BAND_PADDING_Y_PX * 2) * 2 + DEVICE_LABEL_MIN_HEIGHT_PX
        self.assertAlmostEqual(h_with_ports, expected_with_ports_px / UNIT_PX)


if __name__ == "__main__":
    unittest.main()
