# API Spec (tối giản) - Web Network Sketcher

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-23  
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
```

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
/projects/{project_id}/l2/segments
/projects/{project_id}/l2/assignments
/projects/{project_id}/l3/addresses
```

**Bulk (grid nhập liệu):**
```
POST /projects/{project_id}/areas/bulk
POST /projects/{project_id}/devices/bulk
POST /projects/{project_id}/links/bulk
```

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

---

## 8. Format lỗi chuẩn

```json
{
  "errors": [
    {"entity": "device", "row": 3, "field": "name", "code": "DEVICE_NAME_DUP", "message": "Trùng tên thiết bị"}
  ]
}
```

---

## 9. WebSocket (tối giản)

```
WS /ws/projects/{project_id}
Events: diagram.updated, export.progress, export.completed, export.failed
```

---

## 10. Tài liệu liên quan

- `docs/SRS.md`
- `docs/TEMPLATE_SCHEMA.md`
- `docs/DIAGRAM_STYLE_SPEC.md`
