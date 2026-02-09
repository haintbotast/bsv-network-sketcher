from app.services.grid_excel import (
    GRID_CELL_UNITS,
    excel_range_to_rect_units,
    normalize_excel_range,
    rect_units_to_excel_range,
)


def test_normalize_excel_range() -> None:
    assert normalize_excel_range("b2:a1") == "A1:B2"
    assert normalize_excel_range("c7") == "C7"


def test_excel_range_to_rect_units() -> None:
    rect = excel_range_to_rect_units("A1:B2")
    assert rect["x"] == 0
    assert rect["y"] == 0
    assert rect["width"] == 2 * GRID_CELL_UNITS
    assert rect["height"] == 2 * GRID_CELL_UNITS


def test_rect_units_to_excel_range_roundtrip() -> None:
    grid = rect_units_to_excel_range(0.5, 0.75, 1.0, 0.5)
    assert grid == "C4:F5"
