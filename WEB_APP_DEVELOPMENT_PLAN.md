# Network Sketcher Web Application - Development Plan

> **Version:** 1.2
> **Created:** 2026-01-23
> **Updated:** 2026-01-23
> **Status:** Planning
> **Estimated Duration:** 10-14 weeks (MVP + Full features)
> **Target Users:** ~5 concurrent users (internal team)

### 📋 Architecture Summary (Simplified)

| Component | Technology | Notes |
|-----------|------------|-------|
| **Backend** | FastAPI + Python 3.11+ | Chạy trực tiếp, không Docker |
| **Frontend** | Vue 3 + Vite | Static files served by Nginx hoặc backend |
| **Database** | SQLite | Single file, không cần DB server |
| **Task Queue** | FastAPI BackgroundTasks | In-process, không cần Redis/Celery |
| **Deployment** | systemd (Linux) / NSSM (Windows) | Native OS service |
| **Backup** | rsync + cron | Copy SQLite file hàng ngày |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [Data Models](#4-data-models)
5. [Backend API Design](#5-backend-api-design)
6. [Frontend Design](#6-frontend-design)
7. [Core Business Logic Implementation](#7-core-business-logic-implementation)
8. [Export Engine](#8-export-engine)
9. [Development Phases](#9-development-phases)
10. [Testing Strategy](#10-testing-strategy)
11. [Deployment](#11-deployment)
12. [Risk Assessment](#12-risk-assessment)
13. [**Original NS Logic Reference**](#13-original-ns-logic-reference) ← NEW

---

## 1. Executive Summary

### 1.1 Project Goal

Xây dựng Web Application mới hoàn toàn để thay thế Network Sketcher CLI/GUI, đảm bảo:
- ✅ 100% business logic compatibility
- ✅ Real-time diagram preview trên browser
- ✅ Export PPTX/Excel đầy đủ chức năng
- ✅ Multi-user support với project management
- ✅ Modern, responsive UI

### 1.2 Key Deliverables

| Deliverable | Description |
|-------------|-------------|
| **Web Dashboard** | Project management, template gallery |
| **Diagram Editor** | Interactive network topology editor |
| **Live Preview** | Real-time SVG/Canvas rendering |
| **Export Engine** | PPTX/Excel generation via API |
| **Data Import** | Excel/CSV upload và parsing |

### 1.3 Success Criteria

- [ ] Tạo được diagram L1/L2/L3 từ Excel input
- [ ] Export PPTX với layout identical với CLI version
- [ ] Export Excel device file với đầy đủ L1/L2/L3 tables
- [ ] Preview diagram real-time trên browser
- [ ] Support 1000+ devices per project
- [ ] Response time < 3s cho diagram generation

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │   Vue 3 SPA     │  │  Diagram Canvas │  │   Export Preview    │  │
│  │   (Vite)        │  │  (Konva.js)     │  │   (PDF.js)          │  │
│  └────────┬────────┘  └────────┬────────┘  └──────────┬──────────┘  │
└───────────┼─────────────────────┼─────────────────────┼─────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY                                 │
│                     (FastAPI + WebSocket)                           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌─────────────────────┐
│   REST API    │     │   WebSocket     │     │   Background Jobs   │
│   Endpoints   │     │   (real-time)   │     │   (Celery/ARQ)      │
└───────┬───────┘     └────────┬────────┘     └──────────┬──────────┘
        │                      │                         │
        ▼                      ▼                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         SERVICE LAYER                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────┐  │
│  │ ProjectSvc   │  │ DiagramSvc   │  │ ExportSvc    │  │ AuthSvc │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────┼───────────────────────┐
▼                               ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌─────────────────────┐
│   SQLite      │     │   In-Process    │     │   File Storage      │
│   (data)      │     │   Task Queue    │     │   (Local FS)        │
└───────────────┘     └─────────────────┘     └─────────────────────┘
```

> **Note:** Architecture đơn giản hóa cho ~5 concurrent users. Không cần Redis/PostgreSQL.
> Nếu scale lên 20+ users, có thể upgrade lên PostgreSQL + Redis.

### 2.2 Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **Vue 3 SPA** | UI rendering, state management, routing |
| **Konva.js Canvas** | Interactive diagram editing, real-time preview |
| **FastAPI Backend** | REST API, WebSocket, business logic |
| **Background Tasks** | Heavy tasks: PPTX/Excel generation (FastAPI BackgroundTasks hoặc ARQ) |
| **SQLite** | Persistent data storage (đơn giản, không cần DB server) |
| **File Storage** | Generated files, uploaded templates (local filesystem) |

### 2.3 Data Flow

```
User Action → Frontend → API → Service → Repository → Database
                                  ↓
                          Export Worker → File Storage → Download URL
```

---

## 3. Technology Stack

### 3.1 Backend

| Category | Technology | Rationale |
|----------|------------|-----------|
| **Framework** | FastAPI 0.110+ | Async native, OpenAPI, Python ecosystem |
| **ORM** | SQLAlchemy 2.0 | Async support, mature |
| **Database** | **SQLite 3** | Đơn giản, không cần DB server, phù hợp cho ~5 users |
| **Task Queue** | FastAPI BackgroundTasks / ARQ | Background job processing (in-process) |
| **PPTX Generation** | python-pptx | Industry standard |
| **Excel I/O** | openpyxl | Full Excel support |
| **PDF Preview** | WeasyPrint / reportlab | Optional preview generation |

#### 📌 Về việc sử dụng SQLite cho ~5 users

**Kết luận: SQLite là lựa chọn phù hợp cho ~5 concurrent users.**

| Tiêu chí | SQLite | PostgreSQL |
|----------|--------|------------|
| **Setup** | Zero config, 1 file | Cần install DB server |
| **Concurrent writes** | 1 writer tại 1 thời điểm | Unlimited |
| **Read concurrency** | Unlimited | Unlimited |
| **Performance (5 users)** | Đủ tốt | Overkill |
| **Backup** | Copy 1 file | pg_dump |
| **Deployment** | Đơn giản (1 container) | 2+ containers |

**Khi nào cần upgrade lên PostgreSQL:**
- Hơn 20 concurrent users
- Cần full-text search phức tạp
- Cần real-time collaboration (nhiều users edit cùng project)
- Cần horizontal scaling

**SQLite configuration tối ưu:**
```python
# database.py
from sqlalchemy import create_engine

engine = create_engine(
    "sqlite:///./network_sketcher.db",
    connect_args={
        "check_same_thread": False,  # Cho phép multi-thread
        "timeout": 30,               # Wait 30s for write lock
    },
    pool_pre_ping=True,
)

# Enable WAL mode for better concurrency
with engine.connect() as conn:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
```

### 3.2 Frontend

| Category | Technology | Rationale |
|----------|------------|-----------|
| **Framework** | Vue 3 + Composition API | Lightweight, reactive |
| **Build Tool** | Vite 5 | Fast HMR, modern bundling |
| **State Management** | Pinia | Vue 3 official, type-safe |
| **UI Library** | PrimeVue / Naive UI | Enterprise components |
| **Diagram Canvas** | Konva.js + vue-konva | Fast 2D canvas rendering |
| **Icons** | Heroicons / Lucide | Modern icon sets |
| **HTTP Client** | Axios / ofetch | Request handling |
| **WebSocket** | Socket.io-client | Real-time updates |

### 3.3 DevOps (Đơn giản hóa cho ~5 users)

> **Triết lý:** Không sử dụng Docker. Chạy trực tiếp trên máy chủ với Python + Node.js.

| Category | Technology | Lý do |
|----------|------------|-------|
| **Process Manager** | systemd / PM2 | Native OS, không cần container |
| **Reverse Proxy** | Nginx (optional) | Chỉ cần nếu public internet |
| **Backup** | rsync / cron job | Copy SQLite file + exports folder |
| **Logging** | Python logging → file | Simple, đủ cho small team |
| **Monitoring** | Health check endpoint | `/health` API endpoint |

#### Tại sao không dùng Docker?

| Aspect | Docker | Native |
|--------|--------|--------|
| **Learning curve** | Cần học Docker, compose | Không cần |
| **Debugging** | Phức tạp hơn | Trực tiếp |
| **Resource overhead** | ~200MB+ RAM/container | Minimal |
| **Setup time** | 30+ phút | 10 phút |
| **Phù hợp cho** | Production scale, CI/CD | Internal tools, ~5 users |

**Khi nào nên dùng Docker:**
- Cần deploy trên nhiều servers
- Cần CI/CD tự động
- Team có kinh nghiệm Docker
- Scale lên 50+ users

---

## 4. Data Models

### 4.1 Entity Relationship Diagram

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    User      │────<│   Project    │────<│    Area      │
└──────────────┘     └──────────────┘     └──────────────┘
                            │                    │
                            │                    │
                     ┌──────┴──────┐      ┌──────┴──────┐
                     ▼             ▼      ▼             ▼
              ┌───────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐
              │  Export   │  │ Template│  │  Device  │  │ Waypoint │
              │   Job     │  │         │  │          │  │          │
              └───────────┘  └─────────┘  └────┬─────┘  └──────────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          ▼                    ▼                    ▼
                   ┌────────────┐       ┌────────────┐       ┌────────────┐
                   │ Interface  │       │  L1_Link   │       │ Attribute  │
                   │ (Physical) │       │            │       │            │
                   └─────┬──────┘       └────────────┘       └────────────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
       ┌───────────┐ ┌───────────┐ ┌───────────┐
       │ L2_Segment│ │ L3_Address│ │PortChannel│
       │           │ │           │ │           │
       └───────────┘ └───────────┘ └───────────┘
```

### 4.2 Database Schema

```sql
-- Users & Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    settings JSONB DEFAULT '{}',
    theme VARCHAR(50) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Areas (Network Zones)
CREATE TABLE areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    grid_row INTEGER NOT NULL,
    grid_col INTEGER NOT NULL,
    description TEXT,
    position_x DECIMAL(10,4),
    position_y DECIMAL(10,4),
    width DECIMAL(10,4),
    height DECIMAL(10,4),
    style JSONB DEFAULT '{}',
    is_waypoint_area BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, name)
);

-- Devices
CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    area_id UUID REFERENCES areas(id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    device_type VARCHAR(50),
    model VARCHAR(100),
    grid_row INTEGER,
    grid_col INTEGER,
    position_x DECIMAL(10,4),
    position_y DECIMAL(10,4),
    width DECIMAL(10,4),
    height DECIMAL(10,4),
    color_rgb INTEGER[3],
    is_waypoint BOOLEAN DEFAULT FALSE,
    attributes JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, name)
);

-- Interfaces (Physical + Virtual)
CREATE TABLE interfaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    interface_type VARCHAR(50), -- physical, virtual, loopback, svi, port-channel
    normalized_name VARCHAR(100),
    slot INTEGER,
    port INTEGER,
    is_virtual BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(device_id, name)
);

-- L1 Links (Physical Connections)
CREATE TABLE l1_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    from_interface_id UUID REFERENCES interfaces(id) ON DELETE CASCADE,
    to_interface_id UUID REFERENCES interfaces(id) ON DELETE CASCADE,
    purpose VARCHAR(50), -- WAN, LAN, DMZ, MGMT, HA, STORAGE, BACKUP, VPN
    cable_type VARCHAR(50),
    speed VARCHAR(20),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(from_interface_id, to_interface_id)
);

-- L2 Segments (VLANs)
CREATE TABLE l2_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    vlan_id INTEGER,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, name)
);

-- Interface L2 Assignment
CREATE TABLE interface_l2_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interface_id UUID REFERENCES interfaces(id) ON DELETE CASCADE,
    l2_segment_id UUID REFERENCES l2_segments(id) ON DELETE CASCADE,
    port_mode VARCHAR(20), -- access, trunk
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(interface_id, l2_segment_id)
);

-- L3 Addresses
CREATE TABLE l3_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interface_id UUID REFERENCES interfaces(id) ON DELETE CASCADE,
    ip_address INET NOT NULL,
    prefix_length INTEGER NOT NULL,
    vrf_name VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Port Channels
CREATE TABLE port_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    channel_number INTEGER,
    mode VARCHAR(20), -- LACP, static
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(device_id, name)
);

-- Port Channel Members
CREATE TABLE port_channel_members (
    port_channel_id UUID REFERENCES port_channels(id) ON DELETE CASCADE,
    interface_id UUID REFERENCES interfaces(id) ON DELETE CASCADE,
    PRIMARY KEY (port_channel_id, interface_id)
);

-- Export Jobs
CREATE TABLE export_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    job_type VARCHAR(50) NOT NULL, -- l1_diagram, l2_diagram, l3_diagram, device_file
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    options JSONB DEFAULT '{}',
    result_file_path VARCHAR(500),
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_devices_project ON devices(project_id);
CREATE INDEX idx_devices_area ON devices(area_id);
CREATE INDEX idx_interfaces_device ON interfaces(device_id);
CREATE INDEX idx_l1_links_project ON l1_links(project_id);
CREATE INDEX idx_export_jobs_project ON export_jobs(project_id);
CREATE INDEX idx_export_jobs_status ON export_jobs(status);
```

### 4.3 Pydantic Models (API)

```python
# schemas/project.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class AreaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    grid_row: int = Field(..., ge=1)
    grid_col: int = Field(..., ge=1)
    description: Optional[str] = None

class DeviceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    area_name: str
    device_type: Optional[str] = None
    model: Optional[str] = None
    grid_row: int = Field(1, ge=1)
    grid_col: int = Field(1, ge=1)

class L1LinkCreate(BaseModel):
    from_device: str
    from_port: str
    to_device: str
    to_port: str
    purpose: Optional[str] = None
    cable_type: Optional[str] = None
    speed: Optional[str] = None

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    theme: str = "default"

class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    theme: str
    areas_count: int
    devices_count: int
    links_count: int
    created_at: datetime
    updated_at: datetime

class DiagramData(BaseModel):
    """Complete diagram data for rendering"""
    areas: List[dict]
    devices: List[dict]
    links: List[dict]
    l2_segments: List[dict]
    l3_addresses: List[dict]
    settings: dict
```

---

## 5. Backend API Design

### 5.1 API Endpoints Overview

```
/api/v1
├── /auth
│   ├── POST   /register          # User registration
│   ├── POST   /login             # Login, get JWT
│   ├── POST   /refresh           # Refresh token
│   └── POST   /logout            # Invalidate token
│
├── /projects
│   ├── GET    /                  # List user projects
│   ├── POST   /                  # Create project
│   ├── GET    /{id}              # Get project details
│   ├── PUT    /{id}              # Update project
│   ├── DELETE /{id}              # Delete project
│   ├── POST   /{id}/duplicate    # Clone project
│   └── POST   /{id}/import       # Import from Excel
│
├── /projects/{project_id}
│   ├── /areas
│   │   ├── GET    /              # List areas
│   │   ├── POST   /              # Create area
│   │   ├── PUT    /{id}          # Update area
│   │   ├── DELETE /{id}          # Delete area
│   │   └── POST   /bulk          # Bulk create (grid format)
│   │
│   ├── /devices
│   │   ├── GET    /              # List devices
│   │   ├── POST   /              # Create device
│   │   ├── PUT    /{id}          # Update device
│   │   ├── DELETE /{id}          # Delete device
│   │   ├── POST   /bulk          # Bulk create
│   │   └── GET    /{id}/interfaces  # Device interfaces
│   │
│   ├── /interfaces
│   │   ├── GET    /              # List all interfaces
│   │   ├── POST   /              # Create interface
│   │   ├── PUT    /{id}          # Update interface
│   │   ├── DELETE /{id}          # Delete interface
│   │   └── POST   /virtual       # Create virtual port
│   │
│   ├── /links
│   │   ├── GET    /              # List L1 links
│   │   ├── POST   /              # Create link
│   │   ├── PUT    /{id}          # Update link
│   │   ├── DELETE /{id}          # Delete link
│   │   └── POST   /bulk          # Bulk create
│   │
│   ├── /l2
│   │   ├── GET    /segments      # List L2 segments
│   │   ├── POST   /segments      # Create segment
│   │   ├── GET    /assignments   # Interface→segment mapping
│   │   ├── POST   /assignments   # Assign interface to segment
│   │   └── GET    /broadcast-domains  # Computed broadcast domains
│   │
│   ├── /l3
│   │   ├── GET    /addresses     # List IP addresses
│   │   ├── POST   /addresses     # Add IP address
│   │   ├── PUT    /addresses/{id}# Update IP
│   │   └── DELETE /addresses/{id}# Remove IP
│   │
│   ├── /diagram
│   │   ├── GET    /data          # Complete diagram data (for rendering)
│   │   ├── GET    /l1            # L1 diagram data
│   │   ├── GET    /l2            # L2 diagram data
│   │   └── GET    /l3            # L3 diagram data
│   │
│   └── /export
│       ├── POST   /l1-diagram    # Export L1 PPTX (async job)
│       ├── POST   /l2-diagram    # Export L2 PPTX (async job)
│       ├── POST   /l3-diagram    # Export L3 PPTX (async job)
│       ├── POST   /device-file   # Export Excel device file
│       ├── POST   /master-file   # Export master Excel
│       ├── GET    /jobs          # List export jobs
│       └── GET    /jobs/{id}     # Job status + download URL
│
├── /templates
│   ├── GET    /                  # List available templates
│   ├── GET    /{id}              # Get template details
│   └── POST   /{id}/apply        # Apply template to project
│
└── /uploads
    ├── POST   /excel             # Upload Excel for import
    └── POST   /csv               # Upload CSV for import
```

### 5.2 WebSocket Events

```
WS /ws/projects/{project_id}

Events (Server → Client):
├── diagram.updated           # Diagram data changed
├── export.progress           # Export job progress (0-100%)
├── export.completed          # Export finished, download ready
├── export.failed             # Export error
├── user.joined               # Another user opened project
└── user.left                 # User left project

Events (Client → Server):
├── diagram.subscribe         # Subscribe to diagram updates
├── diagram.unsubscribe       # Unsubscribe
└── cursor.move               # Share cursor position (collaboration)
```

### 5.3 API Implementation Example

```python
# api/v1/endpoints/projects.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.deps import get_db, get_current_user
from app.schemas.project import ProjectCreate, ProjectResponse, DiagramData
from app.services.project_service import ProjectService
from app.services.diagram_service import DiagramService
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all projects for current user"""
    service = ProjectService(db)
    return await service.list_user_projects(current_user.id)

@router.post("/", response_model=ProjectResponse)
async def create_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new project"""
    service = ProjectService(db)
    return await service.create_project(project_in, current_user.id)

@router.get("/{project_id}/diagram/data", response_model=DiagramData)
async def get_diagram_data(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get complete diagram data for rendering"""
    diagram_service = DiagramService(db)
    return await diagram_service.get_complete_diagram_data(project_id)

@router.post("/{project_id}/export/l1-diagram")
async def export_l1_diagram(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    options: dict = {},
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Queue L1 diagram export job"""
    from app.services.export_service import ExportService

    service = ExportService(db)
    job = await service.queue_export_job(
        project_id=project_id,
        user_id=current_user.id,
        job_type="l1_diagram",
        options=options
    )

    return {"job_id": job.id, "status": "queued"}
```

---

## 6. Frontend Design

### 6.1 Page Structure

```
/
├── /login                    # Login page
├── /register                 # Registration page
├── /dashboard                # Project list, stats
├── /projects
│   ├── /new                  # Create project wizard
│   └── /{id}
│       ├── /                 # Project overview
│       ├── /editor           # Main diagram editor
│       ├── /data             # Data tables (devices, links, IPs)
│       ├── /import           # Import wizard
│       ├── /export           # Export options
│       └── /settings         # Project settings
└── /templates                # Template gallery
```

### 6.2 Component Architecture

```
src/
├── components/
│   ├── common/
│   │   ├── AppHeader.vue
│   │   ├── AppSidebar.vue
│   │   ├── DataTable.vue
│   │   ├── FileUpload.vue
│   │   └── LoadingSpinner.vue
│   │
│   ├── diagram/
│   │   ├── DiagramCanvas.vue       # Main Konva canvas
│   │   ├── AreaShape.vue           # Area rectangle component
│   │   ├── DeviceShape.vue         # Device shape component
│   │   ├── ConnectionLine.vue      # Link line component
│   │   ├── InterfaceTag.vue        # Interface label
│   │   ├── DiagramToolbar.vue      # Zoom, pan, export controls
│   │   ├── PropertyPanel.vue       # Selected item properties
│   │   └── MiniMap.vue             # Overview minimap
│   │
│   ├── editor/
│   │   ├── AreaEditor.vue          # Area CRUD form
│   │   ├── DeviceEditor.vue        # Device CRUD form
│   │   ├── LinkEditor.vue          # Link CRUD form
│   │   ├── InterfaceEditor.vue     # Interface management
│   │   ├── L2SegmentEditor.vue     # VLAN assignment
│   │   └── L3AddressEditor.vue     # IP address management
│   │
│   ├── import/
│   │   ├── ExcelImporter.vue       # Excel upload + preview
│   │   ├── CSVImporter.vue         # CSV upload + mapping
│   │   ├── ImportPreview.vue       # Preview before import
│   │   └── ImportProgress.vue      # Import status
│   │
│   └── export/
│       ├── ExportDialog.vue        # Export options modal
│       ├── ExportProgress.vue      # Job progress
│       └── ExportHistory.vue       # Past exports
│
├── views/
│   ├── LoginView.vue
│   ├── DashboardView.vue
│   ├── ProjectEditorView.vue
│   ├── ProjectDataView.vue
│   └── TemplatesView.vue
│
├── stores/
│   ├── auth.ts                     # Authentication state
│   ├── project.ts                  # Current project state
│   ├── diagram.ts                  # Diagram data & selection
│   └── export.ts                   # Export jobs state
│
├── composables/
│   ├── useDiagram.ts               # Diagram manipulation
│   ├── useExport.ts                # Export operations
│   ├── useWebSocket.ts             # Real-time updates
│   └── useDeviceColors.ts          # Industry color mapping
│
└── utils/
    ├── api.ts                      # API client
    ├── colors.ts                   # Color utilities
    ├── validation.ts               # Port name, IP validation
    └── layout.ts                   # Layout algorithms
```

### 6.3 Diagram Canvas Implementation

```typescript
// composables/useDiagram.ts
import { ref, computed, watch } from 'vue'
import Konva from 'konva'
import { useProjectStore } from '@/stores/project'
import { getDeviceColor } from '@/utils/colors'

export function useDiagram() {
  const store = useProjectStore()
  const stage = ref<Konva.Stage | null>(null)
  const layer = ref<Konva.Layer | null>(null)
  const selectedId = ref<string | null>(null)

  // Initialize canvas
  function initCanvas(container: HTMLDivElement) {
    stage.value = new Konva.Stage({
      container,
      width: container.clientWidth,
      height: container.clientHeight,
      draggable: true
    })

    layer.value = new Konva.Layer()
    stage.value.add(layer.value)
  }

  // Render areas
  function renderAreas(areas: Area[]) {
    areas.forEach(area => {
      const group = new Konva.Group({
        x: area.position_x * SCALE,
        y: area.position_y * SCALE,
        id: `area-${area.id}`,
        draggable: true
      })

      // Area background
      const rect = new Konva.Rect({
        width: area.width * SCALE,
        height: area.height * SCALE,
        fill: '#f0f0f0',
        stroke: '#333',
        strokeWidth: 1,
        cornerRadius: 5
      })

      // Area label
      const text = new Konva.Text({
        text: area.name,
        fontSize: 14,
        fontFamily: 'Calibri',
        fill: '#333',
        padding: 5
      })

      group.add(rect, text)
      layer.value?.add(group)
    })
  }

  // Render devices
  function renderDevices(devices: Device[]) {
    devices.forEach(device => {
      const color = getDeviceColor(device.name, device.device_type)

      const group = new Konva.Group({
        x: device.position_x * SCALE,
        y: device.position_y * SCALE,
        id: `device-${device.id}`,
        draggable: true
      })

      // Device shape
      const rect = new Konva.Rect({
        width: device.width * SCALE,
        height: device.height * SCALE,
        fill: `rgb(${color.join(',')})`,
        stroke: '#333',
        strokeWidth: 1,
        cornerRadius: 3
      })

      // Device label
      const text = new Konva.Text({
        text: device.name,
        fontSize: 10,
        fontFamily: 'Calibri',
        fill: '#000',
        width: device.width * SCALE,
        align: 'center',
        verticalAlign: 'middle'
      })

      group.add(rect, text)

      // Click handler
      group.on('click', () => {
        selectedId.value = device.id
        store.selectDevice(device.id)
      })

      layer.value?.add(group)
    })
  }

  // Render connections
  function renderLinks(links: L1Link[]) {
    links.forEach(link => {
      const fromDevice = store.getDevice(link.from_device_id)
      const toDevice = store.getDevice(link.to_device_id)

      if (!fromDevice || !toDevice) return

      const [fromPoint, toPoint] = calculateConnectionPoints(
        fromDevice, toDevice
      )

      const line = new Konva.Line({
        points: [fromPoint.x, fromPoint.y, toPoint.x, toPoint.y],
        stroke: getLinkColor(link.purpose),
        strokeWidth: 1.5,
        id: `link-${link.id}`
      })

      layer.value?.add(line)
    })
  }

  return {
    stage,
    layer,
    selectedId,
    initCanvas,
    renderAreas,
    renderDevices,
    renderLinks
  }
}
```

### 6.4 Color System Implementation

```typescript
// utils/colors.ts

export const INDUSTRY_COLORS: Record<string, [number, number, number]> = {
  // Network Infrastructure
  'Router': [70, 130, 180],
  'ISP': [70, 130, 180],

  // Firewalls
  'FW': [220, 80, 80],
  'Firewall': [220, 80, 80],
  'FW-External': [200, 60, 60],
  'WAF': [178, 34, 34],

  // Switches
  'Core-SW': [34, 139, 34],
  'Core': [34, 139, 34],
  'Dist': [60, 179, 113],
  'Access-SW': [0, 139, 139],
  'Access': [0, 139, 139],
  'SW': [46, 139, 87],
  'Switch': [46, 139, 87],

  // Servers
  'Server': [106, 90, 205],
  'App': [138, 43, 226],
  'Web': [75, 0, 130],
  'DB': [148, 0, 211],

  // Storage
  'NAS': [210, 105, 30],
  'SAN': [184, 134, 11],
  'Storage': [205, 133, 63],
  'Backup': [139, 90, 43]
}

export const LINK_PURPOSE_COLORS: Record<string, [number, number, number]> = {
  'WAN': [0, 112, 192],
  'INTERNET': [0, 112, 192],
  'DMZ': [237, 125, 49],
  'LAN': [112, 173, 71],
  'MGMT': [112, 48, 160],
  'STORAGE': [165, 105, 63],
  'BACKUP': [127, 127, 127],
  'HA': [96, 96, 96],
  'VPN': [192, 0, 0],
  'DEFAULT': [0, 0, 0]
}

export function getDeviceColor(
  deviceName: string,
  deviceType?: string
): [number, number, number] {
  const nameUpper = deviceName.toUpperCase()

  // Sort by key length (longest first) for prefix matching
  const sortedKeys = Object.keys(INDUSTRY_COLORS)
    .sort((a, b) => b.length - a.length)

  for (const key of sortedKeys) {
    if (nameUpper.includes(key.toUpperCase())) {
      return INDUSTRY_COLORS[key]
    }
  }

  // Check device type
  if (deviceType && INDUSTRY_COLORS[deviceType]) {
    return INDUSTRY_COLORS[deviceType]
  }

  return [128, 128, 128] // Default gray
}

export function getLinkColor(purpose?: string): string {
  if (!purpose) return 'rgb(0,0,0)'

  const normalized = normalizePurpose(purpose)
  const color = LINK_PURPOSE_COLORS[normalized] || LINK_PURPOSE_COLORS['DEFAULT']

  return `rgb(${color.join(',')})`
}

function normalizePurpose(purpose: string): string {
  const upper = purpose.toUpperCase()

  if (['WAN', 'INTERNET', 'ISP', 'EDGE', 'UNTRUST', 'PUBLIC'].some(k => upper.includes(k))) {
    return 'WAN'
  }
  if (upper.includes('DMZ')) return 'DMZ'
  if (['MGMT', 'MANAGEMENT', 'OOB'].some(k => upper.includes(k))) return 'MGMT'
  if (['STORAGE', 'SAN', 'NAS'].some(k => upper.includes(k))) return 'STORAGE'
  if (upper.includes('BACKUP')) return 'BACKUP'
  if (['HA', 'REDUNDANCY', 'PEER'].some(k => upper.includes(k))) return 'HA'
  if (['VPN', 'TUNNEL'].some(k => upper.includes(k))) return 'VPN'
  if (['LAN', 'INTERNAL', 'TRUST'].some(k => upper.includes(k))) return 'LAN'

  return 'DEFAULT'
}
```

---

## 7. Core Business Logic Implementation

### 7.1 Validation Service

```python
# services/validation_service.py
import re
from typing import Optional, Tuple, List

class ValidationService:
    """Port name and IP address validation"""

    INTERFACE_PATTERNS = {
        r'^(gigabitethernet|ge)\s+(\d+)/(\d+)$': 'GigabitEthernet',
        r'^(fastethernet|fe)\s+(\d+)/(\d+)$': 'FastEthernet',
        r'^(ethernet|eth|et)\s+(\d+)/(\d+)$': 'Ethernet',
        r'^(tengige|te)\s+(\d+)/(\d+)$': 'TenGigE',
        r'^(loopback|lo)\s*(\d+)$': 'Loopback',
        r'^(vlan|vl)\s*(\d+)$': 'Vlan',
        r'^(port-channel|po)\s*(\d+)$': 'Port-Channel',
    }

    def normalize_port_name(self, port_name: str) -> Optional[str]:
        """
        Normalize port name to standard format.
        Returns None if invalid.

        Examples:
            'Gi 0/1' -> 'GigabitEthernet 0/1'
            'Po1' -> 'Port-Channel 1'
            'Vlan10' -> 'Vlan 10'
        """
        port_clean = port_name.strip().lower()

        for pattern, standard_name in self.INTERFACE_PATTERNS.items():
            match = re.match(pattern, port_clean, re.IGNORECASE)
            if match:
                groups = match.groups()
                if standard_name in ['Loopback', 'Vlan', 'Port-Channel']:
                    # Single number interfaces
                    return f"{standard_name} {groups[-1]}"
                else:
                    # Slot/port interfaces
                    slot, port = groups[-2], groups[-1]
                    return f"{standard_name} {slot}/{port}"

        return None

    def validate_ip_address(self, ip_string: str) -> Tuple[bool, str]:
        """
        Validate IPv4 address with CIDR notation.
        Returns (is_valid, error_message)
        """
        if ip_string.count('/') != 1:
            return False, "Must have exactly one '/' for CIDR notation"

        ip_part, prefix_part = ip_string.split('/')

        # Validate prefix
        try:
            prefix = int(prefix_part)
            if not (1 <= prefix <= 32):
                return False, f"Prefix must be 1-32, got {prefix}"
        except ValueError:
            return False, f"Invalid prefix: {prefix_part}"

        # Validate IP octets
        octets = ip_part.split('.')
        if len(octets) != 4:
            return False, "IP must have 4 octets"

        for i, octet in enumerate(octets):
            try:
                val = int(octet)
                if not (0 <= val <= 255):
                    return False, f"Octet {i+1} must be 0-255, got {val}"
            except ValueError:
                return False, f"Invalid octet: {octet}"

        return True, ""

    def check_duplicate_link(
        self,
        existing_links: List[dict],
        from_device: str,
        to_device: str,
        from_port: str,
        to_port: str
    ) -> bool:
        """Check if link already exists (in either direction)"""
        for link in existing_links:
            # Forward match
            if (link['from_device'] == from_device and
                link['to_device'] == to_device and
                link['from_port'] == from_port and
                link['to_port'] == to_port):
                return True

            # Reverse match
            if (link['from_device'] == to_device and
                link['to_device'] == from_device and
                link['from_port'] == to_port and
                link['to_port'] == from_port):
                return True

        return False
```

### 7.2 Layout Algorithm Service

```python
# services/layout_service.py
from typing import List, Dict, Tuple
import math

class LayoutService:
    """Diagram layout algorithms"""

    # Constants
    DEVICE_DEFAULT_WIDTH = 1.2  # inches
    DEVICE_DEFAULT_HEIGHT = 0.5
    DEVICE_SPACING = 0.15
    AREA_PADDING = 0.2
    AREA_MARGIN = 0.1

    def calculate_area_dimensions(
        self,
        devices: List[dict],
        max_cols: int = 6
    ) -> Tuple[float, float]:
        """
        Calculate area width/height based on devices.
        Uses grid layout algorithm.
        """
        if not devices:
            return (2.0, 1.0)  # Minimum size

        device_count = len(devices)
        cols = min(device_count, max_cols)
        rows = math.ceil(device_count / cols)

        width = (cols * self.DEVICE_DEFAULT_WIDTH +
                 (cols - 1) * self.DEVICE_SPACING +
                 2 * self.AREA_PADDING)

        height = (rows * self.DEVICE_DEFAULT_HEIGHT +
                  (rows - 1) * self.DEVICE_SPACING +
                  2 * self.AREA_PADDING +
                  0.3)  # Label space

        return (width, height)

    def position_devices_in_area(
        self,
        devices: List[dict],
        area_x: float,
        area_y: float,
        area_width: float,
        max_cols: int = 6
    ) -> List[dict]:
        """
        Position devices in grid within area.
        Returns devices with updated x, y positions.
        """
        if not devices:
            return devices

        result = []
        cols = min(len(devices), max_cols)

        # Calculate starting position
        start_x = area_x + self.AREA_PADDING
        start_y = area_y + self.AREA_PADDING + 0.3  # Below label

        for i, device in enumerate(devices):
            row = i // cols
            col = i % cols

            device_copy = device.copy()
            device_copy['position_x'] = (
                start_x + col * (self.DEVICE_DEFAULT_WIDTH + self.DEVICE_SPACING)
            )
            device_copy['position_y'] = (
                start_y + row * (self.DEVICE_DEFAULT_HEIGHT + self.DEVICE_SPACING)
            )
            device_copy['width'] = self.DEVICE_DEFAULT_WIDTH
            device_copy['height'] = self.DEVICE_DEFAULT_HEIGHT

            result.append(device_copy)

        return result

    def calculate_connection_points(
        self,
        from_device: dict,
        to_device: dict
    ) -> Tuple[dict, dict]:
        """
        Calculate optimal connection points on device edges.
        Uses 8-directional logic.
        """
        # Device centers
        from_cx = from_device['position_x'] + from_device['width'] / 2
        from_cy = from_device['position_y'] + from_device['height'] / 2
        to_cx = to_device['position_x'] + to_device['width'] / 2
        to_cy = to_device['position_y'] + to_device['height'] / 2

        # Direction vector
        dx = to_cx - from_cx
        dy = to_cy - from_cy

        # Determine primary direction
        if abs(dx) > abs(dy):
            # Horizontal dominant
            if dx > 0:
                # Left to Right
                from_point = {
                    'x': from_device['position_x'] + from_device['width'],
                    'y': from_cy
                }
                to_point = {
                    'x': to_device['position_x'],
                    'y': to_cy
                }
            else:
                # Right to Left
                from_point = {
                    'x': from_device['position_x'],
                    'y': from_cy
                }
                to_point = {
                    'x': to_device['position_x'] + to_device['width'],
                    'y': to_cy
                }
        else:
            # Vertical dominant
            if dy > 0:
                # Top to Bottom
                from_point = {
                    'x': from_cx,
                    'y': from_device['position_y'] + from_device['height']
                }
                to_point = {
                    'x': to_cx,
                    'y': to_device['position_y']
                }
            else:
                # Bottom to Top
                from_point = {
                    'x': from_cx,
                    'y': from_device['position_y']
                }
                to_point = {
                    'x': to_cx,
                    'y': to_device['position_y'] + to_device['height']
                }

        return (from_point, to_point)
```

### 7.3 Synchronization Service

```python
# services/sync_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

class SyncService:
    """Synchronize changes between L1, L2, L3 layers"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def rename_device(
        self,
        project_id: UUID,
        old_name: str,
        new_name: str
    ) -> dict:
        """
        Rename device and propagate to all layers.
        Returns summary of updates.
        """
        updates = {
            'devices': 0,
            'links': 0,
            'l2_assignments': 0,
            'l3_addresses': 0
        }

        # Update device table
        result = await self.db.execute(
            update(Device)
            .where(Device.project_id == project_id)
            .where(Device.name == old_name)
            .values(name=new_name)
        )
        updates['devices'] = result.rowcount

        # Links are FK-based, no update needed if using device_id

        # L2/L3 are also FK-based

        await self.db.commit()
        return updates

    async def rename_interface(
        self,
        device_id: UUID,
        old_name: str,
        new_name: str
    ) -> dict:
        """
        Rename interface and propagate to L2/L3 tables.
        """
        updates = {
            'interfaces': 0,
            'l2_assignments': 0,
            'l3_addresses': 0
        }

        # Find interface
        interface = await self.db.execute(
            select(Interface)
            .where(Interface.device_id == device_id)
            .where(Interface.name == old_name)
        )
        interface = interface.scalar_one_or_none()

        if not interface:
            raise ValueError(f"Interface '{old_name}' not found")

        # Normalize new name
        from app.services.validation_service import ValidationService
        validator = ValidationService()
        normalized = validator.normalize_port_name(new_name)

        if not normalized:
            raise ValueError(f"Invalid port name format: {new_name}")

        # Update interface
        interface.name = new_name
        interface.normalized_name = normalized
        updates['interfaces'] = 1

        await self.db.commit()
        return updates
```

---

## 8. Export Engine

### 8.1 PPTX Generator Service

```python
# services/pptx_generator.py
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from typing import List, Dict
import io

from app.utils.colors import get_device_color, get_link_color

class PPTXGenerator:
    """Generate PowerPoint diagrams"""

    # Constants
    MIN_SLIDE_WIDTH = 13.4
    MAX_SLIDE_WIDTH = 56.0
    MIN_SLIDE_HEIGHT = 7.5
    MAX_SLIDE_HEIGHT = 56.0

    MARGIN = 1.0
    FOLDER_FONT_SIZE = 10
    DEVICE_FONT_SIZE = 6
    LINE_WIDTH_NORMAL = 0.5
    LINE_WIDTH_CONTRAST = 1.25

    def __init__(self, theme: str = "default"):
        self.theme = theme
        self.prs = Presentation()
        self.slide = None

    def generate_l1_diagram(
        self,
        areas: List[dict],
        devices: List[dict],
        links: List[dict],
        settings: dict = {}
    ) -> bytes:
        """
        Generate L1 physical topology diagram.
        Returns PPTX file as bytes.
        """
        # Calculate slide dimensions
        slide_width, slide_height = self._calculate_slide_size(areas, devices)

        self.prs.slide_width = Inches(slide_width)
        self.prs.slide_height = Inches(slide_height)

        # Add slide
        slide_layout = self.prs.slide_layouts[5]  # Title only
        self.slide = self.prs.slides.add_slide(slide_layout)

        # Add root container
        self._add_root_folder(slide_width, slide_height)

        # Render areas
        for area in areas:
            self._add_area_folder(area)

        # Render devices
        for device in devices:
            self._add_device_shape(device)

        # Render connections
        for link in links:
            self._add_connection_line(link, devices)

        # Save to bytes
        output = io.BytesIO()
        self.prs.save(output)
        output.seek(0)
        return output.read()

    def _calculate_slide_size(
        self,
        areas: List[dict],
        devices: List[dict]
    ) -> tuple:
        """Calculate optimal slide dimensions"""
        if not areas and not devices:
            return (self.MIN_SLIDE_WIDTH, self.MIN_SLIDE_HEIGHT)

        # Find bounding box
        max_x = max_y = 0

        for area in areas:
            right = area.get('position_x', 0) + area.get('width', 2)
            bottom = area.get('position_y', 0) + area.get('height', 1)
            max_x = max(max_x, right)
            max_y = max(max_y, bottom)

        for device in devices:
            right = device.get('position_x', 0) + device.get('width', 1)
            bottom = device.get('position_y', 0) + device.get('height', 0.5)
            max_x = max(max_x, right)
            max_y = max(max_y, bottom)

        # Add margins
        width = max(self.MIN_SLIDE_WIDTH, min(self.MAX_SLIDE_WIDTH, max_x + 2 * self.MARGIN))
        height = max(self.MIN_SLIDE_HEIGHT, min(self.MAX_SLIDE_HEIGHT, max_y + 2 * self.MARGIN))

        return (width, height)

    def _add_root_folder(self, width: float, height: float):
        """Add root container rectangle"""
        shape = self.slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(self.MARGIN / 2),
            Inches(self.MARGIN / 2),
            Inches(width - self.MARGIN),
            Inches(height - self.MARGIN)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(240, 240, 240)
        shape.line.color.rgb = RGBColor(100, 100, 100)
        shape.line.width = Pt(1)

    def _add_area_folder(self, area: dict):
        """Add area rectangle with label"""
        x = area.get('position_x', 0) + self.MARGIN
        y = area.get('position_y', 0) + self.MARGIN
        w = area.get('width', 2)
        h = area.get('height', 1)

        shape = self.slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(x), Inches(y),
            Inches(w), Inches(h)
        )

        # Style
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(250, 250, 250)
        shape.line.color.rgb = RGBColor(50, 50, 50)
        shape.line.width = Pt(0.75)

        # Label
        tf = shape.text_frame
        tf.text = area.get('name', '')
        tf.paragraphs[0].font.size = Pt(self.FOLDER_FONT_SIZE)
        tf.paragraphs[0].font.name = 'Calibri'

    def _add_device_shape(self, device: dict):
        """Add device rectangle with label"""
        x = device.get('position_x', 0) + self.MARGIN
        y = device.get('position_y', 0) + self.MARGIN
        w = device.get('width', 1.2)
        h = device.get('height', 0.5)

        # Get color
        color = get_device_color(
            device.get('name', ''),
            device.get('device_type')
        )

        shape = self.slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(x), Inches(y),
            Inches(w), Inches(h)
        )

        # Style
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(*color)
        shape.line.color.rgb = RGBColor(0, 0, 0)
        shape.line.width = Pt(0.5)

        # Label
        tf = shape.text_frame
        tf.text = device.get('name', '')
        para = tf.paragraphs[0]
        para.font.size = Pt(self.DEVICE_FONT_SIZE)
        para.font.name = 'Calibri'
        para.alignment = PP_ALIGN.CENTER

    def _add_connection_line(self, link: dict, devices: List[dict]):
        """Add connection line between devices"""
        # Find devices
        from_device = next(
            (d for d in devices if d['id'] == link['from_device_id']),
            None
        )
        to_device = next(
            (d for d in devices if d['id'] == link['to_device_id']),
            None
        )

        if not from_device or not to_device:
            return

        # Calculate connection points
        from app.services.layout_service import LayoutService
        layout = LayoutService()
        from_point, to_point = layout.calculate_connection_points(
            from_device, to_device
        )

        # Adjust for margin
        from_x = from_point['x'] + self.MARGIN
        from_y = from_point['y'] + self.MARGIN
        to_x = to_point['x'] + self.MARGIN
        to_y = to_point['y'] + self.MARGIN

        # Get line color
        purpose = link.get('purpose', '')
        color = get_link_color(purpose)

        # Add connector
        connector = self.slide.shapes.add_connector(
            1,  # Straight connector
            Inches(from_x), Inches(from_y),
            Inches(to_x), Inches(to_y)
        )

        # Style
        line_width = (
            self.LINE_WIDTH_CONTRAST if self.theme == 'contrast'
            else self.LINE_WIDTH_NORMAL
        )
        connector.line.width = Pt(line_width)
        connector.line.color.rgb = RGBColor(*color)
```

### 8.2 Excel Generator Service

```python
# services/excel_generator.py
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from typing import List, Dict
import io

class ExcelGenerator:
    """Generate Excel device files"""

    HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    HEADER_FONT = Font(color="FFFFFF", bold=True)

    def generate_device_file(
        self,
        project_name: str,
        devices: List[dict],
        interfaces: List[dict],
        links: List[dict],
        l2_assignments: List[dict],
        l3_addresses: List[dict]
    ) -> bytes:
        """
        Generate [DEVICE] Excel file with L1/L2/L3 tables.
        Returns Excel file as bytes.
        """
        wb = Workbook()

        # Remove default sheet
        wb.remove(wb.active)

        # Create sheets
        self._create_l1_table(wb, devices, interfaces, links)
        self._create_l2_table(wb, devices, interfaces, l2_assignments)
        self._create_l3_table(wb, devices, interfaces, l3_addresses)
        self._create_attribute_table(wb, devices)

        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.read()

    def _create_l1_table(
        self,
        wb: Workbook,
        devices: List[dict],
        interfaces: List[dict],
        links: List[dict]
    ):
        """Create L1 Table sheet"""
        ws = wb.create_sheet("L1 Table")

        # Headers
        headers = [
            "Area", "Device Name", "Port Mode", "Port Name",
            "Virtual Port Mode", "Virtual Port Name",
            "Connected Device", "Connected Port"
        ]
        ws.append(headers)
        self._style_header_row(ws, len(headers))

        # Data
        for device in devices:
            device_interfaces = [i for i in interfaces if i['device_id'] == device['id']]

            for iface in device_interfaces:
                # Find connected device via links
                connected_device = ""
                connected_port = ""

                for link in links:
                    if link['from_interface_id'] == iface['id']:
                        conn_iface = next(
                            (i for i in interfaces if i['id'] == link['to_interface_id']),
                            None
                        )
                        if conn_iface:
                            conn_device = next(
                                (d for d in devices if d['id'] == conn_iface['device_id']),
                                None
                            )
                            if conn_device:
                                connected_device = conn_device['name']
                                connected_port = conn_iface['name']
                        break
                    elif link['to_interface_id'] == iface['id']:
                        conn_iface = next(
                            (i for i in interfaces if i['id'] == link['from_interface_id']),
                            None
                        )
                        if conn_iface:
                            conn_device = next(
                                (d for d in devices if d['id'] == conn_iface['device_id']),
                                None
                            )
                            if conn_device:
                                connected_device = conn_device['name']
                                connected_port = conn_iface['name']
                        break

                ws.append([
                    device.get('area_name', ''),
                    device['name'],
                    'Physical' if not iface['is_virtual'] else '',
                    iface['name'] if not iface['is_virtual'] else '',
                    'Virtual' if iface['is_virtual'] else '',
                    iface['name'] if iface['is_virtual'] else '',
                    connected_device,
                    connected_port
                ])

        self._auto_column_width(ws)

    def _create_l2_table(
        self,
        wb: Workbook,
        devices: List[dict],
        interfaces: List[dict],
        l2_assignments: List[dict]
    ):
        """Create L2 Table sheet"""
        ws = wb.create_sheet("L2 Table")

        headers = [
            "Area", "Device Name", "L2 IF Name", "L2 IF Type",
            "Connected L2 Segment Name"
        ]
        ws.append(headers)
        self._style_header_row(ws, len(headers))

        # Group assignments by interface
        for assignment in l2_assignments:
            iface = next(
                (i for i in interfaces if i['id'] == assignment['interface_id']),
                None
            )
            if not iface:
                continue

            device = next(
                (d for d in devices if d['id'] == iface['device_id']),
                None
            )
            if not device:
                continue

            ws.append([
                device.get('area_name', ''),
                device['name'],
                iface['name'],
                assignment.get('port_mode', 'access'),
                assignment.get('segment_name', '')
            ])

        self._auto_column_width(ws)

    def _create_l3_table(
        self,
        wb: Workbook,
        devices: List[dict],
        interfaces: List[dict],
        l3_addresses: List[dict]
    ):
        """Create L3 Table sheet"""
        ws = wb.create_sheet("L3 Table")

        headers = [
            "Area", "Device Name", "L3 IF Name", "L3 Instance Name",
            "IP Address / Subnet mask"
        ]
        ws.append(headers)
        self._style_header_row(ws, len(headers))

        for addr in l3_addresses:
            iface = next(
                (i for i in interfaces if i['id'] == addr['interface_id']),
                None
            )
            if not iface:
                continue

            device = next(
                (d for d in devices if d['id'] == iface['device_id']),
                None
            )
            if not device:
                continue

            ip_str = f"{addr['ip_address']}/{addr['prefix_length']}"

            ws.append([
                device.get('area_name', ''),
                device['name'],
                iface['name'],
                addr.get('vrf_name', ''),
                ip_str
            ])

        self._auto_column_width(ws)

    def _create_attribute_table(self, wb: Workbook, devices: List[dict]):
        """Create Attribute Table sheet"""
        ws = wb.create_sheet("Attribute Table")

        headers = ["Device Name", "Device Type", "Model", "Attributes"]
        ws.append(headers)
        self._style_header_row(ws, len(headers))

        for device in devices:
            ws.append([
                device['name'],
                device.get('device_type', ''),
                device.get('model', ''),
                str(device.get('attributes', {}))
            ])

        self._auto_column_width(ws)

    def _style_header_row(self, ws, col_count: int):
        """Apply header styling"""
        for col in range(1, col_count + 1):
            cell = ws.cell(row=1, column=col)
            cell.fill = self.HEADER_FILL
            cell.font = self.HEADER_FONT
            cell.alignment = Alignment(horizontal='center')

    def _auto_column_width(self, ws):
        """Auto-fit column widths"""
        for column_cells in ws.columns:
            max_length = 0
            column = column_cells[0].column_letter
            for cell in column_cells:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column].width = adjusted_width
```

### 8.3 Background Job Worker

```python
# workers/export_worker.py
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.core.config import settings
from app.db.session import async_session_maker
from app.services.pptx_generator import PPTXGenerator
from app.services.excel_generator import ExcelGenerator
from app.services.diagram_service import DiagramService
from app.models.export_job import ExportJob

celery_app = Celery(
    "export_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

@celery_app.task(bind=True)
def export_l1_diagram(self, job_id: str, project_id: str, options: dict):
    """Background task to generate L1 PPTX diagram"""
    async def _run():
        async with async_session_maker() as db:
            try:
                # Update job status
                job = await db.get(ExportJob, job_id)
                job.status = "processing"
                job.started_at = datetime.utcnow()
                await db.commit()

                # Get diagram data
                diagram_service = DiagramService(db)
                data = await diagram_service.get_l1_diagram_data(project_id)

                # Generate PPTX
                generator = PPTXGenerator(theme=options.get('theme', 'default'))
                pptx_bytes = generator.generate_l1_diagram(
                    areas=data['areas'],
                    devices=data['devices'],
                    links=data['links'],
                    settings=options
                )

                # Save file
                output_path = f"exports/{project_id}/L1_Diagram_{job_id}.pptx"
                await save_file(output_path, pptx_bytes)

                # Update job
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                job.result_file_path = output_path
                await db.commit()

                return {"status": "success", "file_path": output_path}

            except Exception as e:
                job.status = "failed"
                job.error_message = str(e)
                await db.commit()
                raise

    return asyncio.get_event_loop().run_until_complete(_run())

@celery_app.task(bind=True)
def export_device_file(self, job_id: str, project_id: str, options: dict):
    """Background task to generate Excel device file"""
    async def _run():
        async with async_session_maker() as db:
            try:
                job = await db.get(ExportJob, job_id)
                job.status = "processing"
                await db.commit()

                # Get all data
                diagram_service = DiagramService(db)
                data = await diagram_service.get_complete_diagram_data(project_id)

                # Generate Excel
                generator = ExcelGenerator()
                excel_bytes = generator.generate_device_file(
                    project_name=data['project_name'],
                    devices=data['devices'],
                    interfaces=data['interfaces'],
                    links=data['links'],
                    l2_assignments=data['l2_assignments'],
                    l3_addresses=data['l3_addresses']
                )

                # Save
                output_path = f"exports/{project_id}/DEVICE_{job_id}.xlsx"
                await save_file(output_path, excel_bytes)

                job.status = "completed"
                job.result_file_path = output_path
                await db.commit()

                return {"status": "success", "file_path": output_path}

            except Exception as e:
                job.status = "failed"
                job.error_message = str(e)
                await db.commit()
                raise

    return asyncio.get_event_loop().run_until_complete(_run())
```

---

## 9. Development Phases

### Phase 1: Foundation (Week 1-2)

**Goals:**
- [ ] Project setup (monorepo structure)
- [ ] Database schema + migrations
- [ ] Authentication system
- [ ] Basic CRUD API for projects/areas/devices

**Deliverables:**
- Backend skeleton with FastAPI
- PostgreSQL + Redis setup
- User registration/login
- Project CRUD endpoints
- Pydantic schemas

**Tasks:**
```
Week 1:
├── Day 1-2: Project scaffolding, venv setup, requirements.txt
├── Day 3-4: Database models (SQLite + SQLAlchemy)
└── Day 5: Auth endpoints (JWT)

Week 2:
├── Day 1-2: Project/Area CRUD APIs
├── Day 3-4: Device/Interface CRUD APIs
└── Day 5: API testing, documentation
```

---

### Phase 2: Data Layer (Week 3-4)

**Goals:**
- [ ] Complete CRUD for all entities
- [ ] Import from Excel/CSV
- [ ] Validation service
- [ ] Sync between layers

**Deliverables:**
- L1 Link management
- L2 Segment/Assignment APIs
- L3 Address APIs
- Excel import endpoint
- Port name normalization

**Tasks:**
```
Week 3:
├── Day 1-2: L1 Link CRUD + validation
├── Day 3-4: L2 Segment + Assignment APIs
└── Day 5: L3 Address APIs

Week 4:
├── Day 1-2: Excel import parser
├── Day 3-4: CSV import parser
└── Day 5: Validation + sync services
```

---

### Phase 3: Frontend Base (Week 5-6)

**Goals:**
- [ ] Vue 3 project setup
- [ ] Auth pages (login/register)
- [ ] Dashboard with project list
- [ ] Project detail page

**Deliverables:**
- Vue 3 + Vite + Pinia setup
- PrimeVue components
- Authentication flow
- Project management UI
- Responsive layout

**Tasks:**
```
Week 5:
├── Day 1-2: Vue project setup, routing
├── Day 3-4: Auth pages, API client
└── Day 5: Dashboard layout

Week 6:
├── Day 1-2: Project list/create UI
├── Day 3-4: Project detail page
└── Day 5: Data tables (devices, links)
```

---

### Phase 4: Diagram Canvas (Week 7-8)

**Goals:**
- [ ] Interactive diagram canvas
- [ ] Render areas, devices, links
- [ ] Selection and editing
- [ ] Pan/zoom controls

**Deliverables:**
- Konva.js integration
- Area rendering
- Device rendering with colors
- Connection line rendering
- Selection state management

**Tasks:**
```
Week 7:
├── Day 1-2: Konva canvas setup
├── Day 3-4: Area + device rendering
└── Day 5: Industry color system

Week 8:
├── Day 1-2: Connection lines
├── Day 3-4: Selection + property panel
└── Day 5: Pan/zoom, minimap
```

---

### Phase 5: Export Engine (Week 9-10)

**Goals:**
- [ ] PPTX generation (L1/L2/L3)
- [ ] Excel device file export
- [ ] Background job processing
- [ ] Download management

**Deliverables:**
- PPTXGenerator service
- ExcelGenerator service
- Celery workers
- Export job tracking
- File download endpoints

**Tasks:**
```
Week 9:
├── Day 1-2: PPTX generator (shapes, colors)
├── Day 3-4: PPTX connections, tags
└── Day 5: L2/L3 diagram variants

Week 10:
├── Day 1-2: Excel generator
├── Day 3-4: Celery setup, workers
└── Day 5: Job status UI, downloads
```

---

### Phase 6: Import & Polish (Week 11-12)

**Goals:**
- [ ] Excel template import
- [ ] Import preview/validation
- [ ] Error handling
- [ ] Performance optimization

**Deliverables:**
- Import wizard UI
- Preview before import
- Validation feedback
- Bulk operations
- Loading states

**Tasks:**
```
Week 11:
├── Day 1-2: Excel parser improvements
├── Day 3-4: Import wizard UI
└── Day 5: Validation feedback

Week 12:
├── Day 1-2: Error handling, edge cases
├── Day 3-4: Performance tuning
└── Day 5: Code cleanup, refactoring
```

---

### Phase 7: Testing & Deployment (Week 13-14)

**Goals:**
- [ ] Unit tests (80%+ coverage)
- [ ] Integration tests
- [ ] E2E tests
- [ ] Production deployment (no Docker)

**Deliverables:**
- pytest test suite
- Playwright E2E tests
- systemd service config (Linux) / NSSM config (Windows)
- Backup scripts
- Deployment documentation

**Tasks:**
```
Week 13:
├── Day 1-2: Backend unit tests
├── Day 3-4: API integration tests
└── Day 5: Frontend component tests

Week 14:
├── Day 1-2: E2E tests (Playwright)
├── Day 3-4: Service config (systemd/NSSM), backup scripts
└── Day 5: Deployment docs, user guide
```

---

## 10. Testing Strategy

### 10.1 Backend Testing

```python
# tests/test_validation_service.py
import pytest
from app.services.validation_service import ValidationService

class TestPortNameNormalization:
    def setup_method(self):
        self.validator = ValidationService()

    def test_normalize_gigabit_ethernet(self):
        assert self.validator.normalize_port_name("Gi 0/1") == "GigabitEthernet 0/1"
        assert self.validator.normalize_port_name("GE 0/1") == "GigabitEthernet 0/1"
        assert self.validator.normalize_port_name("GigabitEthernet 0/1") == "GigabitEthernet 0/1"

    def test_normalize_loopback(self):
        assert self.validator.normalize_port_name("Lo 0") == "Loopback 0"
        assert self.validator.normalize_port_name("Loopback0") == "Loopback 0"

    def test_normalize_vlan(self):
        assert self.validator.normalize_port_name("Vlan 10") == "Vlan 10"
        assert self.validator.normalize_port_name("Vl10") == "Vlan 10"

    def test_invalid_port_name(self):
        assert self.validator.normalize_port_name("invalid") is None
        assert self.validator.normalize_port_name("") is None

class TestIPValidation:
    def setup_method(self):
        self.validator = ValidationService()

    def test_valid_ip(self):
        is_valid, _ = self.validator.validate_ip_address("192.168.1.1/24")
        assert is_valid

    def test_invalid_prefix(self):
        is_valid, msg = self.validator.validate_ip_address("192.168.1.1/33")
        assert not is_valid
        assert "prefix" in msg.lower()

    def test_invalid_octet(self):
        is_valid, msg = self.validator.validate_ip_address("256.168.1.1/24")
        assert not is_valid
        assert "octet" in msg.lower()
```

### 10.2 API Integration Tests

```python
# tests/test_api_projects.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_project():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login first
        login_response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123"
        })
        token = login_response.json()["access_token"]

        # Create project
        response = await client.post(
            "/api/v1/projects/",
            json={"name": "Test Network", "description": "Test project"},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Network"
        assert "id" in data

@pytest.mark.asyncio
async def test_add_device():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # ... auth ...

        # Create area first
        await client.post(f"/api/v1/projects/{project_id}/areas/", json={
            "name": "Core",
            "grid_row": 1,
            "grid_col": 1
        }, headers=headers)

        # Add device
        response = await client.post(
            f"/api/v1/projects/{project_id}/devices/",
            json={
                "name": "Core-SW-1",
                "area_name": "Core",
                "device_type": "Switch",
                "grid_row": 1,
                "grid_col": 1
            },
            headers=headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Core-SW-1"
```

### 10.3 E2E Tests

```typescript
// tests/e2e/diagram-editor.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Diagram Editor', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('[data-testid="email"]', 'test@example.com')
    await page.fill('[data-testid="password"]', 'testpass123')
    await page.click('[data-testid="login-button"]')
    await expect(page).toHaveURL('/dashboard')
  })

  test('should create new project and add devices', async ({ page }) => {
    // Create project
    await page.click('[data-testid="new-project-button"]')
    await page.fill('[data-testid="project-name"]', 'E2E Test Network')
    await page.click('[data-testid="create-project-submit"]')

    // Should redirect to editor
    await expect(page).toHaveURL(/\/projects\/.*\/editor/)

    // Add area
    await page.click('[data-testid="add-area-button"]')
    await page.fill('[data-testid="area-name"]', 'Core')
    await page.click('[data-testid="save-area"]')

    // Verify area appears on canvas
    await expect(page.locator('[data-testid="area-Core"]')).toBeVisible()

    // Add device
    await page.click('[data-testid="add-device-button"]')
    await page.fill('[data-testid="device-name"]', 'Core-SW-1')
    await page.selectOption('[data-testid="device-area"]', 'Core')
    await page.click('[data-testid="save-device"]')

    // Verify device appears
    await expect(page.locator('[data-testid="device-Core-SW-1"]')).toBeVisible()
  })

  test('should export L1 diagram', async ({ page }) => {
    await page.goto('/projects/existing-project/editor')

    // Click export
    await page.click('[data-testid="export-button"]')
    await page.click('[data-testid="export-l1-pptx"]')

    // Wait for job completion
    await expect(page.locator('[data-testid="export-status"]')).toHaveText('Completed', {
      timeout: 60000
    })

    // Download should be available
    await expect(page.locator('[data-testid="download-button"]')).toBeEnabled()
  })
})
```

---

## 11. Deployment (Đơn giản - Không Docker)

> **Mục tiêu:** Deploy đơn giản nhất có thể cho internal team ~5 users.

### 11.1 Yêu cầu hệ thống

| Component | Requirement |
|-----------|-------------|
| **OS** | Windows 10/11, Ubuntu 20.04+, hoặc macOS |
| **Python** | 3.11+ |
| **Node.js** | 20 LTS |
| **RAM** | 4GB minimum |
| **Disk** | 10GB (app + exports) |

### 11.2 Cài đặt Backend

```bash
# 1. Clone repository
git clone https://github.com/your-org/network-sketcher-web.git
cd network-sketcher-web

# 2. Tạo virtual environment
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 3. Cài đặt dependencies
pip install -r requirements.txt

# 4. Tạo file config
cp .env.example .env
# Chỉnh sửa .env nếu cần

# 5. Khởi tạo database (SQLite auto-created)
python -c "from app.database import init_db; init_db()"

# 6. Chạy server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Hoặc với reload cho development
uvicorn app.main:app --reload --port 8000
```

### 11.3 Cài đặt Frontend

```bash
# 1. Di chuyển vào thư mục frontend
cd frontend

# 2. Cài đặt dependencies
npm install

# 3. Build production
npm run build

# 4. Serve với preview server (optional)
npm run preview
```

### 11.4 File cấu hình (.env)

```bash
# backend/.env

# Database (SQLite - tự động tạo file)
DATABASE_URL=sqlite:///./data/network_sketcher.db

# Security
SECRET_KEY=your-secret-key-here-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# Paths
EXPORTS_DIR=./exports
UPLOADS_DIR=./uploads
TEMPLATES_DIR=./templates

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000
```

### 11.5 Chạy như Service (Production)

#### Windows - Task Scheduler hoặc NSSM

```powershell
# Option 1: Dùng NSSM (Non-Sucking Service Manager)
# Download: https://nssm.cc/

nssm install NetworkSketcherBackend
# Path: C:\path\to\venv\Scripts\uvicorn.exe
# Arguments: app.main:app --host 0.0.0.0 --port 8000
# Startup directory: C:\path\to\backend

nssm start NetworkSketcherBackend
```

#### Linux - systemd

```bash
# /etc/systemd/system/network-sketcher.service

[Unit]
Description=Network Sketcher Web Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/network-sketcher-web/backend
Environment="PATH=/opt/network-sketcher-web/backend/venv/bin"
ExecStart=/opt/network-sketcher-web/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Kích hoạt service
sudo systemctl daemon-reload
sudo systemctl enable network-sketcher
sudo systemctl start network-sketcher
sudo systemctl status network-sketcher
```

### 11.6 Nginx Reverse Proxy (Optional)

Chỉ cần nếu expose ra internet hoặc muốn HTTPS.

```nginx
# /etc/nginx/sites-available/network-sketcher

server {
    listen 80;
    server_name network-sketcher.internal;

    # Frontend (static files)
    location / {
        root /opt/network-sketcher-web/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Exports download
    location /exports/ {
        alias /opt/network-sketcher-web/backend/exports/;
    }
}
```

### 11.7 Backup Script

```bash
#!/bin/bash
# backup.sh - Chạy hàng ngày với cron

BACKUP_DIR="/backup/network-sketcher"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/opt/network-sketcher-web/backend"

# Tạo thư mục backup
mkdir -p $BACKUP_DIR

# Backup SQLite database
cp $APP_DIR/data/network_sketcher.db $BACKUP_DIR/db_$DATE.sqlite

# Backup exports folder
tar -czf $BACKUP_DIR/exports_$DATE.tar.gz $APP_DIR/exports/

# Giữ lại 7 ngày backup
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
# Thêm vào crontab (chạy 2AM mỗi ngày)
0 2 * * * /opt/network-sketcher-web/backup.sh >> /var/log/ns-backup.log 2>&1
```

### 11.8 Health Check

Backend có sẵn endpoint `/health`:

```bash
# Check health
curl http://localhost:8000/health

# Response
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0",
  "uptime_seconds": 3600
}
```

### 11.9 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8000 đã dùng | Đổi port trong .env hoặc dừng process khác |
| SQLite locked | Chờ vài giây, hoặc restart service |
| CORS error | Kiểm tra FRONTEND_URL trong .env |
| Import failed | Kiểm tra định dạng Excel, xem logs |
| Export timeout | Tăng timeout trong uvicorn config |

```bash
# Xem logs
tail -f /var/log/network-sketcher.log

# Restart service
sudo systemctl restart network-sketcher
```

---

## 12. Risk Assessment

### 12.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| PPTX rendering differences | High | Medium | Extensive visual testing, compare with CLI output |
| Large diagram performance | Medium | High | Canvas virtualization, pagination, lazy loading |
| SQLite concurrent writes | Low | Low | WAL mode, ~5 users không vấn đề |
| File storage management | Low | Medium | Daily cleanup job, disk monitoring |

### 12.2 Project Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Scope creep | High | High | Strict MVP definition, phase-based delivery |
| Skill gaps | Medium | Medium | Training, pair programming, documentation |
| Timeline slippage | Medium | Medium | Buffer time, priority-based development |
| Integration issues | Medium | Medium | Early integration testing, API contracts |

### 12.3 Mitigation Strategies

**PPTX Rendering:**
- Create automated visual regression tests
- Compare exported PPTX with CLI version side-by-side
- Maintain reference PPTX files for comparison

**Performance:**
- Implement canvas virtualization (only render visible elements)
- Use WebWorkers for heavy computations
- Implement request debouncing and caching

**Scalability:**
- Design for horizontal scaling from day 1
- Use Redis for session/cache sharing
- Implement health checks and graceful degradation

---

## Appendix A: File Structure

```
network-sketcher-web/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── projects.py
│   │   │   │   │   ├── areas.py
│   │   │   │   │   ├── devices.py
│   │   │   │   │   ├── links.py
│   │   │   │   │   ├── l2.py
│   │   │   │   │   ├── l3.py
│   │   │   │   │   ├── exports.py
│   │   │   │   │   └── imports.py
│   │   │   │   └── router.py
│   │   │   └── deps.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── events.py
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── base.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── project.py
│   │   │   ├── area.py
│   │   │   ├── device.py
│   │   │   ├── interface.py
│   │   │   ├── link.py
│   │   │   ├── l2_segment.py
│   │   │   ├── l3_address.py
│   │   │   └── export_job.py
│   │   ├── schemas/
│   │   │   ├── user.py
│   │   │   ├── project.py
│   │   │   ├── area.py
│   │   │   ├── device.py
│   │   │   ├── link.py
│   │   │   └── export.py
│   │   ├── services/
│   │   │   ├── project_service.py
│   │   │   ├── diagram_service.py
│   │   │   ├── validation_service.py
│   │   │   ├── layout_service.py
│   │   │   ├── sync_service.py
│   │   │   ├── pptx_generator.py
│   │   │   ├── excel_generator.py
│   │   │   └── import_service.py
│   │   ├── workers/
│   │   │   └── export_worker.py
│   │   ├── utils/
│   │   │   └── colors.py
│   │   └── main.py
│   ├── tests/
│   ├── data/                    # SQLite database file
│   ├── exports/                 # Generated PPTX/Excel files
│   ├── uploads/                 # Uploaded Excel templates
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── diagram/
│   │   │   ├── editor/
│   │   │   ├── import/
│   │   │   └── export/
│   │   ├── views/
│   │   ├── stores/
│   │   ├── composables/
│   │   ├── utils/
│   │   ├── router/
│   │   ├── assets/
│   │   ├── App.vue
│   │   └── main.ts
│   ├── tests/
│   ├── dist/                    # Built static files
│   ├── package.json
│   └── vite.config.ts
│
├── scripts/
│   ├── install.sh               # Linux install script
│   ├── install.ps1              # Windows install script
│   ├── backup.sh                # Backup script
│   └── start.sh                 # Start all services
│
├── docs/
│   ├── INSTALL.md               # Installation guide
│   ├── USER_GUIDE.md            # User manual
│   └── API.md                   # API documentation
│
└── README.md
```

---

## Appendix B: API Response Examples

### Create Project Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Enterprise Network",
  "description": "Main corporate network topology",
  "theme": "default",
  "areas_count": 0,
  "devices_count": 0,
  "links_count": 0,
  "created_at": "2026-01-23T10:30:00Z",
  "updated_at": "2026-01-23T10:30:00Z"
}
```

### Diagram Data Response

```json
{
  "areas": [
    {
      "id": "area-uuid-1",
      "name": "Core",
      "grid_row": 1,
      "grid_col": 1,
      "position_x": 1.0,
      "position_y": 1.0,
      "width": 4.5,
      "height": 2.0,
      "style": {}
    }
  ],
  "devices": [
    {
      "id": "device-uuid-1",
      "name": "Core-SW-1",
      "area_id": "area-uuid-1",
      "device_type": "Switch",
      "position_x": 1.2,
      "position_y": 1.5,
      "width": 1.2,
      "height": 0.5,
      "color_rgb": [34, 139, 34]
    }
  ],
  "links": [
    {
      "id": "link-uuid-1",
      "from_device_id": "device-uuid-1",
      "to_device_id": "device-uuid-2",
      "from_interface": "Ethernet 1/1",
      "to_interface": "Ethernet 1/1",
      "purpose": "HA"
    }
  ],
  "l2_segments": [...],
  "l3_addresses": [...],
  "settings": {
    "theme": "default",
    "show_interface_tags": true
  }
}
```

### Export Job Response

```json
{
  "job_id": "job-uuid-1",
  "status": "completed",
  "job_type": "l1_diagram",
  "progress": 100,
  "result_file_path": "exports/project-uuid/L1_Diagram_job-uuid-1.pptx",
  "download_url": "/api/v1/exports/download/job-uuid-1",
  "created_at": "2026-01-23T10:35:00Z",
  "completed_at": "2026-01-23T10:35:05Z"
}
```

---

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| **Area** | Network zone/region containing devices (e.g., Core, DMZ, User-Zone) |
| **Device** | Network infrastructure component (router, switch, server, firewall) |
| **Interface** | Physical or virtual port on a device |
| **L1 Link** | Physical connection between two interfaces |
| **L2 Segment** | Layer 2 broadcast domain (VLAN) |
| **L3 Address** | IP address assigned to an interface |
| **Port-Channel** | Aggregated link (LACP/static bonding) |
| **Waypoint** | Routing helper node for diagram line paths |
| **Master File** | Excel file containing complete network topology data |
| **Device File** | Excel export with L1/L2/L3 tables |

---

## 13. Original NS Logic Reference

Section này cung cấp mapping chi tiết giữa source code gốc của Network Sketcher và các component tương ứng trong Web App, giúp developers dễ dàng tham chiếu logic nghiệp vụ.

### 13.1 Source File Overview

```
network-sketcher/
├── ns_def.py                    # Core definitions, utilities, colors
├── ns_cli.py                    # CLI commands, validation
├── ns_ddx_figure.py             # PPTX generation engine
├── ns_l1_master_create.py       # L1 diagram data creation
├── ns_l2_diagram_create.py      # L2 diagram generation
├── ns_l3_diagram_create.py      # L3 diagram generation
├── ns_sync_between_layers.py    # L1↔L2↔L3 synchronization
└── scripts/
    ├── ns_cli_wrapper.py        # CLI wrapper with themes
    ├── import_from_excel.py     # Excel import logic
    └── create_excel_template.py # Template generation
```

### 13.2 Core Definitions (`ns_def.py`)

#### 13.2.1 Port Name Validation

**Original Function:** `split_portname()` (line ~200-250)

```python
# ns_def.py - Phân tách port name thành type và number
def split_portname(portname):
    """
    Tách port name thành (interface_type, number)
    VD: "Ethernet 1/1" → ("Ethernet", "1/1")
        "Gi 0/0/0" → ("Gi", "0/0/0")

    IMPORTANT: NS requires space between type and number!
    "Eth1/1" is INVALID, must be "Eth 1/1"
    """
```

**Web App Equivalent:**
```python
# services/validation_service.py
class ValidationService:
    PORT_PATTERN = re.compile(r'^([A-Za-z-]+)\s+(.+)$')

    def validate_port_name(self, port_name: str) -> tuple[str, str]:
        match = self.PORT_PATTERN.match(port_name)
        if not match:
            raise ValidationError(f"Invalid port format: {port_name}. Must have space between type and number.")
        return match.groups()
```

#### 13.2.2 Industry Color Definitions

**Original Location:** `ns_def.py` (line ~50-100) và CLI theme system

```python
# INDUSTRY_COLORS mapping - Device colors based on name prefix
DEVICE_COLORS = {
    # Routers
    'Router': [70, 130, 180],    # Steel Blue
    'ISP': [70, 130, 180],

    # Firewalls
    'FW': [220, 60, 60],         # Crimson Red
    'Firewall': [220, 60, 60],

    # Switches
    'Core-SW': [34, 139, 34],    # Forest Green
    'Dist': [60, 179, 113],      # Medium Sea Green
    'Access-SW': [0, 139, 139],  # Dark Cyan

    # Servers
    'Server': [106, 90, 205],    # Slate Blue
    'DB': [148, 0, 211],         # Dark Violet
    'App': [138, 43, 226],       # Blue Violet
    'Web': [75, 0, 130],         # Indigo

    # Storage
    'NAS': [210, 105, 30],       # Chocolate
    'SAN': [184, 134, 11],       # Dark Goldenrod

    # End Devices
    'PC': [119, 136, 153],       # Light Slate Gray
    'Workstation': [112, 128, 144],

    # Wireless
    'WiFi': [135, 206, 250],     # Light Sky Blue
    'AP': [135, 206, 250],

    # Default
    '_DEFAULT_': [235, 241, 222],
}

# Link purpose colors (CLI contrast theme)
LINK_PURPOSE_COLORS = {
    'WAN': [70, 130, 180],       # Blue
    'INTERNET': [70, 130, 180],
    'DMZ': [255, 165, 0],        # Orange
    'LAN': [34, 139, 34],        # Green
    'MGMT': [128, 0, 128],       # Purple
    'HA': [128, 128, 128],       # Gray
    'STORAGE': [139, 69, 19],    # Brown
    'BACKUP': [64, 64, 64],      # Dark Gray
    'VPN': [139, 0, 0],          # Dark Red
}
```

**Web App Equivalent:**
```python
# utils/colors.py
def get_device_color(device_name: str) -> list[int]:
    """Auto-assign color based on device name prefix"""
    name_upper = device_name.upper()
    for prefix, color in DEVICE_COLORS.items():
        if prefix.upper() in name_upper:
            return color
    return DEVICE_COLORS['_DEFAULT_']

def get_link_color(purpose: str) -> list[int]:
    """Get link color based on purpose"""
    return LINK_PURPOSE_COLORS.get(purpose.upper(), [0, 0, 0])
```

### 13.3 CLI Commands (`ns_cli.py`)

#### 13.3.1 Command → API Mapping

| CLI Command | Original Function | Web API Endpoint |
|-------------|-------------------|------------------|
| `add area_location` | `add_area_location()` | `POST /api/v1/projects/{id}/areas` |
| `add device_location` | `add_device_location()` | `POST /api/v1/projects/{id}/devices` |
| `add l1_link` | `add_l1_link()` | `POST /api/v1/projects/{id}/links` |
| `add l1_link_bulk` | `add_l1_link_bulk()` | `POST /api/v1/projects/{id}/links/bulk` |
| `add portchannel_bulk` | `add_portchannel_bulk()` | `POST /api/v1/projects/{id}/portchannels/bulk` |
| `add virtual_port_bulk` | `add_virtual_port_bulk()` | `POST /api/v1/projects/{id}/interfaces/virtual/bulk` |
| `add l2_segment_bulk` | `add_l2_segment_bulk()` | `POST /api/v1/projects/{id}/l2-segments/bulk` |
| `add ip_address_bulk` | `add_ip_address_bulk()` | `POST /api/v1/projects/{id}/l3-addresses/bulk` |
| `export l1_diagram` | `export_l1_diagram()` | `POST /api/v1/projects/{id}/export` body: `{type: "l1"}` |
| `export l2_diagram` | `export_l2_diagram()` | `POST /api/v1/projects/{id}/export` body: `{type: "l2"}` |
| `export l3_diagram` | `export_l3_diagram()` | `POST /api/v1/projects/{id}/export` body: `{type: "l3"}` |
| `show device` | `show_device()` | `GET /api/v1/projects/{id}/devices` |
| `show l1_link` | `show_l1_link()` | `GET /api/v1/projects/{id}/links` |

#### 13.3.2 Validation Logic

**Original:** `ns_cli.py` lines ~100-200

```python
# Validation rules from ns_cli.py

def validate_area_exists(area_name, master_data):
    """Area trong devices.csv phải tồn tại trong areas.csv"""
    if area_name not in master_data['areas']:
        raise ValueError(f"Area '{area_name}' not found")

def validate_device_exists(device_name, master_data):
    """Device trong l1_links.csv phải tồn tại trong devices.csv"""
    if device_name not in master_data['devices']:
        raise ValueError(f"Device '{device_name}' not found")

def validate_port_exists(device_name, port_name, master_data):
    """Port trong l2_segments/ip_addresses phải tồn tại"""
    device_ports = master_data['devices'][device_name]['ports']
    if port_name not in device_ports:
        raise ValueError(f"Port '{port_name}' not found on '{device_name}'")
```

**Web App Equivalent:**
```python
# services/validation_service.py
class ValidationService:
    async def validate_topology_integrity(self, project_id: str) -> list[ValidationError]:
        errors = []

        # Check all device areas exist
        devices = await self.device_repo.get_all(project_id)
        areas = {a.name for a in await self.area_repo.get_all(project_id)}
        for device in devices:
            if device.area_name not in areas:
                errors.append(ValidationError(
                    level="error",
                    entity="device",
                    entity_id=device.id,
                    message=f"Device '{device.name}' references non-existent area '{device.area_name}'"
                ))

        # Check all link endpoints exist
        links = await self.link_repo.get_all(project_id)
        device_names = {d.name for d in devices}
        for link in links:
            if link.from_device not in device_names:
                errors.append(...)
            if link.to_device not in device_names:
                errors.append(...)

        return errors
```

### 13.4 PPTX Generation (`ns_ddx_figure.py`)

#### 13.4.1 Key Classes and Methods

**File:** `ns_ddx_figure.py` (~1200 lines)

| Method | Line Range | Purpose | Web App Equivalent |
|--------|------------|---------|-------------------|
| `__init__()` | 50-90 | Initialize with meta Excel template | `PPTXGenerator.__init__()` |
| `add_root_folder()` | 100-150 | Create slide with root folder | `PPTXGenerator.create_slide()` |
| `add_sub_folder()` | 160-300 | Add area folder shapes | `PPTXGenerator.add_area()` |
| `add_shape()` | 350-600 | Add device shapes | `PPTXGenerator.add_device()` |
| `add_line()` | 620-750 | Draw connection lines | `PPTXGenerator.add_link()` |
| `add_line_tag()` | 780-900 | Add interface labels | `PPTXGenerator.add_interface_tag()` |
| `get_shape_width()` | 1077-1120 | Get shape dimensions | Style cache lookup |
| `get_shape_hight()` | 1123-1180 | Get shape height | Style cache lookup |

#### 13.4.2 Caching Optimization

**Original Issue:** `ns_ddx_figure.py` scans 50,000 rows repeatedly for each shape lookup.

```python
# Original inefficient code (line ~1080)
def get_shape_width(self, shape_name):
    for row in range(1, 50001):
        if str(self.input_ppt_mata_excel.active.cell(row, 1).value) == '<<STYLE_SHAPE>>':
            for row2 in range(row + 1, 50001):
                if str(self.input_ppt_mata_excel.active.cell(row2, 1).value) == shape_name:
                    return float(self.input_ppt_mata_excel.active.cell(row2, 2).value)
```

**Web App Optimized:**
```python
# generators/pptx_generator.py
class PPTXGenerator:
    def __init__(self, template_path: str):
        self._style_cache = self._build_style_cache(template_path)

    def _build_style_cache(self, template_path: str) -> dict:
        """Build complete cache at initialization - O(n) once"""
        cache = {}
        wb = openpyxl.load_workbook(template_path)
        ws = wb.active

        in_style_section = False
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
            cell_value = str(row[0].value)
            if cell_value == '<<STYLE_SHAPE>>':
                in_style_section = True
                continue
            if in_style_section:
                if cell_value.startswith('<<'):
                    break
                cache[cell_value] = {
                    'width': float(row[1].value or 1.0),
                    'height': float(row[2].value or 0.5),
                    'degree': float(row[3].value or 0.0),
                    'color': row[4].value,
                }
        return cache

    def get_shape_dimensions(self, shape_name: str) -> tuple[float, float]:
        """O(1) lookup from cache"""
        style = self._style_cache.get(shape_name, self._style_cache['_DEFAULT_'])
        return style['width'], style['height']
```

#### 13.4.3 Connection Point Logic

**Original:** `ns_ddx_figure.py` lines 687-714

```python
# Simplified connection logic - only considers vertical position
def add_line(self, from_coords, to_coords):
    fx_left, fx_mid, fx_right = from_coords[1:4]
    fy_top, fy_mid, fy_down = from_coords[4:7]
    tx_left, tx_mid, tx_right = to_coords[1:4]
    ty_top, ty_mid, ty_down = to_coords[4:7]

    # Current simple logic
    if fy_mid > ty_mid:
        start_point = (fx_mid, fy_top)
        end_point = (tx_mid, ty_down)
    else:
        start_point = (fx_mid, fy_down)
        end_point = (tx_mid, ty_top)
```

**Web App Enhanced:**
```python
# generators/pptx_generator.py
def _get_best_connection_points(self, from_coords, to_coords):
    """Optimized connection point selection to minimize crossings"""
    fx_left, fx_mid, fx_right = from_coords['x_left'], from_coords['x_mid'], from_coords['x_right']
    fy_top, fy_mid, fy_down = from_coords['y_top'], from_coords['y_mid'], from_coords['y_bottom']
    tx_left, tx_mid, tx_right = to_coords['x_left'], to_coords['x_mid'], to_coords['x_right']
    ty_top, ty_mid, ty_down = to_coords['y_top'], to_coords['y_mid'], to_coords['y_bottom']

    dx = tx_mid - fx_mid
    dy = ty_mid - fy_mid

    # Choose sides based on relative direction
    if abs(dx) > abs(dy) * 1.5:  # Horizontal dominant
        if dx > 0:
            return (fx_right, fy_mid), (tx_left, ty_mid)
        else:
            return (fx_left, fy_mid), (tx_right, ty_mid)
    else:  # Vertical dominant
        if dy > 0:
            return (fx_mid, fy_down), (tx_mid, ty_top)
        else:
            return (fx_mid, fy_top), (tx_mid, ty_down)
```

### 13.5 L2 Diagram Creation (`ns_l2_diagram_create.py`)

**File:** `ns_l2_diagram_create.py` (~500 lines)

#### 13.5.1 Key Functions

| Function | Purpose | Web App Mapping |
|----------|---------|-----------------|
| `create_l2_diagram_data()` | Generate L2 topology data | `L2DiagramService.generate()` |
| `get_l2_segments_for_device()` | Get VLANs for a device | `L2SegmentRepository.get_by_device()` |
| `calculate_l2_area_layout()` | Layout L2 groups | `LayoutService.calculate_l2_layout()` |

#### 13.5.2 L2 Segment Grouping Logic

```python
# Original logic from ns_l2_diagram_create.py

def group_devices_by_l2_segment(devices, l2_segments):
    """
    Group devices that share the same L2 segment (VLAN)
    Devices in same VLAN are drawn in same L2 "bubble"
    """
    segment_groups = defaultdict(list)

    for device in devices:
        device_segments = get_device_l2_segments(device)
        for segment in device_segments:
            segment_groups[segment].append(device)

    return segment_groups
```

### 13.6 L3 Diagram Creation (`ns_l3_diagram_create.py`)

**File:** `ns_l3_diagram_create.py` (~600 lines)

#### 13.6.1 Text Size Caching

**Original Optimization:** Lines 43-60

```python
# ns_l3_diagram_create.py - Already has text caching
_text_size_cache = {}

def get_text_wh_cached(text, font_size=6):
    """Cached text width/height calculation"""
    cache_key = (text, font_size)
    if cache_key not in _text_size_cache:
        # Calculate text dimensions using PIL
        font = ImageFont.truetype("arial.ttf", font_size)
        bbox = font.getbbox(text)
        _text_size_cache[cache_key] = (bbox[2] - bbox[0], bbox[3] - bbox[1])
    return _text_size_cache[cache_key]
```

**Web App Equivalent:**
```python
# services/layout_service.py
from functools import lru_cache
from PIL import ImageFont

class LayoutService:
    @lru_cache(maxsize=10000)
    def get_text_dimensions(self, text: str, font_size: int = 6) -> tuple[int, int]:
        """Cached text dimension calculation"""
        font = ImageFont.truetype("arial.ttf", font_size)
        bbox = font.getbbox(text)
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])
```

### 13.7 Layer Synchronization (`ns_sync_between_layers.py`)

**File:** `ns_sync_between_layers.py` (~400 lines)

#### 13.7.1 Sync Rules

```python
# Layer sync rules from ns_sync_between_layers.py

"""
Sync Direction: L1 → L2 → L3

Rules:
1. L1 physical ports auto-create interface entries
2. L2 segment assignment requires interface to exist
3. L3 IP assignment requires interface to exist (can be physical or virtual)
4. Virtual ports (Vlan X, Loopback X) only exist in L2/L3, not L1
5. Port-channel is logical interface in L2/L3, member ports are L1
"""

def sync_l1_to_l2(master_data):
    """Create L2 interface entries from L1 physical connections"""
    for link in master_data['l1_links']:
        # Ensure interfaces exist in L2 tables
        ensure_interface_exists(link['from_device'], link['from_port'])
        ensure_interface_exists(link['to_device'], link['to_port'])

def sync_l2_to_l3(master_data):
    """Carry forward L2 interfaces to L3"""
    for device_name, l2_data in master_data['l2_devices'].items():
        for interface in l2_data['interfaces']:
            ensure_l3_interface_exists(device_name, interface)
```

**Web App Equivalent:**
```python
# services/sync_service.py
class SyncService:
    async def sync_layers(self, project_id: str, source_layer: str = "l1"):
        """
        Synchronize data between layers.
        L1 changes propagate to L2, L2 changes propagate to L3.
        """
        if source_layer == "l1":
            await self._sync_l1_to_l2(project_id)
            await self._sync_l2_to_l3(project_id)
        elif source_layer == "l2":
            await self._sync_l2_to_l3(project_id)

    async def _sync_l1_to_l2(self, project_id: str):
        """Ensure all L1 physical interfaces exist in L2 layer"""
        links = await self.link_repo.get_all(project_id)
        for link in links:
            await self.interface_repo.ensure_exists(
                project_id, link.from_device_id, link.from_port, layer="l2"
            )
            await self.interface_repo.ensure_exists(
                project_id, link.to_device_id, link.to_port, layer="l2"
            )
```

### 13.8 Excel Import Logic (`scripts/import_from_excel.py`)

#### 13.8.1 Sheet Processing Order

```python
# Import order is critical - dependencies must be satisfied

IMPORT_ORDER = [
    'Areas',        # 1. Define areas first
    'Devices',      # 2. Devices reference areas
    'L1_Links',     # 3. Links reference devices
    'PortChannels', # 4. Port-channels reference physical ports
    'VirtualPorts', # 5. Virtual ports reference devices
    'L2_Segments',  # 6. L2 segments reference ports (physical or virtual)
    'IP_Addresses', # 7. IPs reference ports
]
```

**Web App Import Service:**
```python
# services/import_service.py
class ImportService:
    IMPORT_ORDER = [
        ('Areas', AreaImporter),
        ('Devices', DeviceImporter),
        ('L1_Links', LinkImporter),
        ('PortChannels', PortChannelImporter),
        ('VirtualPorts', VirtualPortImporter),
        ('L2_Segments', L2SegmentImporter),
        ('IP_Addresses', IPAddressImporter),
    ]

    async def import_excel(self, project_id: str, file_path: str) -> ImportResult:
        result = ImportResult()
        wb = openpyxl.load_workbook(file_path)

        async with self.db.begin():
            for sheet_name, importer_class in self.IMPORT_ORDER:
                if sheet_name in wb.sheetnames:
                    importer = importer_class(self.db)
                    sheet_result = await importer.import_sheet(
                        project_id, wb[sheet_name]
                    )
                    result.merge(sheet_result)

        return result
```

### 13.9 CLI Wrapper Theme Support (`scripts/ns_cli_wrapper.py`)

#### 13.9.1 Theme Application

```python
# ns_cli_wrapper.py - Theme argument support

def cmd_export(args):
    theme = args.theme  # e.g., "contrast"

    export_args = ['export', f'{diagram_type}_diagram', '--mode', mode, '--master', master_file]
    if theme:
        export_args.extend(['--theme', theme])

    run_ns(export_args)
```

**Web App Theme System:**
```python
# models/export.py
class ExportRequest(BaseModel):
    project_id: str
    diagram_type: Literal["l1", "l2", "l3", "all"]
    mode: Literal["all_areas", "per_area"] = "all_areas"
    theme: Literal["default", "contrast", "dark", "light"] = "default"
    format: Literal["pptx", "pdf", "png"] = "pptx"

# services/theme_service.py
class ThemeService:
    THEMES = {
        "default": DefaultTheme(),
        "contrast": ContrastTheme(),  # Purpose-based link colors
        "dark": DarkTheme(),
        "light": LightTheme(),
    }

    def get_theme(self, name: str) -> Theme:
        return self.THEMES.get(name, self.THEMES["default"])
```

### 13.10 Quick Reference Table

| NS Function/File | Location | Web App Service | Web App File |
|------------------|----------|-----------------|--------------|
| `split_portname()` | `ns_def.py:200` | `ValidationService.validate_port_name()` | `services/validation.py` |
| `get_device_color()` | `ns_def.py:50` | `ColorService.get_device_color()` | `utils/colors.py` |
| `add_l1_link()` | `ns_cli.py:150` | `LinkService.create()` | `services/link.py` |
| `add_shape()` | `ns_ddx_figure.py:350` | `PPTXGenerator.add_device()` | `generators/pptx.py` |
| `add_line()` | `ns_ddx_figure.py:620` | `PPTXGenerator.add_link()` | `generators/pptx.py` |
| `get_shape_width()` | `ns_ddx_figure.py:1077` | `StyleCache.get_dimensions()` | `generators/pptx.py` |
| `sync_l1_to_l2()` | `ns_sync_between_layers.py:100` | `SyncService.sync_layers()` | `services/sync.py` |
| `create_l2_diagram_data()` | `ns_l2_diagram_create.py:50` | `L2DiagramService.generate()` | `services/diagram.py` |
| `get_text_wh_cached()` | `ns_l3_diagram_create.py:43` | `LayoutService.get_text_dimensions()` | `services/layout.py` |

---

*Document Version: 1.1 | Last Updated: 2026-01-23*
