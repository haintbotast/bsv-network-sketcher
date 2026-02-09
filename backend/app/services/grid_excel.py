"""Tiện ích chuyển đổi tọa độ lưới kiểu Excel <-> hình học logic (đơn vị inch)."""

from __future__ import annotations

import math
import re

EXCEL_CELL_RE = re.compile(r"^\s*([A-Za-z]+)\s*([1-9]\d*)\s*$")
EXCEL_RANGE_RE = re.compile(
    r"^\s*([A-Za-z]+[1-9]\d*)\s*(?::\s*([A-Za-z]+[1-9]\d*)\s*)?$"
)

# Bám theo step chuẩn đang dùng ở frontend (0.25 đơn vị/inch).
GRID_CELL_UNITS = 0.25


def _col_letters_to_index(letters: str) -> int:
    value = 0
    for ch in letters.upper():
        if ch < "A" or ch > "Z":
            raise ValueError(f"Cột '{letters}' không hợp lệ.")
        value = value * 26 + (ord(ch) - ord("A") + 1)
    return value


def _col_index_to_letters(index: int) -> str:
    if index < 1:
        raise ValueError("Chỉ số cột phải >= 1.")
    out: list[str] = []
    n = index
    while n > 0:
        n -= 1
        out.append(chr(ord("A") + (n % 26)))
        n //= 26
    return "".join(reversed(out))


def parse_excel_cell(cell: str) -> tuple[int, int]:
    match = EXCEL_CELL_RE.match(cell or "")
    if not match:
        raise ValueError(f"Ô '{cell}' không hợp lệ. Ví dụ hợp lệ: A1, C12.")
    col_letters, row_text = match.groups()
    col = _col_letters_to_index(col_letters)
    row = int(row_text)
    return col, row


def format_excel_cell(col: int, row: int) -> str:
    if row < 1:
        raise ValueError("Dòng phải >= 1.")
    return f"{_col_index_to_letters(col)}{row}"


def normalize_excel_range(grid_range: str) -> str:
    match = EXCEL_RANGE_RE.match(grid_range or "")
    if not match:
        raise ValueError("Grid range không hợp lệ. Ví dụ: A1 hoặc A1:B3.")
    left, right = match.groups()
    if not right:
        right = left
    start_col, start_row = parse_excel_cell(left)
    end_col, end_row = parse_excel_cell(right)
    col_a, col_b = sorted((start_col, end_col))
    row_a, row_b = sorted((start_row, end_row))
    start = format_excel_cell(col_a, row_a)
    end = format_excel_cell(col_b, row_b)
    if start == end:
        return start
    return f"{start}:{end}"


def parse_excel_range(grid_range: str) -> tuple[int, int, int, int]:
    normalized = normalize_excel_range(grid_range)
    if ":" in normalized:
        left, right = normalized.split(":", 1)
    else:
        left = right = normalized
    start_col, start_row = parse_excel_cell(left)
    end_col, end_row = parse_excel_cell(right)
    return start_col, start_row, end_col, end_row


def excel_range_to_rect_units(grid_range: str, cell_units: float = GRID_CELL_UNITS) -> dict[str, float]:
    col_start, row_start, col_end, row_end = parse_excel_range(grid_range)
    width_cells = col_end - col_start + 1
    height_cells = row_end - row_start + 1
    return {
        "x": (col_start - 1) * cell_units,
        "y": (row_start - 1) * cell_units,
        "width": width_cells * cell_units,
        "height": height_cells * cell_units,
        "col_start": col_start,
        "row_start": row_start,
        "col_end": col_end,
        "row_end": row_end,
    }


def rect_units_to_excel_range(
    position_x: float | None,
    position_y: float | None,
    width: float | None,
    height: float | None,
    cell_units: float = GRID_CELL_UNITS,
) -> str:
    x = float(position_x or 0.0)
    y = float(position_y or 0.0)
    w = max(cell_units, float(width or cell_units))
    h = max(cell_units, float(height or cell_units))

    col_start = max(1, int(math.floor((x / cell_units) + 1e-9)) + 1)
    row_start = max(1, int(math.floor((y / cell_units) + 1e-9)) + 1)
    col_span = max(1, int(round(w / cell_units)))
    row_span = max(1, int(round(h / cell_units)))
    col_end = col_start + col_span - 1
    row_end = row_start + row_span - 1

    start = format_excel_cell(col_start, row_start)
    end = format_excel_cell(col_end, row_end)
    if start == end:
        return start
    return f"{start}:{end}"
