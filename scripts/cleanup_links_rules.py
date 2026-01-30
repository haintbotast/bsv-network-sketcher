#!/usr/bin/env python3
import argparse
import re
import sqlite3
from dataclasses import dataclass


BUSINESS_AREA_RE = re.compile(r"\b(HEAD\s*OFFICE|HQ|HO|DEPARTMENT|DEPT|PROJECT|IT)\b", re.IGNORECASE)
ACCESS_NAME_RE = re.compile(r"\bACCESS\b|\bACC\b", re.IGNORECASE)
CORE_NAME_RE = re.compile(r"\bCORE\b|SW-CORE|CORE-SW", re.IGNORECASE)
DIST_NAME_RE = re.compile(r"\bDIST\b|DISTR", re.IGNORECASE)
SERVER_NAME_RE = re.compile(r"\b(SERVER|SRV|APP|WEB|DB|NAS|SAN|STORAGE|BACKUP)\b", re.IGNORECASE)
SERVER_SWITCH_RE = re.compile(r"\b(SW|SWITCH)\b", re.IGNORECASE)
SERVER_AREA_RE = re.compile(r"\bSERVER|STORAGE\b", re.IGNORECASE)


@dataclass
class DeviceInfo:
    id: str
    name: str
    dtype: str
    area_id: str
    area_name: str


@dataclass
class LinkInfo:
    id: str
    from_device_id: str
    to_device_id: str
    created_at: str


def is_switch(device: DeviceInfo) -> bool:
    return device.dtype == "SWITCH"


def is_business_area(device: DeviceInfo) -> bool:
    return bool(BUSINESS_AREA_RE.search(device.area_name or ""))


def is_access_switch(device: DeviceInfo) -> bool:
    return is_switch(device) and bool(ACCESS_NAME_RE.search(device.name or ""))


def is_distribution_switch(device: DeviceInfo) -> bool:
    return is_switch(device) and bool(DIST_NAME_RE.search(device.name or "") or CORE_NAME_RE.search(device.name or ""))


def is_server_device(device: DeviceInfo) -> bool:
    if device.dtype in {"SERVER", "STORAGE"}:
        return True
    return bool(SERVER_NAME_RE.search(device.name or ""))


def is_server_switch(device: DeviceInfo) -> bool:
    if not is_switch(device):
        return False
    if SERVER_NAME_RE.search(device.name or "") and SERVER_SWITCH_RE.search(device.name or ""):
        return True
    if SERVER_AREA_RE.search(device.area_name or ""):
        return True
    if DIST_NAME_RE.search(device.name or "") and SERVER_NAME_RE.search(device.name or ""):
        return True
    return False


def link_invalid(a: DeviceInfo, b: DeviceInfo) -> bool:
    # Business area devices (non-access) only connect to access switch in same area
    for dev, other in ((a, b), (b, a)):
        if is_business_area(dev) and not is_access_switch(dev):
            same_area = dev.area_id == other.area_id
            if not (is_access_switch(other) and same_area):
                return True

    # Access switch uplink only to distribution, downlink only to same area
    for dev, other in ((a, b), (b, a)):
        if is_access_switch(dev):
            if is_switch(other):
                if not is_distribution_switch(other):
                    return True
            else:
                if dev.area_id != other.area_id:
                    return True

    # Server device only to server switch
    if is_server_device(a) and not is_server_switch(b):
        return True
    if is_server_device(b) and not is_server_switch(a):
        return True

    # Server switch only to server/storage or distribution
    for dev, other in ((a, b), (b, a)):
        if is_server_switch(dev):
            if is_switch(other):
                if not is_distribution_switch(other):
                    return True
            else:
                if not is_server_device(other):
                    return True

    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Cleanup L1 links to enforce new topology rules.")
    parser.add_argument("--db", required=True, help="Path to SQLite DB (network_sketcher.db)")
    parser.add_argument("--apply", action="store_true", help="Apply deletions (default: dry-run)")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    areas = {row[0]: row[1] for row in cur.execute("select id, name from areas").fetchall()}
    devices = {}
    for row in cur.execute("select id, name, device_type, area_id from devices").fetchall():
        area_name = areas.get(row[3], "")
        devices[row[0]] = DeviceInfo(id=row[0], name=row[1], dtype=(row[2] or "").upper(), area_id=row[3], area_name=area_name or "")

    links = [
        LinkInfo(id=row[0], from_device_id=row[1], to_device_id=row[2], created_at=row[3])
        for row in cur.execute("select id, from_device_id, to_device_id, created_at from l1_links").fetchall()
    ]

    invalid_links = []
    for link in links:
        a = devices.get(link.from_device_id)
        b = devices.get(link.to_device_id)
        if not a or not b:
            invalid_links.append(link.id)
            continue
        if link_invalid(a, b):
            invalid_links.append(link.id)

    remaining = [link for link in links if link.id not in set(invalid_links)]

    # Enforce single uplink for business area non-access devices
    extra_links = []
    by_device = {}
    for link in remaining:
        by_device.setdefault(link.from_device_id, []).append(link)
        by_device.setdefault(link.to_device_id, []).append(link)

    for device_id, dev_links in by_device.items():
        device = devices.get(device_id)
        if not device or not (is_business_area(device) and not is_access_switch(device)):
            continue
        if len(dev_links) <= 1:
            continue
        dev_links_sorted = sorted(dev_links, key=lambda l: (l.created_at or "", l.id))
        for extra in dev_links_sorted[1:]:
            extra_links.append(extra.id)

    delete_ids = sorted(set(invalid_links + extra_links))

    print(f"Found {len(delete_ids)} links to delete ({len(invalid_links)} rule violations, {len(extra_links)} extra uplinks).")
    if not delete_ids:
        conn.close()
        return

    if args.apply:
        cur.executemany("delete from l1_links where id = ?", [(lid,) for lid in delete_ids])
        conn.commit()
        print("Deleted.")
    else:
        print("Dry-run. Use --apply to delete.")

    conn.close()


if __name__ == "__main__":
    main()
