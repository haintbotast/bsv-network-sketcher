from app.api.v1.endpoints.waypoint_manager import compute_waypoint_center, point_in_rect, rect_bounds
from app.schemas.layout import AreaLayout


def _area(area_id: str, x: float, y: float, width: float, height: float) -> AreaLayout:
    return AreaLayout(
        id=area_id,
        name=area_id,
        x=x,
        y=y,
        width=width,
        height=height,
    )


def test_waypoint_moves_out_when_gap_too_narrow() -> None:
    area_a = _area("A", 0.0, 0.0, 4.0, 4.0)
    area_b = _area("B", 4.2, 0.0, 4.0, 4.0)

    cx, cy = compute_waypoint_center(
        area_a,
        area_b,
        wp_width=1.2,
        wp_height=0.8,
        clearance=0.4,
    )

    assert not point_in_rect(cx, cy, rect_bounds(area_a))
    assert not point_in_rect(cx, cy, rect_bounds(area_b))
    assert cy > area_a.y + area_a.height
