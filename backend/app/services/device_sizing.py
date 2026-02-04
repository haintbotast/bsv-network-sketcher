"""
Device auto-sizing logic based on port count and port label length.

Auto-resizes device dimensions based on number of ports (from L1 links + L2 assignments)
and the longest port label to keep straight link spacing reasonable.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Device, L1Link, InterfaceL2Assignment


# Base dimensions (inches)
BASE_WIDTH = 1.2
BASE_HEIGHT = 0.8

# Sizing strategy: prioritize horizontal expansion (ports on left/right)
WIDTH_PER_PORT = 0.15  # Each port adds 0.15 inch to width
MIN_WIDTH = 1.2  # Minimum width
MAX_WIDTH = 3.6  # Maximum width to prevent overly wide devices
MAX_HEIGHT = 1.6  # Upper bound to keep layout stable

# Text sizing (approx, based on UI defaults)
LABEL_CHAR_WIDTH_IN = 6.0 / 120.0
LABEL_PADDING_IN = 8.0 / 120.0
LABEL_MIN_WIDTH_IN = 24.0 / 120.0

# Port label sizing heuristic (based on default render tuning)
# Each port needs spacing of ~22px (label height 14px + gap 8px)
PORT_EDGE_INSET_IN = 6.0 / 120.0
PORT_LABEL_HEIGHT_IN = 22.0 / 120.0


async def compute_device_port_counts(db: AsyncSession, project_id: str) -> dict[str, dict[str, int]]:
    """
    Compute port stats for each device in project.

    Counts unique ports and label lengths from:
    - L1 links (from_port, to_port)
    - L2 interface assignments (interface_name)

    Args:
        db: Database session
        project_id: Project ID

    Returns:
        dict[device_id, {"count": int, "max_label_len": int}]
    """
    port_counts: dict[str, set[str]] = {}

    # Get all devices in project
    result = await db.execute(
        select(Device).where(Device.project_id == project_id)
    )
    devices = result.scalars().all()

    # Initialize empty sets for all devices
    for device in devices:
        port_counts[device.id] = set()

    # Count ports from L1 links
    result = await db.execute(
        select(L1Link).where(L1Link.project_id == project_id)
    )
    links = result.scalars().all()

    for link in links:
        # Add from_port to from_device
        if link.from_device_id in port_counts and link.from_port:
            port_counts[link.from_device_id].add(link.from_port.strip())

        # Add to_port to to_device
        if link.to_device_id in port_counts and link.to_port:
            port_counts[link.to_device_id].add(link.to_port.strip())

    # Count ports from L2 assignments
    result = await db.execute(
        select(InterfaceL2Assignment).where(InterfaceL2Assignment.project_id == project_id)
    )
    l2_assignments = result.scalars().all()

    for assignment in l2_assignments:
        if assignment.device_id in port_counts and assignment.interface_name:
            port_counts[assignment.device_id].add(assignment.interface_name.strip())

    # Convert sets to counts + max port label length
    stats: dict[str, dict[str, int]] = {}
    for device_id, ports in port_counts.items():
        max_len = max((len(p) for p in ports), default=0)
        stats[device_id] = {"count": len(ports), "max_label_len": max_len}

    return stats


def compute_device_size(
    port_count: int,
    name: str | None = None,
    max_port_label_len: int = 0,
) -> tuple[float, float]:
    """
    Compute device width and height based on port count.

    Strategy:
    - Ports distributed across 4 sides (left, right, top, bottom)
    - Height accommodates ports on left/right sides
    - Width accommodates ports on top/bottom sides AND device label
    - Use heuristic: max ports per side = ceil(total / 3)

    Args:
        port_count: Number of ports on device
        name: Device name (for width sizing)
        max_port_label_len: Maximum port label length (for width sizing)

    Returns:
        tuple[width, height] in inches
    """
    import math

    # Heuristic: assume max ports per side = ceil(port_count / 3)
    # This accounts for ports being distributed across 2-3 sides typically
    max_ports_per_side = max(1, math.ceil(port_count / 3))

    # Width from label text
    label = (name or "").strip()
    if label:
        text_width = max(len(label) * LABEL_CHAR_WIDTH_IN + LABEL_PADDING_IN * 2, LABEL_MIN_WIDTH_IN)
    else:
        text_width = LABEL_MIN_WIDTH_IN

    # Width from ports on top/bottom sides
    # Each port needs PORT_LABEL_HEIGHT_IN spacing (same as height calculation)
    ports_width = (PORT_LABEL_HEIGHT_IN * (max_ports_per_side + 1)) + PORT_EDGE_INSET_IN * 2

    # Width from port label text length (if provided)
    port_label_width = LABEL_MIN_WIDTH_IN
    if max_port_label_len > 0:
        port_label_width = max(
            max_port_label_len * LABEL_CHAR_WIDTH_IN + LABEL_PADDING_IN * 2,
            LABEL_MIN_WIDTH_IN,
        )

    # Final width: max of base, label, and ports requirement
    width = max(BASE_WIDTH, text_width, ports_width, port_label_width, MIN_WIDTH)
    width = min(width, MAX_WIDTH)

    # Height from ports on left/right sides
    required_height = (PORT_LABEL_HEIGHT_IN * (max_ports_per_side + 1)) + PORT_EDGE_INSET_IN * 2
    height = max(BASE_HEIGHT, required_height)
    height = min(height, MAX_HEIGHT)

    return (width, height)


async def auto_resize_devices_by_ports(
    db: AsyncSession,
    project_id: str,
    port_stats: dict[str, dict[str, int]],
) -> None:
    """
    Auto-resize devices based on port stats.

    Updates device.width and device.height in database based on computed
    dimensions from port_count and port label length.

    Args:
        db: Database session
        project_id: Project ID
        port_stats: dict[device_id, stats] from compute_device_port_counts()

    Side effects:
        Updates device.width and device.height in database
    """
    for device_id, stats in port_stats.items():
        port_count = stats.get("count", 0)
        max_label_len = stats.get("max_label_len", 0)
        # Get device first to access name
        result = await db.execute(
            select(Device).where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()

        if device:
            # Compute new size (ports + name)
            width, height = compute_device_size(port_count, device.name, max_label_len)
            device.width = width
            device.height = height

    await db.commit()
