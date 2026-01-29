"""
Unit tests for device auto-sizing logic.
"""

import unittest

from app.services.device_sizing import compute_device_size, BASE_WIDTH, BASE_HEIGHT, TALL_HEIGHT


class DeviceSizingTests(unittest.TestCase):
    def test_zero_ports(self):
        """Device with 0 ports should have base dimensions."""
        width, height = compute_device_size(0)
        self.assertEqual(width, BASE_WIDTH)
        self.assertEqual(height, BASE_HEIGHT)

    def test_small_port_count(self):
        """Device with 8 ports should increase width moderately."""
        width, height = compute_device_size(8)
        # 8 ports * 0.03 = 0.24 inch increase
        # Expected: 1.2 + 0.24 = 1.44
        self.assertGreater(width, BASE_WIDTH)
        self.assertLess(width, 2.0)
        self.assertEqual(height, BASE_HEIGHT)  # Height stays base for <24 ports

    def test_medium_port_count(self):
        """Device with 24 ports should increase width significantly."""
        width, height = compute_device_size(24)
        # 24 ports * 0.03 = 0.72 inch increase
        # Expected: 1.2 + 0.72 = 1.92
        self.assertGreater(width, 1.5)
        self.assertLess(width, 2.5)
        self.assertEqual(height, BASE_HEIGHT)  # Height at threshold

    def test_high_port_count(self):
        """Device with 48 ports should hit max width and increase height."""
        width, height = compute_device_size(48)
        # 48 ports * 0.03 = 1.44 inch increase
        # Raw: 1.2 + 1.44 = 2.64, but clamped to 3.6 max
        self.assertGreater(width, 2.0)
        self.assertLessEqual(width, 3.6)  # Clamped to max
        self.assertEqual(height, TALL_HEIGHT)  # Height increased for >24 ports

    def test_very_high_port_count(self):
        """Device with 96 ports should hit max width and tall height."""
        width, height = compute_device_size(96)
        # 96 ports * 0.03 = 2.88 inch increase
        # Raw: 1.2 + 2.88 = 4.08, but clamped to 3.6 max
        self.assertEqual(width, 3.6)  # Max width
        self.assertEqual(height, TALL_HEIGHT)  # Tall height for high density

    def test_width_progression(self):
        """Width should increase monotonically with port count (until max)."""
        width_8, _ = compute_device_size(8)
        width_16, _ = compute_device_size(16)
        width_24, _ = compute_device_size(24)

        self.assertGreater(width_16, width_8)
        self.assertGreater(width_24, width_16)

    def test_height_threshold(self):
        """Height should increase only above 24 ports."""
        _, height_23 = compute_device_size(23)
        _, height_24 = compute_device_size(24)
        _, height_25 = compute_device_size(25)

        self.assertEqual(height_23, BASE_HEIGHT)
        self.assertEqual(height_24, BASE_HEIGHT)  # Exactly at threshold
        self.assertEqual(height_25, TALL_HEIGHT)  # Above threshold


if __name__ == "__main__":
    unittest.main()
