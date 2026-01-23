# Kế hoạch phát triển Ứng dụng Web Network Sketcher

> **Phiên bản:** 1.2
> **Tạo:** 2026-01-23
> **Cập nhật:** 2026-01-23
> **Trạng thái:** Lập kế hoạch
> **Thời lượng ước tính:** 10-14 tuần (MVP + đầy đủ tính năng)
> **Người dùng mục tiêu:** ~5 người dùng đồng thời (nội bộ)

### 📋 Tóm tắt kiến trúc (đơn giản hóa)

| Thành phần | Công nghệ | Ghi chú |
|-----------|------------|-------|
| **Backend** | FastAPI + Python 3.11+ | Chạy trực tiếp, không Docker |
| **Frontend** | Vue 3 + Vite | File tĩnh phục vụ bởi Nginx hoặc backend |
| **Database** | SQLite | Single file, không cần DB server |
| **Job Worker** | Worker nhẹ dựa trên DB | Poller async + ProcessPool (không Redis/Celery) |
| **Triển khai** | systemd (Linux) / NSSM (Windows) | Dịch vụ hệ điều hành gốc |
| **Sao lưu** | sqlite3 .backup + cron | Sao lưu SQLite an toàn hằng ngày |

---

## Mục lục

1. [Tóm tắt điều hành](#1-tom-tat-dieu-hanh)
2. [Tổng quan kiến trúc](#2-tong-quan-kien-truc)
3. [Ngăn xếp công nghệ](#3-ngan-xep-cong-nghe)
4. [Mô hình dữ liệu](#4-mo-hinh-du-lieu)
5. [Thiết kế API backend](#5-thiet-ke-api-backend)
6. [Thiết kế frontend](#6-thiet-ke-frontend)
7. [Triển khai logic nghiệp vụ cốt lõi](#7-trien-khai-logic-nghiep-vu-cot-loi)
8. [Bộ máy xuất](#8-bo-may-xuat)
9. [Các giai đoạn phát triển](#9-cac-giai-doan-phat-trien)
10. [Chiến lược kiểm thử](#10-chien-luoc-kiem-thu)
11. [Triển khai](#11-trien-khai)
12. [Đánh giá rủi ro](#12-danh-gia-rui-ro)
13. [**Tham chiếu logic NS gốc**](#13-tham-chieu-logic-ns-goc) ← MỚI

---

## 1. Tóm tắt điều hành

### 1.1 Mục tiêu dự án

Xây dựng Web Application mới hoàn toàn để thay thế Network Sketcher CLI/GUI, đảm bảo:
- ✅ 100% business logic compatibility
- ✅ Xem trước sơ đồ thời gian thực trên trình duyệt
- ✅ Xuất PPTX/Excel đầy đủ chức năng
- ✅ Multi-user support với project management
- ✅ Modern, responsive UI

### 1.2 Sản phẩm bàn giao chính

| Deliverable | Description |
|-------------|-------------|
| **Bảng điều khiển web** | Quản lý dự án, thư viện mẫu |
| **Trình biên tập sơ đồ** | Trình biên tập topo mạng tương tác |
| **Xem trước trực tiếp** | Kết xuất SVG/Canvas thời gian thực |
| **Bộ máy xuất** | Sinh PPTX/Excel qua API |
| **Nhập dữ liệu** | Tải lên và phân tích Excel/CSV |

### 1.3 Tiêu chí thành công

- [ ] Tạo được diagram L1/L2/L3 từ Excel input
- [ ] Xuất PPTX với bố cục tương tự phiên bản CLI
- [ ] Xuất file thiết bị Excel với đầy đủ bảng L1/L2/L3
- [ ] Xem trước sơ đồ thời gian thực trên trình duyệt
- [ ] Support 1000+ devices per project
- [ ] Thời gian phản hồi < 3s cho tạo sơ đồ

---

## 2. Tổng quan kiến trúc

### 2.1 Kiến trúc cấp cao

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │   Vue 3 SPA     │  │  Canvas sơ đồ   │  │   Xem trước xuất    │  │
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
│   Endpoints   │     │ (thời gian thực)│     │   (worker DB)       │
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
│   SQLite      │     │   Job Worker    │     │   File Storage      │
│   (data)      │     │   (DB poller)   │     │   (Local FS)        │
└───────────────┘     └─────────────────┘     └─────────────────────┘
```

> **Lưu ý:** Kiến trúc đơn giản hóa cho ~5 người dùng đồng thời. Không cần Redis/PostgreSQL.
> Nếu scale lên 20+ người dùng, có thể nâng cấp lên PostgreSQL + Redis.

### 2.2 Trách nhiệm thành phần

| Thành phần | Trách nhiệm |
|-----------|----------------|
| **Vue 3 SPA** | Kết xuất UI, quản lý trạng thái, định tuyến |
| **Canvas Konva.js** | Chỉnh sửa sơ đồ tương tác, xem trước thời gian thực |
| **Backend FastAPI** | REST API, WebSocket, logic nghiệp vụ |
| **Job nền** | Sinh PPTX/Excel (worker dựa trên DB, async + ProcessPool) |
| **SQLite** | Lưu trữ dữ liệu bền vững (đơn giản, không cần máy chủ DB) |
| **Lưu trữ tệp** | Tệp sinh ra, template tải lên (hệ thống tệp cục bộ) |

### 2.3 Luồng dữ liệu

```
Thao tác người dùng → Giao diện → API → Dịch vụ → Kho dữ liệu → Cơ sở dữ liệu
                                  ↓
                          Worker xuất → Lưu trữ tệp → URL tải về
```

---

## 3. Ngăn xếp công nghệ

### 3.1 Backend (máy chủ)

| Hạng mục | Công nghệ | Lý do |
|----------|------------|-----------|
| **Khung** | FastAPI 0.110+ | Hỗ trợ async gốc, OpenAPI, hệ sinh thái Python |
| **ORM** | SQLAlchemy 2.0 | Hỗ trợ async, trưởng thành |
| **Cơ sở dữ liệu** | **SQLite 3 + aiosqlite** | Đơn giản, thân thiện async, phù hợp cho ~5 người dùng |
| **Job Worker** | Worker nhẹ dựa trên DB | Poller async + ProcessPool (không Redis) |
| **Sinh PPTX** | python-pptx | Chuẩn phổ biến |
| **Nhập/Xuất Excel** | openpyxl | Hỗ trợ Excel đầy đủ |
| **Xem trước PDF** | WeasyPrint / reportlab | Sinh bản xem trước (tùy chọn) |

#### 📌 Về việc sử dụng SQLite cho ~5 người dùng

**Kết luận: SQLite là lựa chọn phù hợp cho ~5 người dùng đồng thời.**

| Tiêu chí | SQLite | PostgreSQL |
|----------|--------|------------|
| **Thiết lập** | Không cần cấu hình, 1 tệp | Cần cài máy chủ DB |
| **Ghi đồng thời** | 1 tiến trình ghi tại một thời điểm | Không giới hạn |
| **Đọc đồng thời** | Không giới hạn | Không giới hạn |
| **Hiệu năng (5 người dùng)** | Đủ tốt | Dư thừa |
| **Sao lưu** | Sao chép 1 tệp | pg_dump |
| **Triển khai** | Đơn giản (1 container) | 2+ container |

**Khi nào cần nâng cấp lên PostgreSQL:**
- Hơn 20 người dùng đồng thời
- Cần tìm kiếm toàn văn phức tạp
- Cần cộng tác thời gian thực (nhiều người dùng chỉnh cùng dự án)
- Cần mở rộng ngang

**SQLite configuration tối ưu:**
```python
# database.py
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

engine = create_async_engine(
    "sqlite+aiosqlite:///./network_sketcher.db",
    connect_args={
        "check_same_thread": False,  # Cho phép multi-thread
        "timeout": 30,               # Chờ 30s để lấy khóa ghi
    },
    pool_pre_ping=True,
)

# Bật chế độ WAL để tăng khả năng đồng thời
async with engine.begin() as conn:
    await conn.execute(text("PRAGMA journal_mode=WAL"))
    await conn.execute(text("PRAGMA busy_timeout=30000"))
```

### 3.2 Frontend (giao diện)

| Hạng mục | Công nghệ | Lý do |
|----------|------------|-----------|
| **Khung** | Vue 3 + Composition API | Nhẹ, phản ứng tốt |
| **Công cụ build** | Vite 5 | HMR nhanh, bundling hiện đại |
| **Quản lý trạng thái** | Pinia | Chính thức cho Vue 3, an toàn kiểu |
| **Thư viện UI** | PrimeVue / Naive UI | Thành phần doanh nghiệp |
| **Canvas sơ đồ** | Konva.js + vue-konva | Kết xuất canvas 2D nhanh |
| **Biểu tượng** | Heroicons / Lucide | Bộ icon hiện đại |
| **HTTP client** | Axios / ofetch | Xử lý request |
| **WebSocket** | Native WebSocket | Cập nhật thời gian thực (không Socket.IO) |

### 3.3 DevOps (đơn giản hóa cho ~5 người dùng)

> **Triết lý:** Không sử dụng Docker. Chạy trực tiếp trên máy chủ với Python + Node.js.

| Hạng mục | Công nghệ | Lý do |
|----------|------------|-------|
| **Trình quản lý tiến trình** | systemd / NSSM | Dịch vụ backend + worker |
| **Reverse proxy** | Nginx (tùy chọn) | Chỉ cần nếu internet công khai |
| **Sao lưu** | sqlite3 .backup + cron | Sao lưu an toàn cho SQLite + exports |
| **Ghi log** | Python logging → file | Đơn giản, đủ cho nhóm nhỏ |
| **Giám sát** | Endpoint health check | Endpoint API `/health` |

#### Tại sao không dùng Docker?

| Khía cạnh | Docker | Thuần hệ điều hành |
|--------|--------|--------|
| **Độ dốc học** | Cần học Docker, compose | Không cần |
| **Gỡ lỗi** | Phức tạp hơn | Trực tiếp |
| **Chi phí tài nguyên** | ~200MB+ RAM/container | Tối thiểu |
| **Thời gian cài đặt** | 30+ phút | 10 phút |
| **Phù hợp cho** | Quy mô production, CI/CD | Công cụ nội bộ, ~5 người dùng |

**Khi nào nên dùng Docker:**
- Cần triển khai trên nhiều máy chủ
- Cần CI/CD tự động
- Team có kinh nghiệm Docker
- Scale lên 50+ người dùng

---

## 4. Mô hình dữ liệu

### 4.1 Sơ đồ quan hệ thực thể

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

### 4.2 Lược đồ cơ sở dữ liệu (SQLite)

> UUID v4 được generate ở tầng ứng dụng (Python) và lưu dưới dạng TEXT.  
> Các cột JSON lưu dạng TEXT (dùng JSON1 nếu cần query).

```sql
-- Users & Authentication
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    role TEXT DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Projects
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    owner_id TEXT REFERENCES users(id),
    name TEXT NOT NULL,
    description TEXT,
    settings TEXT DEFAULT '{}',
    theme TEXT DEFAULT 'default',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Areas (Network Zones)
CREATE TABLE areas (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    grid_row INTEGER NOT NULL,
    grid_col INTEGER NOT NULL,
    description TEXT,
    position_x REAL,
    position_y REAL,
    width REAL,
    height REAL,
    style TEXT DEFAULT '{}',
    is_waypoint_area INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, name)
);

-- Devices
CREATE TABLE devices (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    area_id TEXT REFERENCES areas(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    device_type TEXT,
    model TEXT,
    grid_row INTEGER,
    grid_col INTEGER,
    position_x REAL,
    position_y REAL,
    width REAL,
    height REAL,
    color_rgb TEXT, -- JSON array, e.g. [255,0,0]
    is_waypoint INTEGER DEFAULT 0,
    attributes TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, name)
);

-- Interfaces (Physical + Virtual)
CREATE TABLE interfaces (
    id TEXT PRIMARY KEY,
    device_id TEXT REFERENCES devices(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    interface_type TEXT, -- physical, virtual, loopback, svi, port-channel
    normalized_name TEXT,
    slot INTEGER,
    port INTEGER,
    is_virtual INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(device_id, name)
);

-- L1 Links (Physical Connections)
CREATE TABLE l1_links (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    from_interface_id TEXT REFERENCES interfaces(id) ON DELETE CASCADE,
    to_interface_id TEXT REFERENCES interfaces(id) ON DELETE CASCADE,
    purpose TEXT, -- WAN, LAN, DMZ, MGMT, HA, STORAGE, BACKUP, VPN
    cable_type TEXT,
    speed TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(from_interface_id, to_interface_id)
);

-- L2 Segments (VLANs)
CREATE TABLE l2_segments (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    vlan_id INTEGER,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, name)
);

-- Interface L2 Assignment
CREATE TABLE interface_l2_assignments (
    id TEXT PRIMARY KEY,
    interface_id TEXT REFERENCES interfaces(id) ON DELETE CASCADE,
    l2_segment_id TEXT REFERENCES l2_segments(id) ON DELETE CASCADE,
    port_mode TEXT, -- access, trunk
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(interface_id, l2_segment_id)
);

-- L3 Addresses
CREATE TABLE l3_addresses (
    id TEXT PRIMARY KEY,
    interface_id TEXT REFERENCES interfaces(id) ON DELETE CASCADE,
    ip_address TEXT NOT NULL,
    prefix_length INTEGER NOT NULL,
    vrf_name TEXT,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Port Channels
CREATE TABLE port_channels (
    id TEXT PRIMARY KEY,
    device_id TEXT REFERENCES devices(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    channel_number INTEGER,
    mode TEXT, -- LACP, static
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(device_id, name)
);

-- Port Channel Members
CREATE TABLE port_channel_members (
    port_channel_id TEXT REFERENCES port_channels(id) ON DELETE CASCADE,
    interface_id TEXT REFERENCES interfaces(id) ON DELETE CASCADE,
    PRIMARY KEY (port_channel_id, interface_id)
);

-- Export Jobs
CREATE TABLE export_jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES users(id),
    job_type TEXT NOT NULL, -- l1_diagram, l2_diagram, l3_diagram, device_file
    status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
    options TEXT DEFAULT '{}',
    result_file_path TEXT,
    error_message TEXT,
    started_at DATETIME,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_devices_project ON devices(project_id);
CREATE INDEX idx_devices_area ON devices(area_id);
CREATE INDEX idx_interfaces_device ON interfaces(device_id);
CREATE INDEX idx_l1_links_project ON l1_links(project_id);
CREATE INDEX idx_export_jobs_project ON export_jobs(project_id);
CREATE INDEX idx_export_jobs_status ON export_jobs(status);
```

### 4.3 Mô hình Pydantic (API)

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

## 5. Thiết kế API backend

### 5.1 Tổng quan endpoint API

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
│       ├── POST   /l1-diagram    # Xuất PPTX L1 (job async)
│       ├── POST   /l2-diagram    # Xuất PPTX L2 (job async)
│       ├── POST   /l3-diagram    # Xuất PPTX L3 (job async)
│       ├── POST   /device-file   # Xuất file thiết bị Excel
│       ├── POST   /master-file   # Xuất Excel master
│       ├── GET    /jobs          # Liệt kê job xuất
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

### 5.2 Sự kiện WebSocket

```
WS /ws/projects/{project_id}

Events (Server → Client):
├── diagram.updated           # Diagram data changed
├── export.progress           # Tiến độ job xuất (0-100%)
├── export.completed          # Xuất hoàn tất, sẵn sàng tải về
├── export.failed             # Lỗi xuất
├── user.joined               # Another user opened project
└── user.left                 # User left project

Events (Client → Server):
├── diagram.subscribe         # Subscribe to diagram updates
├── diagram.unsubscribe       # Unsubscribe
└── cursor.move               # Share cursor position (collaboration)
```

### 5.3 Ví dụ triển khai API

```python
# api/v1/endpoints/projects.py
from fastapi import APIRouter, Depends, HTTPException
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
    options: dict = {},
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Xếp hàng job xuất sơ đồ L1 (worker DB sẽ xử lý)"""
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

## 6. Thiết kế frontend

### 6.1 Cấu trúc trang

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
│       ├── /export           # Tùy chọn xuất
│       └── /settings         # Project settings
└── /templates                # Template gallery
```

### 6.2 Kiến trúc component

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
│   │   ├── DiagramToolbar.vue      # Điều khiển zoom, kéo, xuất
│   │   ├── PropertyPanel.vue       # Selected item properties
│   │   └── MiniMap.vue             # Minimap tổng quan
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
│   │   ├── ExcelImporter.vue       # Tải lên Excel + xem trước
│   │   ├── CSVImporter.vue         # CSV upload + mapping
│   │   ├── ImportPreview.vue       # Xem trước khi nhập
│   │   └── ImportProgress.vue      # Import status
│   │
│   └── export/
│       ├── ExportDialog.vue        # Tùy chọn xuất modal
│       ├── ExportProgress.vue      # Job progress
│       └── ExportHistory.vue       # Lịch sử xuất
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
│   └── export.ts                   # Trạng thái job xuất
│
├── composables/
│   ├── useDiagram.ts               # Diagram manipulation
│   ├── useExport.ts                # Thao tác xuất
│   ├── useWebSocket.ts             # Real-time updates
│   └── useDeviceColors.ts          # Industry color mapping
│
└── utils/
    ├── api.ts                      # API client
    ├── colors.ts                   # Color utilities
    ├── validation.ts               # Port name, IP validation
    └── layout.ts                   # Layout algorithms
```

### 6.3 Triển khai canvas sơ đồ

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

### 6.4 Triển khai hệ màu

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

### 6.5 Lưu ý khi kết hợp Vue 3 + Konva.js

- Dùng `vue-konva` làm lớp tích hợp chính; hạn chế thao tác DOM trực tiếp với Konva.
- Dữ liệu logic và dữ liệu hiển thị phải tách riêng để hỗ trợ zoom/pan nhất quán.
- Tránh tạo lại node Konva khi dữ liệu đổi nhỏ; cập nhật thuộc tính và gọi `batchDraw()`.
- Tách layer tĩnh/động, chỉ bật `draggable` khi cần để giảm chi phí render.
- Với sơ đồ lớn, áp dụng cắt giảm hiển thị/virtualization (chỉ render phần đang thấy).
- Luôn xử lý resize container để cập nhật kích thước `Stage` nhất quán.

---

## 7. Triển khai logic nghiệp vụ cốt lõi

### 7.1 Dịch vụ kiểm tra hợp lệ

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

### 7.2 Dịch vụ thuật toán bố trí

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

### 7.3 Dịch vụ đồng bộ

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

## 8. Bộ máy xuất

### 8.1 Dịch vụ sinh PPTX

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

### 8.2 Dịch vụ sinh Excel

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

### 8.3 Trình xử lý job nền (dựa trên DB, nhẹ)

```python
# workers/export_worker.py
import asyncio
from datetime import datetime
from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.export_job import ExportJob
from app.services.export_service import ExportService

POLL_INTERVAL_SEC = 2

async def run_worker():
    """
    Tiến trình worker đơn (Option A).
    Polls SQLite for pending jobs and processes them sequentially.
    Tác vụ PPTX/Excel nặng nên chạy qua ProcessPool bên trong ExportService.
    """
    while True:
        async with async_session_maker() as db:
            job = await db.scalar(
                select(ExportJob)
                .where(ExportJob.status == "pending")
                .order_by(ExportJob.created_at)
                .limit(1)
            )

            if not job:
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue

            job.status = "processing"
            job.started_at = datetime.utcnow()
            await db.commit()

            service = ExportService(db)
            try:
                await service.process_export_job(job)
                job.status = "completed"
                job.completed_at = datetime.utcnow()
            except Exception as exc:
                job.status = "failed"
                job.error_message = str(exc)
            finally:
                await db.commit()

        await asyncio.sleep(0)  # yield to event loop

if __name__ == "__main__":
    asyncio.run(run_worker())
```

---

## 9. Các giai đoạn phát triển

### Giai đoạn 1: Nền tảng (Tuần 1-2)

**Mục tiêu:**
- [ ] Thiết lập dự án (cấu trúc monorepo)
- [ ] Lược đồ CSDL + migration
- [ ] Hệ thống xác thực
- [ ] API CRUD cơ bản cho dự án/khu vực/thiết bị

**Sản phẩm bàn giao:**
- Khung backend với FastAPI
- Thiết lập SQLite + SQLAlchemy async
- Đăng ký/đăng nhập người dùng
- Endpoint CRUD dự án
- Lược đồ Pydantic

**Công việc:**
```
Tuần 1:
├── Ngày 1-2: Dựng khung dự án, thiết lập venv, requirements.txt
├── Ngày 3-4: Mô hình CSDL (SQLite + SQLAlchemy)
└── Ngày 5: Endpoint xác thực (JWT)

Tuần 2:
├── Ngày 1-2: API CRUD Dự án/Khu vực
├── Ngày 3-4: API CRUD Thiết bị/Giao diện
└── Ngày 5: Kiểm thử API, tài liệu hóa
```

---

### Giai đoạn 2: Tầng dữ liệu (Tuần 3-4)

**Mục tiêu:**
- [ ] Hoàn thiện CRUD cho tất cả thực thể
- [ ] Nhập từ Excel/CSV
- [ ] Dịch vụ kiểm tra hợp lệ
- [ ] Đồng bộ giữa các lớp

**Sản phẩm bàn giao:**
- Quản lý liên kết L1
- API phân đoạn L2/gán cổng
- API địa chỉ L3
- Endpoint nhập Excel
- Chuẩn hóa tên cổng

**Công việc:**
```
Tuần 3:
├── Ngày 1-2: CRUD liên kết L1 + kiểm tra hợp lệ
├── Ngày 3-4: API phân đoạn L2 + gán cổng
└── Ngày 5: API địa chỉ L3

Tuần 4:
├── Ngày 1-2: Parser nhập Excel
├── Ngày 3-4: Parser nhập CSV
└── Ngày 5: Dịch vụ kiểm tra hợp lệ + đồng bộ
```

---

### Giai đoạn 3: Nền frontend (Tuần 5-6)

**Mục tiêu:**
- [ ] Thiết lập dự án Vue 3
- [ ] Trang xác thực (đăng nhập/đăng ký)
- [ ] Dashboard với danh sách dự án
- [ ] Trang chi tiết dự án

**Sản phẩm bàn giao:**
- Thiết lập Vue 3 + Vite + Pinia
- Thành phần PrimeVue
- Luồng xác thực
- UI quản lý dự án
- Bố cục đáp ứng

**Công việc:**
```
Tuần 5:
├── Ngày 1-2: Thiết lập dự án Vue, routing
├── Ngày 3-4: Trang xác thực, client API
└── Ngày 5: Bố cục dashboard

Tuần 6:
├── Ngày 1-2: UI danh sách/tạo dự án
├── Ngày 3-4: Trang chi tiết dự án
└── Ngày 5: Bảng dữ liệu (thiết bị, liên kết)
```

---

### Giai đoạn 4: Canvas sơ đồ (Tuần 7-8)

**Mục tiêu:**
- [ ] Canvas sơ đồ tương tác
- [ ] Kết xuất khu vực, thiết bị, liên kết
- [ ] Chọn lựa và chỉnh sửa
- [ ] Điều khiển kéo/thu phóng

**Sản phẩm bàn giao:**
- Tích hợp Konva.js
- Kết xuất khu vực
- Kết xuất thiết bị theo màu
- Kết xuất đường kết nối
- Quản lý trạng thái chọn

**Công việc:**
```
Tuần 7:
├── Ngày 1-2: Thiết lập canvas Konva
├── Ngày 3-4: Kết xuất khu vực + thiết bị
└── Ngày 5: Hệ màu theo ngành

Tuần 8:
├── Ngày 1-2: Đường kết nối
├── Ngày 3-4: Chọn lựa + bảng thuộc tính
└── Ngày 5: Kéo/thu phóng, bản đồ nhỏ
```

---

### Giai đoạn 5: Bộ máy xuất (Tuần 9-10)

**Mục tiêu:**
- [ ] Sinh PPTX (L1/L2/L3)
- [ ] Xuất file thiết bị Excel
- [ ] Xử lý job nền
- [ ] Quản lý tải về

**Sản phẩm bàn giao:**
- Dịch vụ PPTXGenerator
- Dịch vụ ExcelGenerator
- Worker xuất dựa trên DB (poller)
- Theo dõi job xuất
- Endpoint tải file

**Công việc:**
```
Tuần 9:
├── Ngày 1-2: PPTX generator (hình, màu)
├── Ngày 3-4: Kết nối PPTX, nhãn
└── Ngày 5: Biến thể sơ đồ L2/L3

Tuần 10:
├── Ngày 1-2: Excel generator
├── Ngày 3-4: Worker xuất (DB poller + ProcessPool)
└── Ngày 5: UI trạng thái job, tải về
```

---

### Giai đoạn 6: Nhập liệu & hoàn thiện (Tuần 11-12)

**Mục tiêu:**
- [ ] Nhập template Excel
- [ ] Xem trước/kiểm tra hợp lệ nhập liệu
- [ ] Xử lý lỗi
- [ ] Tối ưu hiệu năng

**Sản phẩm bàn giao:**
- UI wizard nhập liệu
- Xem trước khi nhập
- Phản hồi kiểm tra hợp lệ
- Thao tác hàng loạt
- Trạng thái tải

**Công việc:**
```
Tuần 11:
├── Ngày 1-2: Cải thiện parser Excel
├── Ngày 3-4: UI wizard nhập liệu
└── Ngày 5: Phản hồi kiểm tra hợp lệ

Tuần 12:
├── Ngày 1-2: Xử lý lỗi, trường hợp biên
├── Ngày 3-4: Tinh chỉnh hiệu năng
└── Ngày 5: Dọn dẹp code, refactor
```

---

### Giai đoạn 7: Kiểm thử & triển khai (Tuần 13-14)

**Mục tiêu:**
- [ ] Unit test (coverage 80%+)
- [ ] Kiểm thử tích hợp
- [ ] Kiểm thử E2E
- [ ] Triển khai production (không Docker)

**Sản phẩm bàn giao:**
- Bộ test pytest
- Kiểm thử E2E Playwright
- Cấu hình dịch vụ systemd (Linux) / cấu hình NSSM (Windows)
- Script sao lưu
- Tài liệu triển khai

**Công việc:**
```
Tuần 13:
├── Ngày 1-2: Unit test backend
├── Ngày 3-4: Kiểm thử tích hợp API
└── Ngày 5: Kiểm thử component frontend

Tuần 14:
├── Ngày 1-2: Kiểm thử E2E (Playwright)
├── Ngày 3-4: Cấu hình dịch vụ (systemd/NSSM), script sao lưu
└── Ngày 5: Tài liệu triển khai, hướng dẫn người dùng
```

---

## 10. Chiến lược kiểm thử

### 10.1 Kiểm thử backend

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

### 10.2 Kiểm thử tích hợp API

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

### 10.3 Kiểm thử E2E

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

## 11. Triển khai (đơn giản - không Docker)

> **Mục tiêu:** Triển khai đơn giản nhất có thể cho đội nội bộ ~5 người dùng.

### 11.1 Yêu cầu hệ thống

| Thành phần | Yêu cầu |
|-----------|-------------|
| **OS** | Windows 10/11, Ubuntu 20.04+, hoặc macOS |
| **Python** | 3.11+ |
| **Node.js** | 20 LTS |
| **RAM** | 4GB minimum |
| **Đĩa** | 10GB (ứng dụng + exports) |

### 11.2 Cài đặt Backend

```bash
# 1. Sao chép repository
git clone https://github.com/your-org/network-sketcher-web.git
cd network-sketcher-web

# 2. Tạo môi trường ảo
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 3. Cài đặt phụ thuộc
pip install -r requirements.txt

# 4. Tạo file cấu hình
cp .env.example .env
# Chỉnh sửa .env nếu cần

# 5. Khởi tạo CSDL (SQLite tự tạo)
python -c "from app.database import init_db; init_db()"

# 6. Chạy server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Hoặc với reload cho phát triển
uvicorn app.main:app --reload --port 8000

# 7. Chạy worker xuất (terminal khác)
python -m app.workers.export_worker
```

### 11.3 Cài đặt Frontend

```bash
# 1. Di chuyển vào thư mục frontend
cd frontend

# 2. Cài đặt phụ thuộc
npm install

# 3. Build bản production
npm run build

# 4. Serve với preview server (tùy chọn)
npm run preview
```

### 11.4 File cấu hình (.env)

```bash
# backend/.env

# CSDL (SQLite - tự động tạo file)
DATABASE_URL=sqlite+aiosqlite:///./data/network_sketcher.db

# Bảo mật
SECRET_KEY=your-secret-key-here-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# Đường dẫn
EXPORTS_DIR=./exports
UPLOADS_DIR=./uploads
TEMPLATES_DIR=./templates

# Máy chủ
HOST=0.0.0.0
PORT=8000
DEBUG=false

# URL frontend (cho CORS)
FRONTEND_URL=http://localhost:3000
```

### 11.5 Chạy như Service (Production)

#### Windows - Task Scheduler hoặc NSSM

```powershell
# Tùy chọn 1: Dùng NSSM (Non-Sucking Service Manager)
# Tải về: https://nssm.cc/

nssm install NetworkSketcherBackend
# Đường dẫn: C:\path\to\venv\Scripts\uvicorn.exe
# Tham số: app.main:app --host 0.0.0.0 --port 8000
# Thư mục khởi động: C:\path\to\backend

nssm start NetworkSketcherBackend

# Dịch vụ worker xuất
nssm install NetworkSketcherWorker
# Đường dẫn: C:\path\to\venv\Scripts\python.exe
# Tham số: -m app.workers.export_worker
# Thư mục khởi động: C:\path\to\backend

nssm start NetworkSketcherWorker
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

```bash
# /etc/systemd/system/network-sketcher-worker.service

[Unit]
Description=Network Sketcher Export Worker
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/network-sketcher-web/backend
Environment="PATH=/opt/network-sketcher-web/backend/venv/bin"
ExecStart=/opt/network-sketcher-web/backend/venv/bin/python -m app.workers.export_worker
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Kích hoạt worker
sudo systemctl daemon-reload
sudo systemctl enable network-sketcher-worker
sudo systemctl start network-sketcher-worker
sudo systemctl status network-sketcher-worker
```

### 11.6 Nginx reverse proxy (tùy chọn)

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

    # Tải về exports
    location /exports/ {
        alias /opt/network-sketcher-web/backend/exports/;
    }
}
```

### 11.7 Script sao lưu

```bash
#!/bin/bash
# backup.sh - Chạy hàng ngày với cron

BACKUP_DIR="/backup/network-sketcher"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/opt/network-sketcher-web/backend"

# Tạo thư mục backup
mkdir -p $BACKUP_DIR

# Sao lưu SQLite (an toàn)
sqlite3 $APP_DIR/data/network_sketcher.db ".backup $BACKUP_DIR/db_$DATE.sqlite"

# Sao lưu thư mục exports
tar -czf $BACKUP_DIR/exports_$DATE.tar.gz $APP_DIR/exports/

# Giữ lại 7 ngày backup
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Sao lưu hoàn tất: $DATE"
```

```bash
# Thêm vào crontab (chạy 2 giờ sáng mỗi ngày)
0 2 * * * /opt/network-sketcher-web/backup.sh >> /var/log/ns-backup.log 2>&1
```

### 11.8 Kiểm tra sức khỏe

Backend có sẵn endpoint `/health`:

```bash
# Kiểm tra sức khỏe
curl http://localhost:8000/health

# Phản hồi
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0",
  "uptime_seconds": 3600
}
```

### 11.9 Khắc phục sự cố

| Vấn đề | Giải pháp |
|-------|----------|
| Port 8000 đã dùng | Đổi port trong .env hoặc dừng process khác |
| SQLite bị khóa | Chờ vài giây, hoặc khởi động lại dịch vụ |
| CORS error | Kiểm tra FRONTEND_URL trong .env |
| Import failed | Kiểm tra định dạng Excel, xem logs |
| Timeout xuất | Tăng timeout trong cấu hình uvicorn |
| Job xuất bị treo | Kiểm tra dịch vụ/logs của worker |

```bash
# Xem logs
tail -f /var/log/network-sketcher.log

# Khởi động lại dịch vụ
sudo systemctl restart network-sketcher
```

---

## 12. Đánh giá rủi ro

### 12.1 Rủi ro kỹ thuật

| Rủi ro | Tác động | Xác suất | Giảm thiểu |
|------|--------|-------------|------------|
| Khác biệt kết xuất PPTX | Cao | Trung bình | Kiểm thử thị giác kỹ, so sánh với đầu ra CLI |
| Hiệu năng sơ đồ lớn | Trung bình | Cao | Virtualization canvas, phân trang, lazy loading |
| Ghi đồng thời SQLite | Thấp | Thấp | WAL mode, ~5 người dùng không vấn đề |
| Quản lý lưu trữ tệp | Thấp | Trung bình | Job dọn dẹp hằng ngày, giám sát đĩa |

### 12.2 Rủi ro dự án

| Rủi ro | Tác động | Xác suất | Giảm thiểu |
|------|--------|-------------|------------|
| Trượt phạm vi | Cao | Cao | Định nghĩa MVP chặt chẽ, bàn giao theo giai đoạn |
| Thiếu kỹ năng | Trung bình | Trung bình | Đào tạo, pair programming, tài liệu |
| Trễ tiến độ | Trung bình | Trung bình | Dự phòng thời gian, ưu tiên theo mức độ |
| Vấn đề tích hợp | Trung bình | Trung bình | Kiểm thử tích hợp sớm, hợp đồng API |

### 12.3 Chiến lược giảm thiểu

**PPTX Rendering:**
- Create automated visual regression tests
- So sánh PPTX xuất với phiên bản CLI theo từng cặp
- Duy trì bộ PPTX tham chiếu để đối chiếu

**Performance:**
- Triển khai virtualization canvas (chỉ render phần nhìn thấy)
- Dùng WebWorkers cho tính toán nặng
- Triển khai debounce và cache cho request

**Scalability:**
- Thiết kế cho mở rộng ngang ngay từ đầu
- Giữ app stateless (JWT) + hàng đợi job dựa trên DB; cân nhắc Redis khi scale
- Triển khai health check và suy giảm có kiểm soát

### 12.4 Kế hoạch xử lý khác biệt & rủi ro (khuyến nghị)

- **Ma trận tương thích logic:** lập bảng “input → xử lý → output” đối chiếu từng chức năng với repo gốc; cập nhật khi có thay đổi.
- **Golden files cho xuất:** tạo bộ Excel/PPTX chuẩn, chạy so sánh tự động (snapshot/regression) sau mỗi thay đổi.
- **Job queue an toàn:** thêm cơ chế “claim job” (status + locked_at), retry có giới hạn, idempotency theo `job_id`, và quy tắc phát hiện job treo.
- **Theo dõi chất lượng:** đặt ngưỡng hiệu năng (thời gian render/xuất), benchmark định kỳ trên bộ dữ liệu lớn.
- **Khả năng phục hồi:** quy trình backup/restore thử nghiệm định kỳ, kiểm tra tính toàn vẹn file xuất.
- **Tài liệu hóa thay đổi:** mọi khác biệt so với repo gốc phải ghi rõ trong plan + changelog nội bộ.

---

## Phụ lục A: Cấu trúc thư mục

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
│   ├── exports/                 # Tệp PPTX/Excel đã sinh
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
│   ├── backup.sh                # Script sao lưu
│   └── start.sh                 # Khởi động tất cả dịch vụ
│
├── docs/
│   ├── INSTALL.md               # Installation guide
│   ├── USER_GUIDE.md            # User manual
│   └── API.md                   # API documentation
│
└── README.md
```

---

## Phụ lục B: Ví dụ phản hồi API

### Phản hồi tạo dự án

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

### Phản hồi dữ liệu sơ đồ

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

### Phản hồi job xuất

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

## Phụ lục C: Thuật ngữ

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
| **File thiết bị** | Excel xuất với các bảng L1/L2/L3 |

---

## 13. Tham chiếu logic NS gốc

Section này cung cấp mapping chi tiết giữa source code gốc của Network Sketcher và các component tương ứng trong Web App, giúp developers dễ dàng tham chiếu logic nghiệp vụ.

### 13.0 Kho mã nguồn tham chiếu

Dự án này dựa trên source gốc của Network Sketcher để tham chiếu tính năng/chức năng/logic.

```
https://github.com/cisco-open/network-sketcher
```

### 13.1 Tổng quan tệp nguồn

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

### 13.2 Định nghĩa cốt lõi (`ns_def.py`)

#### 13.2.1 Kiểm tra hợp lệ tên cổng

**Original Function:** `split_portname()` (line ~200-250)

```python
# ns_def.py - Phân tách tên cổng thành loại và số
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

#### 13.2.2 Định nghĩa màu theo ngành

**Original Location:** `ns_def.py` (line ~50-100) và CLI theme system

```python
# Ánh xạ INDUSTRY_COLORS - màu thiết bị theo tiền tố tên
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

    # Máy chủs
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

# Màu mục đích liên kết (theme tương phản CLI)
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

### 13.3 Lệnh CLI (`ns_cli.py`)

#### 13.3.1 Ánh xạ lệnh → API

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

#### 13.3.2 Logic kiểm tra hợp lệ

**Original:** `ns_cli.py` lines ~100-200

```python
# Quy tắc kiểm tra hợp lệ từ ns_cli.py

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

### 13.4 Sinh PPTX (`ns_ddx_figure.py`)

#### 13.4.1 Lớp và phương thức chính

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

#### 13.4.2 Tối ưu bộ nhớ đệm

**Original Issue:** `ns_ddx_figure.py` scans 50,000 rows repeatedly for each shape lookup.

```python
# Đoạn code gốc chưa tối ưu (dòng ~1080)
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

#### 13.4.3 Logic điểm kết nối

**Original:** `ns_ddx_figure.py` lines 687-714

```python
# Logic kết nối giản lược - chỉ xét vị trí theo chiều dọc
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

### 13.5 Tạo sơ đồ L2 (`ns_l2_diagram_create.py`)

**File:** `ns_l2_diagram_create.py` (~500 lines)

#### 13.5.1 Hàm chính

| Function | Purpose | Web App Mapping |
|----------|---------|-----------------|
| `create_l2_diagram_data()` | Generate L2 topology data | `L2DiagramService.generate()` |
| `get_l2_segments_for_device()` | Get VLANs for a device | `L2SegmentRepository.get_by_device()` |
| `calculate_l2_area_layout()` | Layout L2 groups | `LayoutService.calculate_l2_layout()` |

#### 13.5.2 Logic gom nhóm phân đoạn L2

```python
# Logic gốc từ ns_l2_diagram_create.py

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

### 13.6 Tạo sơ đồ L3 (`ns_l3_diagram_create.py`)

**File:** `ns_l3_diagram_create.py` (~600 lines)

#### 13.6.1 Bộ nhớ đệm kích thước chữ

**Original Optimization:** Lines 43-60

```python
# ns_l3_diagram_create.py - Đã có bộ nhớ đệm cho chữ
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

### 13.7 Đồng bộ lớp (`ns_sync_between_layers.py`)

**File:** `ns_sync_between_layers.py` (~400 lines)

#### 13.7.1 Quy tắc đồng bộ

```python
# Quy tắc đồng bộ lớp từ ns_sync_between_layers.py

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

### 13.8 Logic nhập Excel (`scripts/import_from_excel.py`)

#### 13.8.1 Thứ tự xử lý sheet

```python
# Thứ tự nhập rất quan trọng - cần thỏa các phụ thuộc

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

### 13.9 Hỗ trợ theme cho CLI wrapper (`scripts/ns_cli_wrapper.py`)

#### 13.9.1 Áp dụng theme

```python
# ns_cli_wrapper.py - Hỗ trợ tham số theme

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

### 13.10 Bảng tham chiếu nhanh

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
