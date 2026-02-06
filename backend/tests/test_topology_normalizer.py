"""
Tests cho topology normalizer: guard logic + area deletion.
"""

import unittest

from app.api.v1.endpoints.device_classifier import (
    classify_area_kind,
    device_compatible_with_area_kind,
)


class DummyDevice:
    def __init__(self, device_id: str, device_type: str, name: str, area_id: str = "") -> None:
        self.id = device_id
        self.device_type = device_type
        self.name = name
        self.area_id = area_id


class TestClassifyAreaKind(unittest.TestCase):
    def test_datacenter(self):
        self.assertEqual(classify_area_kind("Data Center"), "datacenter")
        self.assertEqual(classify_area_kind("Access-Data Center"), "datacenter")

    def test_server(self):
        self.assertEqual(classify_area_kind("Server"), "server")

    def test_security(self):
        self.assertEqual(classify_area_kind("Security Zone"), "security")
        self.assertEqual(classify_area_kind("VPN-Firewall"), "security")

    def test_cloud(self):
        self.assertEqual(classify_area_kind("Cloud Services"), "cloud")

    def test_vpn(self):
        self.assertEqual(classify_area_kind("VPN-Tunnel"), "vpn")
        # "VPN-Cloud" has both vpn and cloud keywords; cloud checked first
        self.assertEqual(classify_area_kind("VPN-Cloud"), "cloud")

    def test_edge(self):
        self.assertEqual(classify_area_kind("Edge-CH"), "edge")
        self.assertEqual(classify_area_kind("WAN Zone"), "edge")

    def test_access(self):
        self.assertEqual(classify_area_kind("Access-Floor1"), "access")

    def test_monitor(self):
        self.assertEqual(classify_area_kind("Monitoring Room"), "monitor")
        self.assertEqual(classify_area_kind("IT Operations"), "monitor")

    def test_unknown(self):
        self.assertIsNone(classify_area_kind("Custom Zone XYZ"))
        self.assertIsNone(classify_area_kind(None))


class TestDeviceCompatibleWithAreaKind(unittest.TestCase):
    """Device ở area phù hợp → không cần di chuyển."""

    def test_firewall_in_vpn_area_compatible(self):
        fw = DummyDevice("fw1", "firewall", "CMC-VPN")
        self.assertTrue(device_compatible_with_area_kind(fw, "vpn"))

    def test_firewall_in_security_area_compatible(self):
        fw = DummyDevice("fw1", "firewall", "CH-FW1")
        self.assertTrue(device_compatible_with_area_kind(fw, "security"))

    def test_firewall_in_edge_area_compatible(self):
        fw = DummyDevice("fw1", "firewall", "TK-FW1")
        self.assertTrue(device_compatible_with_area_kind(fw, "edge"))

    def test_firewall_in_cloud_area_compatible(self):
        fw = DummyDevice("fw1", "firewall", "Cloud-FW")
        self.assertTrue(device_compatible_with_area_kind(fw, "cloud"))

    def test_firewall_in_datacenter_area_compatible(self):
        fw = DummyDevice("fw1", "firewall", "DC-FW")
        self.assertTrue(device_compatible_with_area_kind(fw, "datacenter"))

    def test_firewall_in_access_area_not_compatible(self):
        fw = DummyDevice("fw1", "firewall", "FW-Floor1")
        self.assertFalse(device_compatible_with_area_kind(fw, "access"))

    def test_server_in_cloud_area_compatible(self):
        srv = DummyDevice("srv1", "server", "Aruba Central")
        self.assertTrue(device_compatible_with_area_kind(srv, "cloud"))

    def test_server_in_edge_area_compatible(self):
        srv = DummyDevice("srv1", "server", "Office365")
        self.assertTrue(device_compatible_with_area_kind(srv, "edge"))

    def test_server_in_server_area_compatible(self):
        srv = DummyDevice("srv1", "server", "App-Server")
        self.assertTrue(device_compatible_with_area_kind(srv, "server"))

    def test_server_in_security_area_compatible(self):
        srv = DummyDevice("srv1", "server", "SmartSensor")
        self.assertTrue(device_compatible_with_area_kind(srv, "security"))

    def test_server_in_unknown_area_not_compatible(self):
        srv = DummyDevice("srv1", "server", "App-Server")
        self.assertFalse(device_compatible_with_area_kind(srv, None))

    def test_router_in_edge_area_compatible(self):
        rtr = DummyDevice("rtr1", "router", "CH-BAT-1")
        self.assertTrue(device_compatible_with_area_kind(rtr, "edge"))

    def test_router_in_datacenter_area_compatible(self):
        rtr = DummyDevice("rtr1", "router", "Core-RTR")
        self.assertTrue(device_compatible_with_area_kind(rtr, "datacenter"))

    def test_router_in_access_area_not_compatible(self):
        rtr = DummyDevice("rtr1", "router", "Floor-RTR")
        self.assertFalse(device_compatible_with_area_kind(rtr, "access"))

    def test_switch_no_match_returns_false(self):
        sw = DummyDevice("sw1", "switch", "SW-Generic")
        self.assertFalse(device_compatible_with_area_kind(sw, "datacenter"))

    def test_none_area_kind_returns_false(self):
        fw = DummyDevice("fw1", "firewall", "FW1")
        self.assertFalse(device_compatible_with_area_kind(fw, None))


if __name__ == "__main__":
    unittest.main()
