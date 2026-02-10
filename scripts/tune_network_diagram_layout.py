#!/usr/bin/env python3
"""Tinh chinh bo cuc Network diagram trong DB dev de bam mau PDF page 1."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.grid_excel import excel_range_to_rect_units, rect_units_to_excel_range


@dataclass
class Box:
    x: float
    y: float
    width: float
    height: float


AREA_BOXES: dict[str, Box] = {
    "Edge-CH": Box(0.5, 0.75, 8.75, 6.75),
    "VPN-Cloud": Box(10.0, 0.75, 11.75, 5.5),
    "Security-TK": Box(11.0, 7.5, 8.75, 8.25),
    "Server": Box(22.0, 8.75, 17.75, 6.0),
    "Core": Box(9.5, 16.75, 11.75, 5.75),
    "Distribution": Box(8.5, 23.5, 14.75, 4.0),
    "Access-HTM": Box(23.75, 23.5, 4.5, 4.75),
    "Access-3F-PMJ": Box(0.5, 29.0, 10.75, 5.0),
    "Access-3F-Rakuma": Box(12.25, 29.0, 5.25, 4.75),
    "Access-KF-SODA-SQEX": Box(23.5, 29.0, 5.25, 4.75),
    "Access-3F-SCSJ": Box(2.0, 35.0, 5.25, 4.75),
    "Access-KF-CTCT": Box(12.25, 35.0, 5.25, 4.75),
    "Access-3F-BackOffice": Box(18.0, 35.0, 16.25, 4.75),
    "Access-KF-BackOffice": Box(34.75, 35.0, 11.75, 5.0),
}

AREA_ROWS: dict[str, list[list[str]]] = {
    "Edge-CH": [
        ["CH-BAT-1", "CH-BAT-2", "TK-XX-1", "TK-XX-2"],
        ["CH-FW1", "CH-FW2"],
        ["EDR-CH-1", "EDR-CH-2"],
    ],
    "VPN-Cloud": [
        ["CMC-VPN", "CMC"],
        ["Aruba Central", "Forti Cloud", "Office365-1", "Office365-2"],
    ],
    "Security-TK": [
        ["TK-FW1", "TK-FW2"],
        ["TK-CMC-SS"],
        ["SmartSensor"],
    ],
    "Server": [
        ["TK-SV1", "TK-SV2"],
        ["ESX1-HP", "ESX2-HP", "NAS-1"],
        ["AD-1", "AD-2", "VPN-SRV"],
    ],
    "Core": [
        ["TK-CR1", "TK-CR2"],
        ["TK-ICT1"],
    ],
    "Distribution": [
        ["YH-DS1", "YH-DS2"],
    ],
    "Access-HTM": [
        ["TK-HTH-1", "TK-HTH-2"],
        ["PC-HTH-1", "PC-HTH-2"],
    ],
    "Access-3F-PMJ": [
        ["YH-PMJ-1", "YH-PMJ-2", "YH-PMJ-3"],
        ["AP-PMJ-1", "AP-PMJ-2", "PC-PMJ-1", "PC-PMJ-2", "PC-PMJ-3"],
    ],
    "Access-3F-Rakuma": [
        ["YH-Rak-1", "YH-Rak-2"],
        ["AP-Rak-1", "PC-Rak-1"],
    ],
    "Access-KF-SODA-SQEX": [
        ["YH-SQ-SO-1", "YH-SQ-SO-2"],
        ["AP-SQ-1", "PC-SQ-1"],
    ],
    "Access-3F-SCSJ": [
        ["YH-SCSJ-2"],
        ["AP-SCSJ-1", "PC-SCSJ-1"],
    ],
    "Access-KF-CTCT": [
        ["YH-CTCT-1", "YH-CTCT-2"],
        ["AP-CTCT-1", "PC-CTCT-1"],
    ],
    "Access-3F-BackOffice": [
        ["YH-BO-3F-1"],
        ["AP-BO-3F-1", "AP-BO-3F-2", "PC-BO-3F-1", "PC-BO-3F-2", "PC-BO-3F-3"],
    ],
    "Access-KF-BackOffice": [
        ["YH-BO-KF-1", "YH-BO-KF-2", "YH-BO-KF-3"],
        ["AP-BO-KF-1", "AP-BO-KF-2", "PC-BO-KF-1", "PC-BO-KF-2", "PC-BO-KF-3"],
    ],
}

AREA_PADDING: dict[str, tuple[float, float, float, float]] = {
    "default": (0.9, 0.9, 0.9, 0.9),  # left, right, top, bottom
    "Security-TK": (1.0, 1.0, 0.95, 0.95),
    "Core": (1.0, 1.0, 0.95, 0.95),
    "Server": (1.0, 1.0, 0.95, 0.95),
    "Edge-CH": (0.95, 0.95, 0.9, 0.9),
    "Access-3F-BackOffice": (0.85, 0.85, 0.85, 0.85),
    "Access-KF-BackOffice": (0.85, 0.85, 0.85, 0.85),
}

# Fine-tune cho cac node cot song song chinh (Security -> Core -> Distribution).
OVERRIDE_DEVICE_XY: dict[str, tuple[float, float]] = {
    "TK-FW1": (11.75, 8.9),
    "TK-FW2": (16.0, 8.9),
    "TK-CMC-SS": (12.75, 11.6),
    "SmartSensor": (12.75, 14.0),
    "TK-CR1": (11.5, 17.85),
    "TK-CR2": (16.0, 17.85),
    "TK-ICT1": (13.75, 20.8),
    "YH-DS1": (11.5, 24.5),
    "YH-DS2": (16.0, 24.5),
    "TK-SV1": (22.8, 9.8),
    "TK-SV2": (26.2, 9.8),
    "CMC-VPN": (10.75, 1.8),
    "CMC": (14.0, 1.8),
}


def normalize_rect(x: float, y: float, width: float, height: float) -> dict[str, float | str]:
    grid_range = rect_units_to_excel_range(x, y, width, height)
    rect = excel_range_to_rect_units(grid_range)
    rect["grid_range"] = grid_range
    return rect


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def row_positions(
    box: Box,
    rows: list[list[str]],
    pad_left: float,
    pad_right: float,
    pad_top: float,
    pad_bottom: float,
) -> dict[str, tuple[float, float]]:
    positions: dict[str, tuple[float, float]] = {}
    row_count = len(rows)
    usable_h = max(0.2, box.height - pad_top - pad_bottom)
    if row_count <= 1:
        y_centers = [box.y + pad_top + usable_h / 2]
    else:
        y_centers = [
            box.y + pad_top + (usable_h * i / (row_count - 1))
            for i in range(row_count)
        ]

    usable_w = max(0.2, box.width - pad_left - pad_right)
    for ri, names in enumerate(rows):
        if not names:
            continue
        if len(names) == 1:
            x_centers = [box.x + pad_left + usable_w / 2]
        else:
            x_centers = [
                box.x + pad_left + (usable_w * i / (len(names) - 1))
                for i in range(len(names))
            ]
        for name, x in zip(names, x_centers):
            positions[name] = (x, y_centers[ri])
    return positions


def compute_waypoint_center(
    a: Box,
    b: Box,
    wp_width: float,
    wp_height: float,
    clearance: float,
) -> tuple[float, float]:
    left_a, top_a, right_a, bottom_a = a.x, a.y, a.x + a.width, a.y + a.height
    left_b, top_b, right_b, bottom_b = b.x, b.y, b.x + b.width, b.y + b.height

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

    if horizontal_gap > 0 and horizontal_gap < (wp_width + clearance * 2):
        cy = max(bottom_a, bottom_b) + wp_height / 2 + clearance if dy >= 0 else min(top_a, top_b) - wp_height / 2 - clearance
    if vertical_gap > 0 and vertical_gap < (wp_height + clearance * 2):
        cx = max(right_a, right_b) + wp_width / 2 + clearance if dx >= 0 else min(left_a, left_b) - wp_width / 2 - clearance

    if overlap_x > 0 and overlap_y > 0:
        if abs(dx) >= abs(dy):
            cx = max(right_a, right_b) + wp_width / 2 + clearance if dx >= 0 else min(left_a, left_b) - wp_width / 2 - clearance
            cy = (acy + bcy) / 2
        else:
            cy = max(bottom_a, bottom_b) + wp_height / 2 + clearance if dy >= 0 else min(top_a, top_b) - wp_height / 2 - clearance
            cx = (acx + bcx) / 2

    in_a = left_a <= cx <= right_a and top_a <= cy <= bottom_a
    in_b = left_b <= cx <= right_b and top_b <= cy <= bottom_b
    if in_a or in_b:
        if abs(dx) >= abs(dy):
            cx = max(right_a, right_b) + wp_width / 2 + clearance if dx >= 0 else min(left_a, left_b) - wp_width / 2 - clearance
            cy = (acy + bcy) / 2
        else:
            cy = max(bottom_a, bottom_b) + wp_height / 2 + clearance if dy >= 0 else min(top_a, top_b) - wp_height / 2 - clearance
            cx = (acx + bcx) / 2

    return cx, cy


def tune_layout(db_path: Path, project_name: str, dry_run: bool) -> None:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("SELECT id FROM projects WHERE name = ?", (project_name,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Khong tim thay project '{project_name}'")
    project_id = row["id"]

    cur.execute(
        """
        SELECT id, name, grid_row, grid_col, position_x, position_y, width, height
        FROM areas
        WHERE project_id = ? AND name NOT LIKE '%_wp_'
        """,
        (project_id,),
    )
    areas = {r["name"]: dict(r) for r in cur.fetchall()}
    missing_areas = sorted(set(AREA_BOXES) - set(areas))
    if missing_areas:
        raise RuntimeError(f"Thieu area trong DB: {missing_areas}")

    for area_name, box in AREA_BOXES.items():
        rect = normalize_rect(box.x, box.y, box.width, box.height)
        area = areas[area_name]
        area["position_x"] = rect["x"]
        area["position_y"] = rect["y"]
        area["width"] = rect["width"]
        area["height"] = rect["height"]
        area["grid_range"] = rect["grid_range"]
        if not dry_run:
            cur.execute(
                """
                UPDATE areas
                SET position_x = ?, position_y = ?, width = ?, height = ?, grid_range = ?
                WHERE id = ?
                """,
                (
                    area["position_x"],
                    area["position_y"],
                    area["width"],
                    area["height"],
                    area["grid_range"],
                    area["id"],
                ),
            )

    cur.execute(
        """
        SELECT d.id, d.name, d.area_id, d.position_x, d.position_y, d.width, d.height, a.name AS area_name
        FROM devices d
        JOIN areas a ON a.id = d.area_id
        WHERE d.project_id = ?
        """,
        (project_id,),
    )
    devices = {r["name"]: dict(r) for r in cur.fetchall()}

    planned_positions: dict[str, tuple[float, float]] = {}
    for area_name, rows in AREA_ROWS.items():
        box = AREA_BOXES[area_name]
        pad = AREA_PADDING.get(area_name, AREA_PADDING["default"])
        area_positions = row_positions(box, rows, *pad)
        planned_positions.update(area_positions)

    # Apply final override positions for key nodes.
    planned_positions.update(OVERRIDE_DEVICE_XY)

    missing_devices = sorted(set(devices) - set(planned_positions))
    if missing_devices:
        print("[WARN] Device chua duoc dinh vi rieng, giu nguyen toa do:", ", ".join(missing_devices))

    for name, dev in devices.items():
        target = planned_positions.get(name)
        if not target:
            continue
        tx, ty = target
        width = float(dev["width"] or 1.2)
        height = float(dev["height"] or 0.5)
        area_box = AREA_BOXES[dev["area_name"]]

        tx = clamp(tx, area_box.x + 0.2, area_box.x + area_box.width - width - 0.2)
        ty = clamp(ty, area_box.y + 0.2, area_box.y + area_box.height - height - 0.2)
        rect = normalize_rect(tx, ty, width, height)

        if not dry_run:
            cur.execute(
                """
                UPDATE devices
                SET position_x = ?, position_y = ?, width = ?, height = ?, grid_range = ?
                WHERE id = ?
                """,
                (
                    rect["x"],
                    rect["y"],
                    rect["width"],
                    rect["height"],
                    rect["grid_range"],
                    dev["id"],
                ),
            )

    # Rebuild waypoint areas based on current inter-area links.
    cur.execute(
        """
        SELECT id, name
        FROM areas
        WHERE project_id = ?
        """,
        (project_id,),
    )
    area_id_to_name = {r["id"]: r["name"] for r in cur.fetchall()}
    non_wp_ids = {aid for aid, n in area_id_to_name.items() if not n.endswith("_wp_")}

    cur.execute(
        """
        SELECT id, area_id
        FROM devices
        WHERE project_id = ?
        """,
        (project_id,),
    )
    device_to_area = {r["id"]: r["area_id"] for r in cur.fetchall()}

    cur.execute(
        """
        SELECT from_device_id, to_device_id
        FROM l1_links
        WHERE project_id = ?
        """,
        (project_id,),
    )
    pair_counts: dict[tuple[str, str], int] = {}
    for r in cur.fetchall():
        fa = device_to_area.get(r["from_device_id"])
        ta = device_to_area.get(r["to_device_id"])
        if not fa or not ta or fa == ta:
            continue
        if fa not in non_wp_ids or ta not in non_wp_ids:
            continue
        key = tuple(sorted((fa, ta)))
        pair_counts[key] = pair_counts.get(key, 0) + 1

    if not dry_run:
        cur.execute(
            "DELETE FROM areas WHERE project_id = ? AND name LIKE '%_wp_'",
            (project_id,),
        )

    wp_style = json.dumps(
        {
            "fill_color_rgb": [245, 245, 245],
            "stroke_color_rgb": [180, 180, 180],
            "stroke_width": 0.5,
        }
    )

    area_boxes_by_id: dict[str, Box] = {}
    for name, area in areas.items():
        area_boxes_by_id[area["id"]] = Box(
            float(area["position_x"]),
            float(area["position_y"]),
            float(area["width"]),
            float(area["height"]),
        )

    wp_created = 0
    for (aid_a, aid_b), link_count in sorted(pair_counts.items()):
        name_a = area_id_to_name.get(aid_a, "")
        name_b = area_id_to_name.get(aid_b, "")
        if not name_a or not name_b:
            continue
        wp_name = "_".join(sorted([name_a, name_b])) + "_wp_"

        density = max(1, int(link_count))
        wp_width = min(1.6, 0.6 + max(0, density - 1) * 0.08)
        wp_height = min(1.0, 0.4 + max(0, density - 1) * 0.05)
        wp_clearance = 0.15 + min(0.35, max(0, density - 1) * 0.03)

        box_a = area_boxes_by_id[aid_a]
        box_b = area_boxes_by_id[aid_b]
        cx, cy = compute_waypoint_center(box_a, box_b, wp_width, wp_height, wp_clearance)
        wx = cx - wp_width / 2
        wy = cy - wp_height / 2
        rect = normalize_rect(wx, wy, wp_width, wp_height)

        wp_created += 1
        if not dry_run:
            cur.execute(
                """
                INSERT INTO areas (
                    id, project_id, name, grid_row, grid_col, grid_range,
                    position_x, position_y, width, height, style_json, created_at
                ) VALUES (?, ?, ?, 99, 99, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    str(uuid.uuid4()),
                    project_id,
                    wp_name,
                    rect["grid_range"],
                    rect["x"],
                    rect["y"],
                    rect["width"],
                    rect["height"],
                    wp_style,
                ),
            )

    if not dry_run:
        con.commit()

    cur.execute("SELECT COUNT(*) AS c FROM areas WHERE project_id = ? AND name LIKE '%_wp_'", (project_id,))
    wp_count = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) AS c FROM devices WHERE project_id = ?", (project_id,))
    dev_count = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) AS c FROM l1_links WHERE project_id = ?", (project_id,))
    link_count = cur.fetchone()["c"]

    print(f"Project: {project_name} ({project_id})")
    print(f"Dry-run: {dry_run}")
    print(f"Updated areas: {len(AREA_BOXES)}")
    print(f"Positioned devices: {len(planned_positions)} / {dev_count}")
    print(f"Waypoints: {wp_count} (created/rebuilt from {len(pair_counts)} inter-area pairs)")
    print(f"Links preserved: {link_count}")

    con.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tune Network diagram layout in SQLite DB.")
    parser.add_argument(
        "--db",
        default="/opt/bsv-ns-deploy/backend/data/network_sketcher.db",
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--project",
        default="Network diagram",
        help="Project name to tune",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print summary, do not write changes",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tune_layout(Path(args.db), args.project, args.dry_run)


if __name__ == "__main__":
    main()
