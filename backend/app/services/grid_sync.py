"""Hàm tiện ích đồng bộ hình học DB và grid_range."""

from __future__ import annotations

from app.services.grid_excel import (
    GRID_CELL_UNITS,
    excel_range_to_rect_units,
    parse_excel_range,
    rect_units_to_excel_range,
)


def _safe_float(value, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def sync_device_grid_from_geometry(device, *, default_width: float, default_height: float) -> None:
    """Đồng bộ grid_range của device theo position/size hiện tại."""
    x = _safe_float(getattr(device, "position_x", None), 0.0)
    y = _safe_float(getattr(device, "position_y", None), 0.0)
    width = _safe_float(getattr(device, "width", None), default_width)
    height = _safe_float(getattr(device, "height", None), default_height)
    grid_range = rect_units_to_excel_range(x, y, width, height)
    rect = excel_range_to_rect_units(grid_range)
    device.position_x = rect["x"]
    device.position_y = rect["y"]
    device.width = rect["width"]
    device.height = rect["height"]
    device.grid_range = grid_range


def sync_area_grid_from_geometry(
    area,
    *,
    default_width: float,
    default_height: float,
    update_grid_index: bool = False,
) -> None:
    """Đồng bộ area theo position/size; có thể tùy chọn cập nhật grid_row/grid_col."""
    fallback_col = max(1, int(getattr(area, "grid_col", 1) or 1))
    fallback_row = max(1, int(getattr(area, "grid_row", 1) or 1))
    x = _safe_float(getattr(area, "position_x", None), (fallback_col - 1) * GRID_CELL_UNITS)
    y = _safe_float(getattr(area, "position_y", None), (fallback_row - 1) * GRID_CELL_UNITS)
    width = _safe_float(getattr(area, "width", None), default_width)
    height = _safe_float(getattr(area, "height", None), default_height)
    grid_range = rect_units_to_excel_range(x, y, width, height)
    rect = excel_range_to_rect_units(grid_range)
    area.position_x = rect["x"]
    area.position_y = rect["y"]
    area.width = rect["width"]
    area.height = rect["height"]
    area.grid_range = grid_range
    if update_grid_index:
        col_start, row_start, _col_end, _row_end = parse_excel_range(grid_range)
        area.grid_col = col_start
        area.grid_row = row_start
