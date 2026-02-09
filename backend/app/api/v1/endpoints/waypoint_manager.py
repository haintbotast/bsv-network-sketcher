"""
Waypoint area creation and management for inter-area links.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.layout import AreaLayout
from app.services.grid_sync import sync_area_grid_from_geometry


def rect_bounds(layout: AreaLayout) -> tuple[float, float, float, float]:
    left = layout.x
    top = layout.y
    right = layout.x + layout.width
    bottom = layout.y + layout.height
    return left, top, right, bottom


def point_in_rect(px: float, py: float, rect: tuple[float, float, float, float]) -> bool:
    left, top, right, bottom = rect
    return left <= px <= right and top <= py <= bottom


def compute_waypoint_center(
    la: AreaLayout,
    lb: AreaLayout,
    wp_width: float,
    wp_height: float,
    clearance: float = 0.15,
) -> tuple[float, float]:
    left_a, top_a, right_a, bottom_a = rect_bounds(la)
    left_b, top_b, right_b, bottom_b = rect_bounds(lb)

    overlap_x = min(right_a, right_b) - max(left_a, left_b)
    overlap_y = min(bottom_a, bottom_b) - max(top_a, top_b)
    horizontal_gap = max(0.0, max(left_a, left_b) - min(right_a, right_b))
    vertical_gap = max(0.0, max(top_a, top_b) - min(bottom_a, bottom_b))

    if right_a <= left_b:
        cx = (right_a + left_b) / 2
    elif right_b <= left_a:
        cx = (right_b + left_a) / 2
    else:
        cx = (max(left_a, left_b) + min(right_a, right_b)) / 2

    if bottom_a <= top_b:
        cy = (bottom_a + top_b) / 2
    elif bottom_b <= top_a:
        cy = (bottom_b + top_a) / 2
    else:
        cy = (max(top_a, top_b) + min(bottom_a, bottom_b)) / 2

    acx = (left_a + right_a) / 2
    acy = (top_a + bottom_a) / 2
    bcx = (left_b + right_b) / 2
    bcy = (top_b + bottom_b) / 2
    dx = bcx - acx
    dy = bcy - acy

    # Khoảng trống giữa 2 area quá hẹp thì đẩy waypoint ra phía ngoài để tránh chen vào object.
    if horizontal_gap > 0 and horizontal_gap < (wp_width + clearance * 2):
        cy = max(bottom_a, bottom_b) + wp_height / 2 + clearance if dy >= 0 else min(top_a, top_b) - wp_height / 2 - clearance
    if vertical_gap > 0 and vertical_gap < (wp_height + clearance * 2):
        cx = max(right_a, right_b) + wp_width / 2 + clearance if dx >= 0 else min(left_a, left_b) - wp_width / 2 - clearance

    if overlap_x > 0 and overlap_y > 0:
        if abs(dx) >= abs(dy):
            if dx >= 0:
                cx = max(right_a, right_b) + wp_width / 2 + clearance
            else:
                cx = min(left_a, left_b) - wp_width / 2 - clearance
            cy = (acy + bcy) / 2
        else:
            if dy >= 0:
                cy = max(bottom_a, bottom_b) + wp_height / 2 + clearance
            else:
                cy = min(top_a, top_b) - wp_height / 2 - clearance
            cx = (acx + bcx) / 2

    if point_in_rect(cx, cy, (left_a, top_a, right_a, bottom_a)) or point_in_rect(cx, cy, (left_b, top_b, right_b, bottom_b)):
        if abs(dx) >= abs(dy):
            if dx >= 0:
                cx = max(right_a, right_b) + wp_width / 2 + clearance
            else:
                cx = min(left_a, left_b) - wp_width / 2 - clearance
            cy = (acy + bcy) / 2
        else:
            if dy >= 0:
                cy = max(bottom_a, bottom_b) + wp_height / 2 + clearance
            else:
                cy = min(top_a, top_b) - wp_height / 2 - clearance
            cx = (acx + bcx) / 2

    return cx, cy


async def create_or_update_waypoint_areas(
    db: AsyncSession,
    project_id: str,
    response: dict,
    areas: list,
    links: list,
    devices: list,
) -> None:
    """Tạo/cập nhật waypoint areas cho inter-area links."""
    import json
    from sqlalchemy import select
    from app.db.models import Area, generate_uuid

    # Build device→area map
    device_area = {d.id: d.area_id for d in devices if d.area_id}
    area_name_map = {a.id: a.name for a in areas}

    # Tìm unique inter-area pairs
    inter_pair_counts: dict[tuple[str, str], int] = {}
    for link in links:
        fa = device_area.get(link.from_device_id)
        ta = device_area.get(link.to_device_id)
        if fa and ta and fa != ta:
            pair = tuple(sorted([fa, ta]))
            inter_pair_counts[pair] = inter_pair_counts.get(pair, 0) + 1

    if not inter_pair_counts:
        return

    # Area layout lookup (từ compute_layout_l1)
    area_layouts = response.get("areas") or []
    area_layout_map = {a.id: a for a in area_layouts}

    # Load existing waypoints (idempotency)
    existing_result = await db.execute(
        select(Area).where(Area.project_id == project_id, Area.name.like("%_wp_"))
    )
    existing_wp = {a.name: a for a in existing_result.scalars().all()}

    wp_style = json.dumps({
        "fill_color_rgb": [245, 245, 245],
        "stroke_color_rgb": [180, 180, 180],
        "stroke_width": 0.5,
    })

    for (aid_a, aid_b), link_count in inter_pair_counts.items():
        names = sorted([area_name_map.get(aid_a, ""), area_name_map.get(aid_b, "")])
        wp_name = f"{names[0]}_{names[1]}_wp_"

        la = area_layout_map.get(aid_a)
        lb = area_layout_map.get(aid_b)
        if not la or not lb:
            continue

        density = max(1, int(link_count))
        wp_width = min(1.6, 0.6 + max(0, density - 1) * 0.08)
        wp_height = min(1.0, 0.4 + max(0, density - 1) * 0.05)
        wp_clearance = 0.15 + min(0.35, max(0, density - 1) * 0.03)

        # Waypoint đặt ở hành lang giữa 2 area (ưu tiên giữa biên)
        center_x, center_y = compute_waypoint_center(la, lb, wp_width, wp_height, clearance=wp_clearance)
        mid_x = center_x - wp_width / 2
        mid_y = center_y - wp_height / 2

        if wp_name in existing_wp:
            wp = existing_wp[wp_name]
            wp.position_x = mid_x
            wp.position_y = mid_y
            wp.width = wp_width
            wp.height = wp_height
            wp.grid_row = 99
            wp.grid_col = 99
            sync_area_grid_from_geometry(
                wp,
                default_width=wp_width,
                default_height=wp_height,
                update_grid_index=False,
            )
            wp_id = wp.id
        else:
            wp_id = generate_uuid()
            wp = Area(
                id=wp_id,
                project_id=project_id,
                name=wp_name,
                grid_row=99,
                grid_col=99,
                position_x=mid_x,
                position_y=mid_y,
                width=wp_width,
                height=wp_height,
                style_json=wp_style,
            )
            sync_area_grid_from_geometry(
                wp,
                default_width=wp_width,
                default_height=wp_height,
                update_grid_index=False,
            )
            db.add(wp)

        area_layouts.append(AreaLayout(
            id=wp_id, name=wp_name, x=mid_x, y=mid_y, width=wp_width, height=wp_height,
        ))

    await db.flush()
