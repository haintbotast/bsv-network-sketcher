"""
Layout constants and keyword dictionaries.
"""

import re

AREA_PREFIX_RE = re.compile(r"^([A-Za-z0-9]{2,6})(\s*-\s*)")
SECURITY_AREA_KEYWORDS = ["security", "firewall", "fw", "ids", "ips", "soc"]
SERVER_AREA_KEYWORDS = ["server", "servers", "storage", "nas", "san"]
DMZ_AREA_KEYWORDS = ["dmz", "proxy"]
DATACENTER_AREA_KEYWORDS = ["datacenter", "data center", "dc"]

SECURITY_DEVICE_KEYWORDS = ["firewall", "fw", "ids", "ips", "vpn", "security"]
ROUTER_DEVICE_KEYWORDS = ["router", "rtr"]
SERVER_DEVICE_KEYWORDS = ["server", "srv", "app", "web", "db", "backup"]
STORAGE_DEVICE_KEYWORDS = ["storage", "nas", "san"]
MONITOR_DEVICE_KEYWORDS = ["monitor", "monitoring", "noc", "nms"]
SERVER_SWITCH_KEYWORDS = ["server", "srv", "storage", "nas"]
ACCESS_SWITCH_KEYWORDS = ["access", "acc"]
DMZ_DEVICE_KEYWORDS = ["dmz", "waf", "proxy"]

CLOUD_AREA_KEYWORDS = ["cloud", "saas", "paas", "iaas"]
EDGE_AREA_KEYWORDS = ["edge", "wan", "internet", "isp", "branch"]
VPN_AREA_KEYWORDS = ["vpn", "tunnel", "ipsec"]
ACCESS_AREA_KEYWORDS = ["access", "floor", "department", "dept"]
MONITOR_AREA_KEYWORDS = ["monitor", "monitoring", "noc", "nms", "it"]

DEPT_AREA_KEYWORDS = ["department", "dept"]
PROJECT_AREA_KEYWORDS = ["project", "proj"]
IT_AREA_KEYWORDS = ["it"]
HO_AREA_KEYWORDS = ["head office", "hq", "office", "headquarter", "headquarters"]

# UI uses 120px per logical unit (inch) when mapping to canvas.
UNIT_PX = 120.0
LABEL_CHAR_WIDTH_PX = 6.0
LABEL_PADDING_PX = 8.0
LABEL_MIN_WIDTH_PX = 24.0
LABEL_HEIGHT_PX = 16.0
DEFAULT_DEVICE_WIDTH = 1.2
DEFAULT_DEVICE_HEIGHT = 0.8

# Port band dimensions – mirror frontend CanvasStage.vue constants
PORT_CELL_MIN_WIDTH_PX = 30.0
PORT_CELL_HEIGHT_PX = 18.0
PORT_CELL_GAP_PX = 2.0
PORT_BAND_PADDING_X_PX = 6.0
PORT_BAND_PADDING_Y_PX = 4.0
PORT_FONT_SIZE_PX = 10.0
PORT_CELL_TEXT_PADDING_PX = 10.0
DEVICE_LABEL_MIN_HEIGHT_PX = 30.0
DEVICE_MIN_WIDTH_PX = 96.0


def normalize_text(text: str | None) -> str:
    """Normalize text for classification (lowercase, strip)."""
    return (text or "").strip().lower()
