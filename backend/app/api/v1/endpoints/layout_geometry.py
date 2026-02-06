"""
Geometry and sizing utilities for layout computation.
"""

import math

from .layout_constants import (
    UNIT_PX,
    LABEL_CHAR_WIDTH_PX,
    LABEL_PADDING_PX,
    LABEL_MIN_WIDTH_PX,
    LABEL_HEIGHT_PX,
    PORT_CELL_MIN_WIDTH_PX,
    PORT_CELL_HEIGHT_PX,
    PORT_CELL_GAP_PX,
    PORT_BAND_PADDING_X_PX,
    PORT_BAND_PADDING_Y_PX,
    PORT_FONT_SIZE_PX,
    PORT_CELL_TEXT_PADDING_PX,
    DEVICE_LABEL_MIN_HEIGHT_PX,
    DEVICE_MIN_WIDTH_PX,
)


def safe_dim(value: float | None, fallback: float) -> float:
    try:
        return float(value) if value is not None else fallback
    except (TypeError, ValueError):
        return fallback


def compute_max_device_size(devices: list, base_width: float, base_height: float) -> tuple[float, float]:
    max_width = base_width
    max_height = base_height
    for device in devices:
        max_width = max(max_width, safe_dim(getattr(device, "width", None), base_width))
        max_height = max(max_height, safe_dim(getattr(device, "height", None), base_height))
    return max_width, max_height


def effective_node_size(
    devices: list,
    base_width: float,
    base_height: float,
    extra_width: float = 0.0,
    extra_height: float = 0.0,
) -> tuple[float, float]:
    max_width, max_height = compute_max_device_size(devices, base_width, base_height)
    return max_width + max(0.0, extra_width), max_height + max(0.0, extra_height)


def collect_device_ports(links: list, l2_assignments: list | None = None) -> dict[str, set[str]]:
    ports: dict[str, set[str]] = {}

    def add(device_id: str | None, port: str | None) -> None:
        if not device_id or not port:
            return
        cleaned = port.strip()
        if not cleaned:
            return
        ports.setdefault(device_id, set()).add(cleaned)

    for link in links:
        add(getattr(link, "from_device_id", None), getattr(link, "from_port", None))
        add(getattr(link, "to_device_id", None), getattr(link, "to_port", None))

    if l2_assignments:
        for assignment in l2_assignments:
            add(getattr(assignment, "device_id", None), getattr(assignment, "interface_name", None))

    return ports


def estimate_label_clearance(ports_by_device: dict[str, set[str]], render_tuning: dict | None) -> tuple[float, float]:
    if not ports_by_device:
        return 0.0, 0.0

    max_len = 0
    for ports in ports_by_device.values():
        for port in ports:
            max_len = max(max_len, len(port))

    if max_len <= 0:
        return 0.0, 0.0

    tuning = render_tuning or {}
    label_gap_x = float(tuning.get("label_gap_x", 8))
    label_gap_y = float(tuning.get("label_gap_y", 6))
    label_offset = float(tuning.get("port_label_offset", 12))

    label_width_px = max(max_len * LABEL_CHAR_WIDTH_PX + LABEL_PADDING_PX, LABEL_MIN_WIDTH_PX)
    label_width_px += label_gap_x + label_offset * 2
    label_height_px = LABEL_HEIGHT_PX + label_gap_y + label_offset * 2

    return label_width_px / UNIT_PX, label_height_px / UNIT_PX


def _estimate_band_width_px(ports: list[str]) -> float:
    """Estimate port band width in pixels — mirrors frontend estimateBandWidth()."""
    if not ports:
        return 0.0
    char_width = PORT_FONT_SIZE_PX * 0.62
    cells_width = sum(
        max(PORT_CELL_MIN_WIDTH_PX, math.ceil(len(p.strip()) * char_width + PORT_CELL_TEXT_PADDING_PX))
        for p in ports
    )
    gaps_width = PORT_CELL_GAP_PX * max(len(ports) - 1, 0)
    return PORT_BAND_PADDING_X_PX * 2 + cells_width + gaps_width


def estimate_device_rendered_size(
    body_width_in: float,
    body_height_in: float,
    ports: list[str],
) -> tuple[float, float]:
    """Estimate rendered device size matching frontend expandDeviceRectForPorts().

    Splits ports 50/50 (ceil) between top/bottom bands as heuristic.
    Returns (width, height) in inches.
    """
    body_width_px = body_width_in * UNIT_PX
    body_height_px = body_height_in * UNIT_PX

    if not ports:
        width_px = max(body_width_px, DEVICE_MIN_WIDTH_PX)
        height_px = max(body_height_px, DEVICE_LABEL_MIN_HEIGHT_PX)
        return width_px / UNIT_PX, height_px / UNIT_PX

    half = math.ceil(len(ports) / 2)
    side_a = ports[:half]
    side_b = ports[half:]

    band_a_width = _estimate_band_width_px(side_a)
    band_b_width = _estimate_band_width_px(side_b)

    width_px = max(body_width_px, DEVICE_MIN_WIDTH_PX, band_a_width, band_b_width)

    band_height = PORT_CELL_HEIGHT_PX + PORT_BAND_PADDING_Y_PX * 2
    body_rendered_px = max(body_height_px, DEVICE_LABEL_MIN_HEIGHT_PX)
    top_band_h = band_height if side_a else 0
    bottom_band_h = band_height if side_b else 0
    height_px = top_band_h + body_rendered_px + bottom_band_h

    return width_px / UNIT_PX, height_px / UNIT_PX
