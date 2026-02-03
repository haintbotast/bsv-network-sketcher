"""SQLAlchemy models cho BSV Network Sketcher."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ============================================================================
# User & Auth
# ============================================================================


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    projects: Mapped[list["Project"]] = relationship(back_populates="owner")


# ============================================================================
# Project
# ============================================================================


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    layout_mode: Mapped[str] = mapped_column(String(20), default="cisco")  # cisco | iso | custom
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="projects")
    areas: Mapped[list["Area"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    devices: Mapped[list["Device"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    l1_links: Mapped[list["L1Link"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    port_channels: Mapped[list["PortChannel"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    virtual_ports: Mapped[list["VirtualPort"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    l2_segments: Mapped[list["L2Segment"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    interface_l2_assignments: Mapped[list["InterfaceL2Assignment"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    l3_addresses: Mapped[list["L3Address"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    export_jobs: Mapped[list["ExportJob"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    port_anchor_overrides: Mapped[list["PortAnchorOverride"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


# ============================================================================
# Area
# ============================================================================


class Area(Base):
    __tablename__ = "areas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    grid_row: Mapped[int] = mapped_column(Integer, nullable=False)
    grid_col: Mapped[int] = mapped_column(Integer, nullable=False)
    position_x: Mapped[Optional[float]] = mapped_column(Float)
    position_y: Mapped[Optional[float]] = mapped_column(Float)
    width: Mapped[float] = mapped_column(Float, default=3.0)
    height: Mapped[float] = mapped_column(Float, default=1.5)
    # Style stored as JSON text
    style_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="areas")
    devices: Mapped[list["Device"]] = relationship(back_populates="area")


# ============================================================================
# Device
# ============================================================================


DEVICE_TYPES = ["Router", "Switch", "Firewall", "Server", "AP", "PC", "Storage", "Unknown"]


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    area_id: Mapped[str] = mapped_column(String(36), ForeignKey("areas.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[str] = mapped_column(String(20), default="Unknown")
    position_x: Mapped[Optional[float]] = mapped_column(Float)
    position_y: Mapped[Optional[float]] = mapped_column(Float)
    width: Mapped[float] = mapped_column(Float, default=1.2)
    height: Mapped[float] = mapped_column(Float, default=0.5)
    color_rgb_json: Mapped[Optional[str]] = mapped_column(Text)  # [R, G, B] as JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="devices")
    area: Mapped["Area"] = relationship(back_populates="devices")
    port_channels: Mapped[list["PortChannel"]] = relationship(back_populates="device")
    virtual_ports: Mapped[list["VirtualPort"]] = relationship(back_populates="device")
    port_anchor_overrides: Mapped[list["PortAnchorOverride"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


# ============================================================================
# L1 Link
# ============================================================================


LINK_PURPOSES = ["WAN", "INTERNET", "DMZ", "LAN", "MGMT", "HA", "STORAGE", "BACKUP", "VPN", "DEFAULT"]
LINE_STYLES = ["solid", "dashed", "dotted"]


class L1Link(Base):
    __tablename__ = "l1_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    from_device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), nullable=False)
    from_port: Mapped[str] = mapped_column(String(50), nullable=False)
    to_device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), nullable=False)
    to_port: Mapped[str] = mapped_column(String(50), nullable=False)
    purpose: Mapped[str] = mapped_column(String(20), default="DEFAULT")
    line_style: Mapped[str] = mapped_column(String(10), default="solid")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="l1_links")
    from_device: Mapped["Device"] = relationship(foreign_keys=[from_device_id])
    to_device: Mapped["Device"] = relationship(foreign_keys=[to_device_id])


# ============================================================================
# Port Anchor Override
# ============================================================================


ANCHOR_SIDES = ["left", "right", "top", "bottom"]


class PortAnchorOverride(Base):
    __tablename__ = "port_anchor_overrides"
    __table_args__ = (
        UniqueConstraint("project_id", "device_id", "port_name", name="uq_port_anchor_override"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), nullable=False)
    port_name: Mapped[str] = mapped_column(String(50), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False, default="right")
    offset_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="port_anchor_overrides")
    device: Mapped["Device"] = relationship(back_populates="port_anchor_overrides")


# ============================================================================
# Port Channel
# ============================================================================


class PortChannel(Base):
    __tablename__ = "port_channels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # Port-Channel 1
    channel_number: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[str] = mapped_column(String(10), default="LACP")  # LACP | static
    members_json: Mapped[str] = mapped_column(Text, nullable=False)  # ["Gi 0/1", "Gi 0/2"]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="port_channels")
    device: Mapped["Device"] = relationship(back_populates="port_channels")


# ============================================================================
# Virtual Port
# ============================================================================


class VirtualPort(Base):
    __tablename__ = "virtual_ports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # Vlan 100, Loopback 0
    interface_type: Mapped[str] = mapped_column(String(20), nullable=False)  # Vlan | Loopback | Port-Channel
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="virtual_ports")
    device: Mapped["Device"] = relationship(back_populates="virtual_ports")


# ============================================================================
# L2 Segment (VLAN)
# ============================================================================


class L2Segment(Base):
    __tablename__ = "l2_segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    vlan_id: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="l2_segments")


# ============================================================================
# Interface L2 Assignment
# ============================================================================


class InterfaceL2Assignment(Base):
    __tablename__ = "interface_l2_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), nullable=False)
    interface_name: Mapped[str] = mapped_column(String(50), nullable=False)
    l2_segment_id: Mapped[str] = mapped_column(String(36), ForeignKey("l2_segments.id"), nullable=False)
    port_mode: Mapped[str] = mapped_column(String(10), nullable=False)  # access | trunk
    native_vlan: Mapped[Optional[int]] = mapped_column(Integer)
    allowed_vlans_json: Mapped[Optional[str]] = mapped_column(Text)  # [10, 20, 30]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="interface_l2_assignments")


# ============================================================================
# L3 Address
# ============================================================================


class L3Address(Base):
    __tablename__ = "l3_addresses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), nullable=False)
    interface_name: Mapped[str] = mapped_column(String(50), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)  # IPv4 or IPv6
    prefix_length: Mapped[int] = mapped_column(Integer, nullable=False)
    is_secondary: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="l3_addresses")


# ============================================================================
# Export Job
# ============================================================================


JOB_STATUSES = ["pending", "processing", "completed", "failed"]
EXPORT_TYPES = ["l1_diagram", "l2_diagram", "l3_diagram", "device_file", "master_file"]


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    export_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[Optional[str]] = mapped_column(String(255))
    file_path: Mapped[Optional[str]] = mapped_column(String(500))
    file_name: Mapped[Optional[str]] = mapped_column(String(255))
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    options_json: Mapped[Optional[str]] = mapped_column(Text)  # Export options as JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="export_jobs")


# ============================================================================
# Admin Config
# ============================================================================


class AdminConfig(Base):
    __tablename__ = "admin_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    config_key: Mapped[str] = mapped_column(String(50), unique=True, default="global")
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
