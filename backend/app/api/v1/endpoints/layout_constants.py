"""
Layout constants and keyword dictionaries.
"""

import re

AREA_PREFIX_RE = re.compile(r"^([A-Za-z0-9]{2,6})(\s*-\s*)")
SECURITY_AREA_KEYWORDS = ["security", "firewall", "fw", "ids", "ips", "vpn", "soc"]
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
DEFAULT_DEVICE_HEIGHT = 0.5


def normalize_text(text: str | None) -> str:
    """Normalize text for classification (lowercase, strip)."""
    return (text or "").strip().lower()
