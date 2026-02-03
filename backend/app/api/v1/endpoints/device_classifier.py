"""
Device classification predicates.
"""

from .layout_constants import (
    MONITOR_DEVICE_KEYWORDS,
    SECURITY_DEVICE_KEYWORDS,
    SERVER_DEVICE_KEYWORDS,
    STORAGE_DEVICE_KEYWORDS,
    ROUTER_DEVICE_KEYWORDS,
    SERVER_SWITCH_KEYWORDS,
    ACCESS_SWITCH_KEYWORDS,
    DMZ_DEVICE_KEYWORDS,
    DATACENTER_AREA_KEYWORDS,
    SERVER_AREA_KEYWORDS,
    SECURITY_AREA_KEYWORDS,
    DMZ_AREA_KEYWORDS,
    normalize_text,
)


def is_monitor_device(device) -> bool:
    name = normalize_text(getattr(device, "name", ""))
    return any(keyword in name for keyword in MONITOR_DEVICE_KEYWORDS)


def is_server_device(device) -> bool:
    dtype = normalize_text(getattr(device, "device_type", ""))
    name = normalize_text(getattr(device, "name", ""))
    if dtype in {"server", "storage"}:
        return True
    if any(keyword in name for keyword in SERVER_DEVICE_KEYWORDS + STORAGE_DEVICE_KEYWORDS):
        return True
    if "sw" in name and any(keyword in name for keyword in SERVER_DEVICE_KEYWORDS + STORAGE_DEVICE_KEYWORDS):
        return True
    return False


def is_security_device(device) -> bool:
    dtype = normalize_text(getattr(device, "device_type", ""))
    name = normalize_text(getattr(device, "name", ""))
    if "waf" in name:
        return False
    if dtype == "firewall":
        return True
    return any(keyword in name for keyword in SECURITY_DEVICE_KEYWORDS)


def is_dmz_device(device) -> bool:
    name = normalize_text(getattr(device, "name", ""))
    return any(keyword in name for keyword in DMZ_DEVICE_KEYWORDS)


def is_router_device(device) -> bool:
    dtype = normalize_text(getattr(device, "device_type", ""))
    name = normalize_text(getattr(device, "name", ""))
    if dtype == "router":
        return True
    return any(keyword in name for keyword in ROUTER_DEVICE_KEYWORDS)


def is_access_switch(device) -> bool:
    dtype = normalize_text(getattr(device, "device_type", ""))
    name = normalize_text(getattr(device, "name", ""))
    if dtype == "switch" and any(keyword in name for keyword in ACCESS_SWITCH_KEYWORDS):
        return True
    return False


def is_distribution_switch(device) -> bool:
    dtype = normalize_text(getattr(device, "device_type", ""))
    name = normalize_text(getattr(device, "name", ""))
    if dtype != "switch":
        return False
    if "dist" in name or "distribution" in name:
        return True
    if "core" in name:
        return True
    if any(keyword in name for keyword in SERVER_SWITCH_KEYWORDS):
        return True
    return False


def classify_area_kind(name: str | None) -> str | None:
    label = normalize_text(name)
    if any(keyword in label for keyword in DATACENTER_AREA_KEYWORDS):
        return "datacenter"
    if any(keyword in label for keyword in SERVER_AREA_KEYWORDS):
        return "server"
    if any(keyword in label for keyword in SECURITY_AREA_KEYWORDS):
        return "security"
    if any(keyword in label for keyword in DMZ_AREA_KEYWORDS):
        return "dmz"
    if any(keyword in label for keyword in ["edge", "wan", "internet", "isp"]):
        return "edge"
    return None
