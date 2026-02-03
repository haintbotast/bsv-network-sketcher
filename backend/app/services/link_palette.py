"""Bảng màu link theo purpose (đồng bộ UI/PPTX)."""

from __future__ import annotations

from typing import Dict, Tuple

DEFAULT_LINK_COLOR_RGB: Tuple[int, int, int] = (43, 42, 40)

LINK_PURPOSE_COLORS_RGB: Dict[str, Tuple[int, int, int]] = {
    "DEFAULT": DEFAULT_LINK_COLOR_RGB,
    "INTERNET": (231, 76, 60),
    "WAN": (230, 126, 34),
    "DMZ": (241, 196, 15),
    "LAN": (39, 174, 96),
    "MGMT": (41, 128, 185),
    "HA": (22, 160, 133),
    "STORAGE": (26, 188, 156),
    "BACKUP": (127, 140, 141),
    "VPN": (155, 89, 182),
    "UPLINK": (230, 126, 34),
    "INTER-AREA": (230, 126, 34),
    "INTER_AREA": (230, 126, 34),
}


def normalize_purpose(purpose: str | None) -> str:
    if not purpose:
        return "DEFAULT"
    return purpose.strip().upper()


def get_link_color_rgb(purpose: str | None) -> Tuple[int, int, int]:
    key = normalize_purpose(purpose)
    return LINK_PURPOSE_COLORS_RGB.get(key, DEFAULT_LINK_COLOR_RGB)


def get_link_palette_rgb() -> Dict[str, Tuple[int, int, int]]:
    return dict(LINK_PURPOSE_COLORS_RGB)
