from dataclasses import dataclass

from app.services.grid_sync import sync_area_grid_from_geometry, sync_device_grid_from_geometry


@dataclass
class DummyDevice:
    position_x: float | None
    position_y: float | None
    width: float | None
    height: float | None
    grid_range: str | None = None


@dataclass
class DummyArea:
    position_x: float | None
    position_y: float | None
    width: float | None
    height: float | None
    grid_row: int = 1
    grid_col: int = 1
    grid_range: str | None = None


def test_sync_device_grid_from_geometry() -> None:
    device = DummyDevice(
        position_x=0.5,
        position_y=0.75,
        width=1.2,
        height=0.8,
    )
    sync_device_grid_from_geometry(device, default_width=1.2, default_height=0.8)
    assert device.grid_range == "C4:G6"
    assert device.position_x == 0.5
    assert device.position_y == 0.75
    assert device.width == 1.25
    assert device.height == 0.75


def test_sync_area_grid_from_geometry_updates_row_col() -> None:
    area = DummyArea(
        position_x=1.0,
        position_y=2.0,
        width=1.75,
        height=1.5,
    )
    sync_area_grid_from_geometry(area, default_width=1.75, default_height=1.5, update_grid_index=True)
    assert area.grid_range == "E9:K14"
    assert area.grid_row == 9
    assert area.grid_col == 5


def test_sync_area_grid_from_geometry_fallback_position() -> None:
    area = DummyArea(
        position_x=None,
        position_y=None,
        width=0.5,
        height=0.5,
        grid_row=3,
        grid_col=4,
    )
    sync_area_grid_from_geometry(area, default_width=0.5, default_height=0.5, update_grid_index=True)
    assert area.grid_range == "D3:E4"
    assert area.grid_row == 3
    assert area.grid_col == 4
