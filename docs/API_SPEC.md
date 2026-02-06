# API Spec (tối giản) - Web Network Sketcher

> **Phiên bản:** 1.1
> **Tạo:** 2026-01-23
> **Cập nhật:** 2026-02-03
> **Mục tiêu:** Đặc tả API phục vụ nhập liệu trực tiếp, quản lý dự án và xuất dữ liệu.

---

## 1. Nguyên tắc

- Base URL: `/api/v1`
- Auth: JWT (Bearer)
- Trả lỗi theo format chuẩn (xem mục 8).
- Ưu tiên API **tối giản nhưng ổn định**.

---

## 2. Auth

```
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
```

---

## 3. Projects

```
GET    /projects
POST   /projects
GET    /projects/{id}
PUT    /projects/{id}
DELETE /projects/{id}
POST   /projects/{id}/duplicate
POST   /projects/{id}/import   # import template/json/excel/csv
GET    /projects/{id}/versions
POST   /projects/{id}/versions
GET    /projects/{id}/versions/{version_id}
POST   /projects/{id}/versions/{version_id}/restore
```

**Trường cấu hình project (gợi ý):**
- `layout_mode`: `standard` (mặc định, cố định)

---

## 4. Template dữ liệu

```
GET    /templates
POST   /templates
GET    /templates/{id}
PUT    /templates/{id}
DELETE /templates/{id}
POST   /templates/{id}/apply
```

---

## 5. CRUD theo project

```
/projects/{project_id}/areas
/projects/{project_id}/devices
/projects/{project_id}/interfaces
/projects/{project_id}/links
/projects/{project_id}/port-channels
/projects/{project_id}/virtual-ports
/projects/{project_id}/l2/segments
/projects/{project_id}/l2/assignments
/projects/{project_id}/l3/addresses
/projects/{project_id}/port-anchors
```

**Bulk (grid nhập liệu):**
```
POST /projects/{project_id}/areas/bulk
POST /projects/{project_id}/devices/bulk
POST /projects/{project_id}/links/bulk
POST /projects/{project_id}/port-channels/bulk
POST /projects/{project_id}/virtual-ports/bulk
```

**Port Anchor Overrides:**
```
GET    /projects/{project_id}/port-anchors
PUT    /projects/{project_id}/port-anchors   # bulk upsert
DELETE /projects/{project_id}/port-anchors?device_id=...&port_name=...
```

**Request (bulk upsert):**
```json
{
  "overrides": [
    {
      "device_id": "dev-uuid",
      "port_name": "Gi 0/1",
      "side": "left",
      "offset_ratio": null
    }
  ]
}
```

**Ghi chú:**
- `side` ∈ `left|right|top|bottom`
- `offset_ratio` ∈ `[0..1]` (hoặc `null`), tính theo chiều cạnh thiết bị.  
  Nếu `null` thì **giữ auto offset** theo side đã chọn.

---

## 5.1 Auto-layout (bố cục tự động)

```
POST /projects/{project_id}/auto-layout
POST /projects/{project_id}/invalidate-layout-cache
```

**Request (gợi ý):**
```json
{
  "algorithm": "simple_layer_topology_aware",
  "direction": "horizontal|vertical",
  "layer_gap": 2.0,
  "node_spacing": 0.5,
  "crossing_iterations": 24,
  "apply_to_db": false,
  "group_by_area": true,
  "layout_scope": "project|area",
  "anchor_routing": true,
  "overview_mode": "l1-only",
  "normalize_topology": false
}
```

**Response (gợi ý):**
```json
{
  "devices": [{ "id": "...", "x": 1.2, "y": 0.5, "layer": 2, "area_id": "..." }],
  "areas": [{ "id": "...", "x": 0.0, "y": 0.0, "width": 3.0, "height": 1.5 }],
  "stats": { "total_layers": 5, "total_crossings": 8, "execution_time_ms": 120, "algorithm": "simple_layer_grouped" }
}
```

**Ghi chú:**
- `group_by_area=true` là mặc định theo AI Context: layout 2 tầng (macro Area + micro Device).
- `overview_mode="l1-only"` để tránh đè nhãn L2/L3 trong overview.
- `normalize_topology=true` sẽ tự tạo Area Data Center/Server (nếu thiếu) và chuyển device theo quy ước (Access vào area nghiệp vụ, Server về Server, Edge/Security/DMZ/Core/Dist vào Data Center; Monitor/NOC/NMS gộp vào IT).

---

## 6. Xuất dữ liệu

```
POST /projects/{project_id}/export/l1-diagram
POST /projects/{project_id}/export/l2-diagram
POST /projects/{project_id}/export/l3-diagram
POST /projects/{project_id}/export/device-file
POST /projects/{project_id}/export/master-file
GET  /projects/{project_id}/export/jobs
GET  /projects/{project_id}/export/jobs/{id}
```

**Ghi chú:** export job lưu `version_id` để truy vết.
**Tùy chọn:** request export có thể nhận `version_id` để xuất theo snapshot.

---

## 7. Import dữ liệu (tổng hợp)

```
POST /projects/{id}/import
{
  "mode": "template" | "json" | "excel" | "csv",
  "template_id": "tpl-uuid",
  "payload": { ... },
  "options": {
    "validate_only": true,
    "merge_strategy": "replace" | "merge"
  }
}
```

**Merge strategy (tối giản):**
- `replace`: xóa dữ liệu hiện có của project rồi nhập mới.
- `merge`: chỉ thêm mới, không ghi đè bản ghi trùng khóa tự nhiên.

---

## 8. Format lỗi chuẩn

```json
{
  "errors": [
    {"entity": "device", "row": 3, "field": "name", "code": "DEVICE_NAME_DUP", "message": "Trùng tên thiết bị"}
  ]
}
```

### 8.1 Danh sách mã lỗi (tối thiểu)

- `AREA_NAME_DUP`, `AREA_GRID_INVALID`, `AREA_SIZE_INVALID`
- `DEVICE_NAME_DUP`, `DEVICE_TYPE_INVALID`, `DEVICE_SIZE_INVALID`, `AREA_NOT_FOUND`
- `DEVICE_NOT_FOUND`, `PORT_FORMAT_INVALID`, `L1_LINK_DUP`, `ENDPOINT_UPLINK_INVALID`, `SERVER_UPLINK_INVALID`
- `PORT_CHANNEL_MEMBERS_INVALID`
- `PORT_CHANNEL_MEMBER_DUP`
- `VIRTUAL_PORT_TYPE_INVALID`
- `VIRTUAL_PORT_L1_FORBIDDEN`
- `VLAN_INVALID`, `PORT_MODE_INVALID`
- `INTERFACE_NOT_FOUND`, `IP_INVALID`
- `L2_ASSIGNMENT_INVALID`, `L3_ASSIGNMENT_INVALID`

---

## 9. WebSocket (tối giản)

```
WS /ws/projects/{project_id}
Events: diagram.updated, export.progress, export.completed, export.failed
```

---

## 10. Cấu hình hệ thống (admin)

```
GET  /admin/config
PUT  /admin/config
GET  /admin/config/versions
POST /admin/config/versions/{version_id}/restore
```

**Phạm vi cấu hình:** preset layout/style, validation rules + layout checks, export defaults.
**Schema:** xem `docs/ADMIN_CONFIG_SCHEMA.md`.
**Bổ sung:** `layout_tuning` và `render_tuning` dùng để điều chỉnh auto-layout & routing/label trên UI.

---

---

## 11. Ví dụ Request/Response chi tiết

### 10.1 Authentication

**POST /api/v1/auth/register**

Request:
```json
{
  "email": "user@example.com",
  "password": "SecureP@ss123",
  "display_name": "Nguyễn Văn A"
}
```

Response (201 Created):
```json
{
  "id": "usr_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "user@example.com",
  "display_name": "Nguyễn Văn A",
  "created_at": "2026-01-23T10:00:00Z"
}
```

**POST /api/v1/auth/login**

Request:
```json
{
  "email": "user@example.com",
  "password": "SecureP@ss123"
}
```

Response (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

Response (401 Unauthorized):
```json
{
  "errors": [
    {
      "code": "AUTH_INVALID_CREDENTIALS",
      "message": "Email hoặc mật khẩu không đúng"
    }
  ]
}
```

---

### 10.2 Projects

**POST /api/v1/projects**

Request:
```json
{
  "name": "DC Network 2026",
  "description": "Sơ đồ mạng Data Center Q1 2026"
}
```

Response (201 Created):
```json
{
  "id": "prj_f1e2d3c4-b5a6-7890-1234-567890abcdef",
  "name": "DC Network 2026",
  "description": "Sơ đồ mạng Data Center Q1 2026",
  "owner_id": "usr_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "created_at": "2026-01-23T10:15:00Z",
  "updated_at": "2026-01-23T10:15:00Z",
  "stats": {
    "area_count": 0,
    "device_count": 0,
    "link_count": 0
  }
}
```

**GET /api/v1/projects/{id}**

Response (200 OK):
```json
{
  "id": "prj_f1e2d3c4-b5a6-7890-1234-567890abcdef",
  "name": "DC Network 2026",
  "description": "Sơ đồ mạng Data Center Q1 2026",
  "owner_id": "usr_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "created_at": "2026-01-23T10:15:00Z",
  "updated_at": "2026-01-23T11:30:00Z",
  "stats": {
    "area_count": 3,
    "device_count": 15,
    "link_count": 22
  }
}
```

---

### 10.3 Areas

**POST /api/v1/projects/{project_id}/areas**

Request:
```json
{
  "name": "Core",
  "grid_row": 1,
  "grid_col": 1,
  "width": 4.0,
  "height": 2.5
}
```

Response (201 Created):
```json
{
  "id": "area_1a2b3c4d-5e6f-7890-abcd-ef1234567890",
  "project_id": "prj_f1e2d3c4-b5a6-7890-1234-567890abcdef",
  "name": "Core",
  "grid_row": 1,
  "grid_col": 1,
  "position_x": 0.5,
  "position_y": 0.5,
  "width": 4.0,
  "height": 2.5,
  "style": {
    "fill_color_rgb": [240, 240, 240],
    "stroke_color_rgb": [51, 51, 51],
    "stroke_width": 1
  },
  "created_at": "2026-01-23T10:20:00Z"
}
```

Response (400 Bad Request - trùng tên):
```json
{
  "errors": [
    {
      "entity": "area",
      "field": "name",
      "code": "AREA_NAME_DUP",
      "message": "Tên area 'Core' đã tồn tại trong project"
    }
  ]
}
```

---

### 10.4 Devices

**POST /api/v1/projects/{project_id}/devices**

Request:
```json
{
  "name": "Core-SW-1",
  "area_name": "Core",
  "device_type": "Switch",
  "position_x": 1.5,
  "position_y": 1.0
}
```

Response (201 Created):
```json
{
  "id": "dev_2b3c4d5e-6f78-9012-3456-7890abcdef12",
  "project_id": "prj_f1e2d3c4-b5a6-7890-1234-567890abcdef",
  "name": "Core-SW-1",
  "area_id": "area_1a2b3c4d-5e6f-7890-abcd-ef1234567890",
  "area_name": "Core",
  "device_type": "Switch",
  "position_x": 1.5,
  "position_y": 1.0,
  "width": 1.2,
  "height": 0.5,
  "color_rgb": [34, 139, 34],
  "created_at": "2026-01-23T10:25:00Z"
}
```

**POST /api/v1/projects/{project_id}/devices/bulk**

Request:
```json
{
  "devices": [
    {
      "name": "Access-SW-1",
      "area_name": "Access",
      "device_type": "Switch"
    },
    {
      "name": "Access-SW-2",
      "area_name": "Access",
      "device_type": "Switch"
    },
    {
      "name": "Server-1",
      "area_name": "Server Room",
      "device_type": "Server"
    }
  ]
}
```

Response (200 OK - partial success):
```json
{
  "success_count": 2,
  "error_count": 1,
  "created": [
    {
      "id": "dev_3c4d5e6f-7890-1234-5678-90abcdef1234",
      "name": "Access-SW-1",
      "row": 0
    },
    {
      "id": "dev_4d5e6f78-9012-3456-7890-abcdef123456",
      "name": "Access-SW-2",
      "row": 1
    }
  ],
  "errors": [
    {
      "entity": "device",
      "row": 2,
      "field": "area_name",
      "code": "AREA_NOT_FOUND",
      "message": "Area 'Server Room' không tồn tại"
    }
  ]
}
```

---

### 10.5 Links

**POST /api/v1/projects/{project_id}/links**

Request:
```json
{
  "from_device": "Core-SW-1",
  "from_port": "Gi 0/1",
  "to_device": "Access-SW-1",
  "to_port": "Gi 0/24",
  "purpose": "LAN"
}
```

Response (201 Created):
```json
{
  "id": "link_5e6f7890-1234-5678-90ab-cdef12345678",
  "project_id": "prj_f1e2d3c4-b5a6-7890-1234-567890abcdef",
  "from_device_id": "dev_2b3c4d5e-6f78-9012-3456-7890abcdef12",
  "from_device_name": "Core-SW-1",
  "from_port": "Gi 0/1",
  "to_device_id": "dev_3c4d5e6f-7890-1234-5678-90abcdef1234",
  "to_device_name": "Access-SW-1",
  "to_port": "Gi 0/24",
  "purpose": "LAN",
  "line_style": "solid",
  "color_rgb": [112, 173, 71],
  "created_at": "2026-01-23T10:30:00Z"
}
```

Response (400 Bad Request - port format sai):
```json
{
  "errors": [
    {
      "entity": "link",
      "field": "from_port",
      "code": "PORT_FORMAT_INVALID",
      "message": "Port 'Gi0/1' không hợp lệ. Phải có khoảng trắng giữa loại và số (vd: 'Gi 0/1')"
    }
  ]
}
```

Response (400 Bad Request - endpoint uplink sai tầng):
```json
{
  "errors": [
    {
      "entity": "link",
      "code": "ENDPOINT_UPLINK_INVALID",
      "message": "Endpoint không được kết nối trực tiếp lên Distribution/Core (phải qua Access)."
    }
  ]
}
```

Response (400 Bad Request - server uplink sai tầng):
```json
{
  "errors": [
    {
      "entity": "link",
      "code": "SERVER_UPLINK_INVALID",
      "message": "Server chỉ được kết nối lên Server Distribution Switch."
    }
  ]
}
```

**Ghi chú:** `PUT /api/v1/projects/{project_id}/links/{link_id}` áp dụng cùng validation như tạo mới (trùng link, port đã dùng, ràng buộc tầng).

Response (400 Bad Request - vi phạm quy tắc Access/Area/Server Switch):
```json
{
  "errors": [
    {
      "entity": "link",
      "code": "BUSINESS_AREA_UPLINK_INVALID",
      "message": "Thiết bị trong Area HO/IT/Department/Project chỉ được kết nối đến Access Switch cùng Area."
    }
  ]
}
```

Các mã lỗi liên quan khác có thể gặp:
- `BUSINESS_AREA_SINGLE_UPLINK`
- `ACCESS_UPLINK_INVALID`
- `ACCESS_DOWNLINK_INVALID`
- `SERVER_SWITCH_UPLINK_INVALID`
- `SERVER_SWITCH_DOWNLINK_INVALID`

---

### 10.6 Export

**POST /api/v1/projects/{project_id}/export/l1-diagram**

Request:
```json
{
  "mode": "all_areas",
  "theme": "default",
  "format": "pptx"
}
```

Response (202 Accepted):
```json
{
  "job_id": "job_6f789012-3456-7890-abcd-ef1234567890",
  "project_id": "prj_f1e2d3c4-b5a6-7890-1234-567890abcdef",
  "type": "l1_diagram",
  "status": "pending",
  "created_at": "2026-01-23T10:35:00Z",
  "progress": 0
}
```

**GET /api/v1/projects/{project_id}/export/jobs/{job_id}**

Response (200 OK - in progress):
```json
{
  "job_id": "job_6f789012-3456-7890-abcd-ef1234567890",
  "type": "l1_diagram",
  "status": "processing",
  "progress": 65,
  "message": "Đang tạo slide 3/5...",
  "created_at": "2026-01-23T10:35:00Z",
  "started_at": "2026-01-23T10:35:02Z"
}
```

Response (200 OK - completed):
```json
{
  "job_id": "job_6f789012-3456-7890-abcd-ef1234567890",
  "type": "l1_diagram",
  "status": "completed",
  "progress": 100,
  "created_at": "2026-01-23T10:35:00Z",
  "started_at": "2026-01-23T10:35:02Z",
  "completed_at": "2026-01-23T10:35:15Z",
  "download_url": "/api/v1/exports/job_6f789012-3456-7890-abcd-ef1234567890/download",
  "file_name": "DC_Network_2026_L1_Diagram.pptx",
  "file_size": 245760
}
```

Response (200 OK - failed):
```json
{
  "job_id": "job_6f789012-3456-7890-abcd-ef1234567890",
  "type": "l1_diagram",
  "status": "failed",
  "progress": 0,
  "created_at": "2026-01-23T10:35:00Z",
  "started_at": "2026-01-23T10:35:02Z",
  "failed_at": "2026-01-23T10:35:05Z",
  "error": {
    "code": "EXPORT_FAILED",
    "message": "Không thể tạo PPTX: Project không có devices"
  }
}
```

---

### 10.7 WebSocket Events

**Kết nối:** `WS /ws/projects/{project_id}`

**Event: diagram.updated**
```json
{
  "event": "diagram.updated",
  "data": {
    "entity_type": "device",
    "entity_id": "dev_2b3c4d5e-6f78-9012-3456-7890abcdef12",
    "action": "updated",
    "changes": {
      "position_x": 2.0,
      "position_y": 1.5
    },
    "timestamp": "2026-01-23T10:40:00Z",
    "user_id": "usr_a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

**Event: export.progress**
```json
{
  "event": "export.progress",
  "data": {
    "job_id": "job_6f789012-3456-7890-abcd-ef1234567890",
    "progress": 65,
    "message": "Đang tạo slide 3/5..."
  }
}
```

**Event: export.completed**
```json
{
  "event": "export.completed",
  "data": {
    "job_id": "job_6f789012-3456-7890-abcd-ef1234567890",
    "download_url": "/api/v1/exports/job_6f789012-3456-7890-abcd-ef1234567890/download",
    "file_name": "DC_Network_2026_L1_Diagram.pptx"
  }
}
```

---

## 12. Tài liệu liên quan

- `docs/SRS.md`
- `docs/TEMPLATE_SCHEMA.md`
- `docs/DIAGRAM_STYLE_SPEC.md`
- `docs/SECURITY_SPEC.md`
