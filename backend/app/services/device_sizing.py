"""
Device auto-sizing logic based on port count.

Auto-resizes device dimensions based on number of ports (from L1 links + L2 assignments).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Device, L1Link, InterfaceL2Assignment


# Base dimensions (inches)
BASE_WIDTH = 1.2
BASE_HEIGHT = 0.5

# Sizing strategy: prioritize horizontal expansion (ports on left/right)
WIDTH_PER_PORT = 0.15  # Each port adds 0.15 inch to width
MIN_WIDTH = 1.2  # Minimum width
MAX_WIDTH = 3.6  # Maximum width to prevent overly wide devices
HEIGHT_THRESHOLD = 24  # If more than 24 ports, increase height slightly
TALL_HEIGHT = 0.6  # Height for high-density devices (>24 ports)


async def compute_device_port_counts(db: AsyncSession, project_id: str) -> dict[str, int]:
    """
    Compute port count for each device in project.

    Counts unique ports from:
    - L1 links (from_port, to_port)
    - L2 interface assignments (interface_name)

    Args:
        db: Database session
        project_id: Project ID

    Returns:
        dict[device_id, port_count]
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

    # Convert sets to counts
    return {device_id: len(ports) for device_id, ports in port_counts.items()}


def compute_device_size(port_count: int) -> tuple[float, float]:
    """
    Compute device width and height based on port count.

    Strategy:
    - Prioritize horizontal (width) expansion
    - Ports are typically on left/right sides of device
    - Increase height only for high-density devices (>24 ports)

    Args:
        port_count: Number of ports on device

    Returns:
        tuple[width, height] in inches
    """
    if port_count == 0:
        return (BASE_WIDTH, BASE_HEIGHT)

    # Compute width: base + increment per port, clamped to [MIN_WIDTH, MAX_WIDTH]
    computed_width = BASE_WIDTH + (port_count * WIDTH_PER_PORT)
    width = max(MIN_WIDTH, min(MAX_WIDTH, computed_width))

    # Compute height: increase only for high-density devices
    height = TALL_HEIGHT if port_count > HEIGHT_THRESHOLD else BASE_HEIGHT

    return (width, height)


async def auto_resize_devices_by_ports(
    db: AsyncSession,
    project_id: str,
    port_counts: dict[str, int],
) -> None:
    """
    Auto-resize devices based on port counts.

    Updates device.width and device.height in database based on computed
    dimensions from port_count.

    Args:
        db: Database session
        project_id: Project ID
        port_counts: dict[device_id, port_count] from compute_device_port_counts()

    Side effects:
        Updates device.width and device.height in database
    """
    for device_id, port_count in port_counts.items():
        # Compute new size
        width, height = compute_device_size(port_count)

        # Update device
        result = await db.execute(
            select(Device).where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()

        if device:
            device.width = width
            device.height = height

    await db.commit()
