"""Service cho import dữ liệu tổng hợp."""

import json
from typing import Any, Optional

from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Area,
    Device,
    DevicePort,
    InterfaceL2Assignment,
    L1Link,
    L2Segment,
    L3Address,
    PortChannel,
    Project,
    VirtualPort,
)
from app.schemas.area import AreaCreate
from app.schemas.common import ErrorDetail
from app.schemas.device import DeviceCreate
from app.schemas.import_data import ImportL2Assignment, ImportOptions, ImportResult
from app.schemas.link import L1LinkCreate
from app.schemas.l2_segment import L2SegmentCreate
from app.schemas.l3_address import L3AddressCreate
from app.schemas.port_channel import PortChannelCreate
from app.schemas.virtual_port import VirtualPortCreate


def _add_error(
    errors: list[ErrorDetail],
    *,
    entity: str,
    row: Optional[int],
    field: Optional[str],
    code: str,
    message: str,
) -> None:
    errors.append(
        ErrorDetail(
            entity=entity,
            row=row,
            field=field,
            code=code,
            message=message,
        )
    )


def _map_validation_code(entity: str, field: Optional[str]) -> str:
    if entity == "l2_segment" and field == "vlan_id":
        return "VLAN_INVALID"
    if entity == "l2_assignment" and field == "port_mode":
        return "PORT_MODE_INVALID"
    if entity == "l3_address" and field == "ip_address":
        return "IP_INVALID"
    if entity == "l1_link" and field in {"from_port", "to_port"}:
        return "PORT_FORMAT_INVALID"
    return "VALIDATION_ERROR"


def _normalize_link_key(
    from_device_id: str, from_port: str, to_device_id: str, to_port: str
) -> tuple[str, str, str, str]:
    left = (from_device_id, from_port)
    right = (to_device_id, to_port)
    if left <= right:
        return (from_device_id, from_port, to_device_id, to_port)
    return (to_device_id, to_port, from_device_id, from_port)


def _extract_channel_number(name: str) -> Optional[int]:
    import re

    match = re.search(r"(\d+)$", name)
    if not match:
        return None
    return int(match.group(1))


def _validate_virtual_port_name(name: str, interface_type: str) -> bool:
    import re

    patterns = {
        "Vlan": r"^Vlan\s*\d+$",
        "Loopback": r"^Loopback\s*\d+$",
        "Port-Channel": r"^Port-[Cc]hannel\s*\d+$",
    }
    pattern = patterns.get(interface_type)
    if not pattern:
        return False
    return re.match(pattern, name) is not None


def _validate_items(
    entity: str,
    items: list[dict[str, Any]],
    schema,
    errors: list[ErrorDetail],
) -> list[Any]:
    result = []
    for idx, item in enumerate(items):
        row = idx + 1
        try:
            result.append(schema.model_validate(item))
        except ValidationError as exc:
            for err in exc.errors():
                field = ".".join(str(p) for p in err.get("loc", [])) or None
                code = _map_validation_code(entity, field)
                _add_error(
                    errors,
                    entity=entity,
                    row=row,
                    field=field,
                    code=code,
                    message=err.get("msg", "Dữ liệu không hợp lệ"),
                )
    return result


async def _clear_project_data(db: AsyncSession, project_id: str) -> None:
    await db.execute(delete(L3Address).where(L3Address.project_id == project_id))
    await db.execute(
        delete(InterfaceL2Assignment).where(InterfaceL2Assignment.project_id == project_id)
    )
    await db.execute(delete(L2Segment).where(L2Segment.project_id == project_id))
    await db.execute(delete(PortChannel).where(PortChannel.project_id == project_id))
    await db.execute(delete(VirtualPort).where(VirtualPort.project_id == project_id))
    await db.execute(delete(L1Link).where(L1Link.project_id == project_id))
    await db.execute(delete(DevicePort).where(DevicePort.project_id == project_id))
    await db.execute(delete(Device).where(Device.project_id == project_id))
    await db.execute(delete(Area).where(Area.project_id == project_id))


async def import_project_data(
    db: AsyncSession,
    project: Project,
    payload: dict[str, Any],
    options: ImportOptions,
    mode: str,
) -> ImportResult:
    project_id = project.id
    errors: list[ErrorDetail] = []
    created = {
        "areas": 0,
        "devices": 0,
        "l1_links": 0,
        "port_channels": 0,
        "virtual_ports": 0,
        "l2_segments": 0,
        "l2_assignments": 0,
        "l3_addresses": 0,
    }
    skipped = {key: 0 for key in created.keys()}

    if not isinstance(payload, dict):
        _add_error(
            errors,
            entity="payload",
            row=None,
            field=None,
            code="VALIDATION_ERROR",
            message="payload phải là object",
        )
        return ImportResult(
            mode=mode,
            validate_only=options.validate_only,
            merge_strategy=options.merge_strategy,
            applied=False,
            created=created,
            skipped=skipped,
            errors=errors,
        )

    areas_raw = payload.get("areas") or []
    devices_raw = payload.get("devices") or []
    links_raw = payload.get("l1_links") or []
    port_channels_raw = payload.get("port_channels") or []
    virtual_ports_raw = payload.get("virtual_ports") or []
    l2_segments_raw = payload.get("l2_segments") or []
    l2_assignments_raw = payload.get("interface_l2_assignments") or []
    l3_addresses_raw = payload.get("l3_addresses") or []

    for key, value in [
        ("areas", areas_raw),
        ("devices", devices_raw),
        ("l1_links", links_raw),
        ("port_channels", port_channels_raw),
        ("virtual_ports", virtual_ports_raw),
        ("l2_segments", l2_segments_raw),
        ("interface_l2_assignments", l2_assignments_raw),
        ("l3_addresses", l3_addresses_raw),
    ]:
        if not isinstance(value, list):
            _add_error(
                errors,
                entity=key,
                row=None,
                field=None,
                code="VALIDATION_ERROR",
                message=f"{key} phải là danh sách",
            )
    if not isinstance(areas_raw, list):
        areas_raw = []
    if not isinstance(devices_raw, list):
        devices_raw = []
    if not isinstance(links_raw, list):
        links_raw = []
    if not isinstance(port_channels_raw, list):
        port_channels_raw = []
    if not isinstance(virtual_ports_raw, list):
        virtual_ports_raw = []
    if not isinstance(l2_segments_raw, list):
        l2_segments_raw = []
    if not isinstance(l2_assignments_raw, list):
        l2_assignments_raw = []
    if not isinstance(l3_addresses_raw, list):
        l3_addresses_raw = []

    area_items = _validate_items("area", areas_raw, AreaCreate, errors)
    device_items = _validate_items("device", devices_raw, DeviceCreate, errors)
    link_items = _validate_items("l1_link", links_raw, L1LinkCreate, errors)
    port_channel_items = _validate_items("port_channel", port_channels_raw, PortChannelCreate, errors)
    virtual_port_items = _validate_items("virtual_port", virtual_ports_raw, VirtualPortCreate, errors)
    l2_segment_items = _validate_items("l2_segment", l2_segments_raw, L2SegmentCreate, errors)
    l2_assignment_items = _validate_items(
        "l2_assignment", l2_assignments_raw, ImportL2Assignment, errors
    )
    l3_address_items = _validate_items("l3_address", l3_addresses_raw, L3AddressCreate, errors)

    if db.in_transaction():
        await db.rollback()
    tx = await db.begin()
    applied = False
    try:
        if options.merge_strategy == "replace":
            await _clear_project_data(db, project_id)

        area_by_name: dict[str, Area] = {}
        device_by_name: dict[str, Device] = {}
        l2_segment_by_name: dict[str, L2Segment] = {}
        l2_segment_by_vlan: dict[int, L2Segment] = {}
        port_channel_by_key: set[tuple[str, str]] = set()
        port_channel_number_by_key: set[tuple[str, int]] = set()
        virtual_port_by_key: set[tuple[str, str]] = set()
        link_keys: set[tuple[str, str, str, str]] = set()
        ports_in_use: set[tuple[str, str]] = set()
        device_port_keys: set[tuple[str, str]] = set()
        l2_assignment_keys: set[tuple[str, str]] = set()
        l3_address_keys: set[tuple[str, str, str, int]] = set()

        if options.merge_strategy == "merge":
            result = await db.execute(select(Area).where(Area.project_id == project_id))
            for area in result.scalars().all():
                area_by_name[area.name] = area

            result = await db.execute(select(Device).where(Device.project_id == project_id))
            for device in result.scalars().all():
                device_by_name[device.name] = device

            result = await db.execute(select(L2Segment).where(L2Segment.project_id == project_id))
            for segment in result.scalars().all():
                l2_segment_by_name[segment.name] = segment
                l2_segment_by_vlan[segment.vlan_id] = segment

            result = await db.execute(select(PortChannel).where(PortChannel.project_id == project_id))
            for pc in result.scalars().all():
                port_channel_by_key.add((pc.device_id, pc.name))
                port_channel_number_by_key.add((pc.device_id, pc.channel_number))

            result = await db.execute(select(VirtualPort).where(VirtualPort.project_id == project_id))
            for vp in result.scalars().all():
                virtual_port_by_key.add((vp.device_id, vp.name))

            result = await db.execute(select(L1Link).where(L1Link.project_id == project_id))
            for link in result.scalars().all():
                key = _normalize_link_key(
                    link.from_device_id,
                    link.from_port,
                    link.to_device_id,
                    link.to_port,
                )
                link_keys.add(key)
                ports_in_use.add((link.from_device_id, link.from_port))
                ports_in_use.add((link.to_device_id, link.to_port))

            result = await db.execute(select(DevicePort).where(DevicePort.project_id == project_id))
            for port in result.scalars().all():
                device_port_keys.add((port.device_id, port.name))

            result = await db.execute(
                select(InterfaceL2Assignment).where(
                    InterfaceL2Assignment.project_id == project_id
                )
            )
            for assignment in result.scalars().all():
                l2_assignment_keys.add((assignment.device_id, assignment.interface_name))

            result = await db.execute(select(L3Address).where(L3Address.project_id == project_id))
            for addr in result.scalars().all():
                l3_address_keys.add(
                    (addr.device_id, addr.interface_name, addr.ip_address, addr.prefix_length)
                )

        # Areas
        for idx, area_data in enumerate(area_items):
            row = idx + 1
            if area_data.name in area_by_name:
                if options.merge_strategy == "merge":
                    skipped["areas"] += 1
                    continue
                _add_error(
                    errors,
                    entity="area",
                    row=row,
                    field="name",
                    code="AREA_NAME_DUP",
                    message=f"Area '{area_data.name}' đã tồn tại",
                )
                continue

            style_json = area_data.style.model_dump() if area_data.style else None
            area = Area(
                project_id=project_id,
                name=area_data.name,
                grid_row=area_data.grid_row,
                grid_col=area_data.grid_col,
                grid_range=area_data.grid_range,
                position_x=area_data.position_x,
                position_y=area_data.position_y,
                width=area_data.width,
                height=area_data.height,
                style_json=None if style_json is None else json.dumps(style_json),
            )
            db.add(area)
            await db.flush()
            area_by_name[area.name] = area
            created["areas"] += 1

        # Devices
        for idx, device_data in enumerate(device_items):
            row = idx + 1
            if device_data.name in device_by_name:
                if options.merge_strategy == "merge":
                    skipped["devices"] += 1
                    continue
                _add_error(
                    errors,
                    entity="device",
                    row=row,
                    field="name",
                    code="DEVICE_NAME_DUP",
                    message=f"Device '{device_data.name}' đã tồn tại",
                )
                continue

            area = area_by_name.get(device_data.area_name)
            if not area:
                _add_error(
                    errors,
                    entity="device",
                    row=row,
                    field="area_name",
                    code="AREA_NOT_FOUND",
                    message=f"Area '{device_data.area_name}' không tồn tại",
                )
                continue

            color_rgb_json = None
            if device_data.color_rgb:
                color_rgb_json = json.dumps(device_data.color_rgb)

            device = Device(
                project_id=project_id,
                area_id=area.id,
                name=device_data.name,
                device_type=device_data.device_type,
                grid_range=device_data.grid_range,
                position_x=device_data.position_x,
                position_y=device_data.position_y,
                width=device_data.width,
                height=device_data.height,
                color_rgb_json=color_rgb_json,
            )
            db.add(device)
            await db.flush()
            device_by_name[device.name] = device
            created["devices"] += 1

        # L1 Links
        for idx, link_data in enumerate(link_items):
            row = idx + 1
            from_device = device_by_name.get(link_data.from_device)
            to_device = device_by_name.get(link_data.to_device)
            if not from_device:
                _add_error(
                    errors,
                    entity="l1_link",
                    row=row,
                    field="from_device",
                    code="DEVICE_NOT_FOUND",
                    message=f"Device '{link_data.from_device}' không tồn tại",
                )
                continue
            if not to_device:
                _add_error(
                    errors,
                    entity="l1_link",
                    row=row,
                    field="to_device",
                    code="DEVICE_NOT_FOUND",
                    message=f"Device '{link_data.to_device}' không tồn tại",
                )
                continue

            key = _normalize_link_key(
                from_device.id, link_data.from_port, to_device.id, link_data.to_port
            )
            if key in link_keys:
                if options.merge_strategy == "merge":
                    skipped["l1_links"] += 1
                    continue
                _add_error(
                    errors,
                    entity="l1_link",
                    row=row,
                    field=None,
                    code="L1_LINK_DUP",
                    message="Link đã tồn tại",
                )
                continue

            if (from_device.id, link_data.from_port) in ports_in_use:
                _add_error(
                    errors,
                    entity="l1_link",
                    row=row,
                    field="from_port",
                    code="L1_LINK_DUP",
                    message=f"Port '{link_data.from_port}' trên '{from_device.name}' đã được sử dụng",
                )
                continue
            if (to_device.id, link_data.to_port) in ports_in_use:
                _add_error(
                    errors,
                    entity="l1_link",
                    row=row,
                    field="to_port",
                    code="L1_LINK_DUP",
                    message=f"Port '{link_data.to_port}' trên '{to_device.name}' đã được sử dụng",
                )
                continue

            link = L1Link(
                project_id=project_id,
                from_device_id=from_device.id,
                from_port=link_data.from_port,
                to_device_id=to_device.id,
                to_port=link_data.to_port,
                purpose=link_data.purpose,
                line_style=link_data.line_style,
            )
            db.add(link)
            await db.flush()
            for device_id, port_name in (
                (from_device.id, link_data.from_port),
                (to_device.id, link_data.to_port),
            ):
                key_pair = (device_id, port_name)
                if key_pair in device_port_keys:
                    continue
                db.add(
                    DevicePort(
                        project_id=project_id,
                        device_id=device_id,
                        name=port_name,
                        side="bottom",
                        offset_ratio=None,
                    )
                )
                device_port_keys.add(key_pair)
            link_keys.add(key)
            ports_in_use.add((from_device.id, link_data.from_port))
            ports_in_use.add((to_device.id, link_data.to_port))
            created["l1_links"] += 1

        # Port Channels
        for idx, pc_data in enumerate(port_channel_items):
            row = idx + 1
            device = device_by_name.get(pc_data.device_name)
            if not device:
                _add_error(
                    errors,
                    entity="port_channel",
                    row=row,
                    field="device_name",
                    code="DEVICE_NOT_FOUND",
                    message=f"Device '{pc_data.device_name}' không tồn tại",
                )
                continue

            if len(set(pc_data.members)) != len(pc_data.members):
                _add_error(
                    errors,
                    entity="port_channel",
                    row=row,
                    field="members",
                    code="PORT_CHANNEL_MEMBER_DUP",
                    message="Member bị trùng trong port-channel",
                )
                continue

            parsed_number = _extract_channel_number(pc_data.name)
            channel_number = pc_data.channel_number or parsed_number
            if channel_number is None:
                _add_error(
                    errors,
                    entity="port_channel",
                    row=row,
                    field="channel_number",
                    code="PORT_CHANNEL_MEMBERS_INVALID",
                    message="Không xác định được channel_number",
                )
                continue
            if parsed_number is not None and pc_data.channel_number is not None:
                if parsed_number != pc_data.channel_number:
                    _add_error(
                        errors,
                        entity="port_channel",
                        row=row,
                        field="channel_number",
                        code="PORT_CHANNEL_MEMBERS_INVALID",
                        message="Tên và channel_number không khớp",
                    )
                    continue
            if channel_number < 1 or channel_number > 256:
                _add_error(
                    errors,
                    entity="port_channel",
                    row=row,
                    field="channel_number",
                    code="PORT_CHANNEL_MEMBERS_INVALID",
                    message="channel_number phải từ 1 đến 256",
                )
                continue

            key = (device.id, pc_data.name)
            key_number = (device.id, channel_number)
            if key in port_channel_by_key or key_number in port_channel_number_by_key:
                if options.merge_strategy == "merge":
                    skipped["port_channels"] += 1
                    continue
                _add_error(
                    errors,
                    entity="port_channel",
                    row=row,
                    field="name",
                    code="PORT_CHANNEL_MEMBERS_INVALID",
                    message="Port Channel đã tồn tại trong device",
                )
                continue

            port_channel = PortChannel(
                project_id=project_id,
                device_id=device.id,
                name=pc_data.name,
                channel_number=channel_number,
                mode=pc_data.mode,
                members_json=json.dumps(pc_data.members),
            )
            db.add(port_channel)
            await db.flush()
            port_channel_by_key.add(key)
            port_channel_number_by_key.add(key_number)
            created["port_channels"] += 1

        # Virtual Ports
        for idx, vp_data in enumerate(virtual_port_items):
            row = idx + 1
            device = device_by_name.get(vp_data.device_name)
            if not device:
                _add_error(
                    errors,
                    entity="virtual_port",
                    row=row,
                    field="device_name",
                    code="DEVICE_NOT_FOUND",
                    message=f"Device '{vp_data.device_name}' không tồn tại",
                )
                continue

            if not _validate_virtual_port_name(vp_data.name, vp_data.interface_type):
                _add_error(
                    errors,
                    entity="virtual_port",
                    row=row,
                    field="name",
                    code="VIRTUAL_PORT_TYPE_INVALID",
                    message="Tên không khớp interface_type",
                )
                continue

            if (device.id, vp_data.name) in virtual_port_by_key:
                if options.merge_strategy == "merge":
                    skipped["virtual_ports"] += 1
                    continue
                _add_error(
                    errors,
                    entity="virtual_port",
                    row=row,
                    field="name",
                    code="VIRTUAL_PORT_TYPE_INVALID",
                    message="Virtual Port đã tồn tại trong device",
                )
                continue

            virtual_port = VirtualPort(
                project_id=project_id,
                device_id=device.id,
                name=vp_data.name,
                interface_type=vp_data.interface_type,
            )
            db.add(virtual_port)
            await db.flush()
            virtual_port_by_key.add((device.id, vp_data.name))
            created["virtual_ports"] += 1

        # L2 Segments
        for idx, seg_data in enumerate(l2_segment_items):
            row = idx + 1
            if seg_data.vlan_id in l2_segment_by_vlan or seg_data.name in l2_segment_by_name:
                if options.merge_strategy == "merge":
                    skipped["l2_segments"] += 1
                    continue
                _add_error(
                    errors,
                    entity="l2_segment",
                    row=row,
                    field="vlan_id",
                    code="VLAN_INVALID",
                    message=f"VLAN {seg_data.vlan_id} đã tồn tại",
                )
                continue

            segment = L2Segment(
                project_id=project_id,
                name=seg_data.name,
                vlan_id=seg_data.vlan_id,
                description=seg_data.description,
            )
            db.add(segment)
            await db.flush()
            l2_segment_by_name[segment.name] = segment
            l2_segment_by_vlan[segment.vlan_id] = segment
            created["l2_segments"] += 1

        # L2 Assignments
        for idx, assign_data in enumerate(l2_assignment_items):
            row = idx + 1
            device = device_by_name.get(assign_data.device_name)
            if not device:
                _add_error(
                    errors,
                    entity="l2_assignment",
                    row=row,
                    field="device_name",
                    code="DEVICE_NOT_FOUND",
                    message=f"Device '{assign_data.device_name}' không tồn tại",
                )
                continue

            segment = l2_segment_by_name.get(assign_data.l2_segment)
            if not segment:
                _add_error(
                    errors,
                    entity="l2_assignment",
                    row=row,
                    field="l2_segment",
                    code="L2_ASSIGNMENT_INVALID",
                    message=f"L2 segment '{assign_data.l2_segment}' không tồn tại",
                )
                continue

            key = (device.id, assign_data.interface_name)
            if key in l2_assignment_keys:
                if options.merge_strategy == "merge":
                    skipped["l2_assignments"] += 1
                    continue
                _add_error(
                    errors,
                    entity="l2_assignment",
                    row=row,
                    field="interface_name",
                    code="L2_ASSIGNMENT_INVALID",
                    message="Interface đã có L2 assignment",
                )
                continue

            assignment = InterfaceL2Assignment(
                project_id=project_id,
                device_id=device.id,
                interface_name=assign_data.interface_name,
                l2_segment_id=segment.id,
                port_mode=assign_data.port_mode,
                native_vlan=assign_data.native_vlan,
                allowed_vlans_json=(
                    None
                    if assign_data.allowed_vlans is None
                    else json.dumps(assign_data.allowed_vlans)
                ),
            )
            db.add(assignment)
            await db.flush()
            l2_assignment_keys.add(key)
            created["l2_assignments"] += 1

        # L3 Addresses
        for idx, addr_data in enumerate(l3_address_items):
            row = idx + 1
            device = device_by_name.get(addr_data.device_name)
            if not device:
                _add_error(
                    errors,
                    entity="l3_address",
                    row=row,
                    field="device_name",
                    code="DEVICE_NOT_FOUND",
                    message=f"Device '{addr_data.device_name}' không tồn tại",
                )
                continue

            key = (device.id, addr_data.interface_name, addr_data.ip_address, addr_data.prefix_length)
            if key in l3_address_keys:
                if options.merge_strategy == "merge":
                    skipped["l3_addresses"] += 1
                    continue
                _add_error(
                    errors,
                    entity="l3_address",
                    row=row,
                    field="ip_address",
                    code="L3_ASSIGNMENT_INVALID",
                    message="Địa chỉ IP đã tồn tại",
                )
                continue

            address = L3Address(
                project_id=project_id,
                device_id=device.id,
                interface_name=addr_data.interface_name,
                ip_address=addr_data.ip_address,
                prefix_length=addr_data.prefix_length,
                is_secondary=addr_data.is_secondary,
                description=addr_data.description,
            )
            db.add(address)
            await db.flush()
            l3_address_keys.add(key)
            created["l3_addresses"] += 1

        if errors or options.validate_only:
            await tx.rollback()
        else:
            await tx.commit()
            applied = True
    except Exception:
        await tx.rollback()
        raise

    return ImportResult(
        mode=mode,
        validate_only=options.validate_only,
        merge_strategy=options.merge_strategy,
        applied=applied,
        created=created,
        skipped=skipped,
        errors=errors,
    )
