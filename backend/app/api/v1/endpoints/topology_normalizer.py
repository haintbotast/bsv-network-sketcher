"""
Topology normalization: auto-create missing areas and reassign devices.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import device as device_service
from app.services import area as area_service
from app.schemas.area import AreaCreate

from .layout_constants import (
    DATACENTER_AREA_KEYWORDS,
    SERVER_AREA_KEYWORDS,
    IT_AREA_KEYWORDS,
    normalize_text,
)
from .area_classifier import (
    infer_area_prefix,
    find_area_by_keywords,
    find_best_access_area,
)
from .device_classifier import (
    classify_area_kind,
    device_compatible_with_area_kind,
    is_monitor_device,
    is_server_device,
    is_security_device,
    is_dmz_device,
    is_router_device,
    is_access_switch,
    is_distribution_switch,
)


async def ensure_area(
    db: AsyncSession,
    project_id: str,
    areas: list,
    name: str,
    next_row: int,
) -> tuple[object, int]:
    existing = next((area for area in areas if normalize_text(area.name) == normalize_text(name)), None)
    if existing:
        return existing, next_row
    area = await area_service.create_area(
        db,
        project_id,
        AreaCreate(name=name, grid_row=next_row, grid_col=1),
    )
    areas.append(area)
    return area, next_row + 1


async def normalize_topology(
    db: AsyncSession,
    project_id: str,
    areas: list,
    devices: list,
    links: list,
) -> tuple[list, list]:
    if not areas or not devices:
        return areas, devices

    prefix = infer_area_prefix(areas)
    datacenter_area = find_area_by_keywords(areas, DATACENTER_AREA_KEYWORDS)
    server_area = find_area_by_keywords(areas, SERVER_AREA_KEYWORDS)
    it_area = find_area_by_keywords(areas, IT_AREA_KEYWORDS)

    next_row = max((area.grid_row for area in areas), default=1) + 1

    if not datacenter_area:
        has_infra = any(
            is_security_device(device) or is_router_device(device) or is_distribution_switch(device)
            for device in devices
        )
        if has_infra:
            datacenter_area, next_row = await ensure_area(
                db,
                project_id,
                areas,
                f"{prefix}Data Center" if prefix else "Data Center",
                next_row,
            )
    if not server_area:
        server_area, next_row = await ensure_area(
            db,
            project_id,
            areas,
            f"{prefix}Servers" if prefix else "Servers",
            next_row,
        )
    if not it_area:
        it_area, next_row = await ensure_area(
            db,
            project_id,
            areas,
            f"{prefix}IT" if prefix else "IT",
            next_row,
        )

    area_by_id = {area.id: area for area in areas}
    device_by_id = {device.id: device for device in devices}
    device_area_id = {device.id: device.area_id for device in devices}
    area_kind_by_id = {
        area_id: classify_area_kind(area.name) for area_id, area in area_by_id.items()
    }
    neighbor_area_index: dict[str, dict[str, int]] = {}
    for link in links:
        from_id = getattr(link, "from_device_id", None)
        to_id = getattr(link, "to_device_id", None)
        if not from_id or not to_id:
            continue
        from_area = device_area_id.get(from_id)
        to_area = device_area_id.get(to_id)
        if not from_area or not to_area:
            continue
        neighbor_area_index.setdefault(from_id, {})
        neighbor_area_index.setdefault(to_id, {})
        neighbor_area_index[from_id][to_area] = neighbor_area_index[from_id].get(to_area, 0) + 1
        neighbor_area_index[to_id][from_area] = neighbor_area_index[to_id].get(from_area, 0) + 1
    updated = False

    for device in devices:
        current_area = area_by_id.get(device.area_id)
        area_kind = classify_area_kind(current_area.name if current_area else None)
        target_area = None

        # Guard: nếu device đã ở area có kind phù hợp → không di chuyển
        if device_compatible_with_area_kind(device, area_kind):
            continue

        if is_monitor_device(device):
            target_area = it_area
        elif is_server_device(device):
            target_area = server_area
        elif is_access_switch(device):
            target_area = find_best_access_area(areas, device.name)
            if not target_area:
                neighbors = neighbor_area_index.get(device.id, {})
                if neighbors:
                    sorted_neighbors = sorted(
                        neighbors.items(),
                        key=lambda item: item[1],
                        reverse=True,
                    )
                    for area_id, _count in sorted_neighbors:
                        kind = area_kind_by_id.get(area_id)
                        if kind not in {"datacenter", "server"}:
                            target_area = area_by_id.get(area_id)
                            break
        elif datacenter_area and (
            is_security_device(device)
            or is_router_device(device)
            or is_distribution_switch(device)
            or is_dmz_device(device)
            or "core" in normalize_text(getattr(device, "name", ""))
        ):
            target_area = datacenter_area
        elif datacenter_area and area_kind == "datacenter":
            target_area = None

        if target_area and device.area_id != target_area.id:
            device.area_id = target_area.id
            updated = True

    if updated:
        await db.commit()

    # Chỉ xóa area trống nếu do normalizer tạo ra (không xóa area gốc của user/template)
    normalizer_area_names = {
        normalize_text(f"{prefix}Data Center" if prefix else "Data Center"),
        normalize_text(f"{prefix}Servers" if prefix else "Servers"),
        normalize_text(f"{prefix}IT" if prefix else "IT"),
    }
    area_ids_in_use = {device.area_id for device in devices}
    removed = False
    for area in list(area_by_id.values()):
        if area.id not in area_ids_in_use and normalize_text(area.name) in normalizer_area_names:
            await db.delete(area)
            removed = True
    if removed:
        await db.commit()

    areas = await area_service.get_areas(db, project_id)
    devices = await device_service.get_devices(db, project_id)
    return areas, devices
