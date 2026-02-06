# Topology dự án Web Network Sketcher

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-02-06  
> **Trạng thái:** Tài liệu kiến trúc vận hành  
> **Nguyên tắc:** Dự án web tham chiếu Network Sketcher gốc (logic), **không triển khai CLI**; ưu tiên đúng logic và UX tối giản nhưng dùng được ngay.

---

## 1. Mục tiêu tài liệu

Tài liệu này mô tả **topology tổng thể** của hệ thống (thành phần, luồng dữ liệu, triển khai tối giản) để:
- Làm nguồn chuẩn khi thiết kế/triển khai.
- Dễ kiểm tra tính đúng logic và layout theo chuẩn đã chọn.
- Giữ hệ thống gọn nhẹ nhưng **đúng logic** và **UX tiện dụng**.

---

## 2. Phạm vi & giả định

- Ứng dụng web nội bộ, ~5 người dùng đồng thời.
- Không Docker, không Redis/Celery.
- Backend FastAPI async + SQLAlchemy async.
- CSDL SQLite + aiosqlite (UUID dạng TEXT).
- Xuất PPTX/Excel qua worker nền + ProcessPool.
- WebSocket gốc cho cập nhật thời gian thực.

---

## 3. Topology chức năng (logical)

```
Người dùng
   │
   ▼
Frontend SPA (Vue 3 + Konva)
   │  REST/WS
   ▼
API Gateway (FastAPI)
   │
   ▼
Service Layer (Project/Diagram/Export/Import/Auth)
   │
   ├── SQLite (data)
   ├── File Storage (uploads/exports/templates)
   └── Job Queue (DB table) ──▶ Worker Poller ──▶ ProcessPool
```

### 3.1 Thành phần chính

| Thành phần | Vai trò | Ghi chú |
|-----------|---------|---------|
| Frontend SPA | UI/UX, canvas sơ đồ, nhập/xuất | Vue 3 + Konva |
| API Gateway | REST + WebSocket | FastAPI |
| Service Layer | Logic nghiệp vụ | Giữ logic L1→L2→L3 |
| SQLite | Lưu trữ bền vững | WAL + FK bắt buộc |
| File Storage | Tệp upload/xuất | Local FS |
| Job Worker | Sinh PPTX/Excel | Poller + ProcessPool |
| Versioning | Snapshot topology | Lưu JSON theo project |
| Config Versioning | Snapshot cấu hình | Lưu JSON cấu hình admin |

---

## 4. Luồng dữ liệu chính

### 4.1 Luồng chỉnh sửa sơ đồ
```
UI thao tác → REST API → Service → DB → phản hồi → UI render
```
- Auto-layout tự chạy khi mở project và sau CRUD topology (area/device/link/port-link/anchor override).
- Thao tác viewport (`pan/zoom/reset view`) chỉ đổi góc nhìn trên client, **không** trigger auto-layout.

### 4.2 Luồng xem trước thời gian thực
```
UI thao tác → REST API → Service → DB
                          └─> WebSocket push → UI cập nhật
```

### 4.3 Luồng xuất PPTX/Excel
```
UI yêu cầu xuất → REST API → tạo job (DB)
Worker poller → claim job → ProcessPool → sinh file → lưu storage → cập nhật trạng thái job
UI đọc trạng thái → tải file
```

---

## 5. Topology triển khai tối giản (single host)

```
[Client] ──HTTPS──> [Nginx (tùy chọn)] ──HTTP/WS──> [FastAPI + Worker]
                                           │
                                           ├── SQLite (file)
                                           └── Local Storage (uploads/exports)
```

### 5.1 Dịch vụ tối thiểu
- `backend`: FastAPI chạy app + WebSocket.
- `worker`: poller đọc job từ DB.
- `storage`: thư mục local cho uploads/exports.
- `sqlite`: file DB (WAL).

---

## 6. Topology dữ liệu & lưu trữ

| Kho | Mục đích | Ví dụ |
|-----|---------|------|
| DB SQLite | Metadata dự án/topology | `data/network_sketcher.db` |
| Uploads | Excel/template upload | `uploads/` |
| Exports | PPTX/Excel đã sinh | `exports/` |
| Templates | Mẫu đầu vào chuẩn | `templates/` |
| Logs | Nhật ký vận hành | `logs/` (tùy chọn) |
| Versions | Snapshot topology | `data/project_versions` |
| Config Versions | Snapshot cấu hình | `data/config_versions` |

---

## 7. Topology an toàn & toàn vẹn (tối giản nhưng bắt buộc)

- **FK bật** cho mọi kết nối SQLite.
- **Transaction ngắn** theo lô thao tác.
- **Idempotency** cho job (không chạy trùng).
- **Claim job nguyên tử** (status + locked_at + worker_id).
- **Kiểm soát upload/download** (kích thước/đuôi file/đường dẫn).
- **Anchor override:** lưu `port_anchor_overrides` để cố định vị trí anchor per-port (không bị auto-layout ghi đè).

---

## 8. Chuẩn layout & logic (tham chiếu NS)

- Không dùng CLI trong dự án web.
- Logic L1→L2→L3 giữ nguyên; validation chặt chẽ hơn.
- Output theo **style chung** (chuẩn nội bộ); NS chỉ tham chiếu.
- Bắt buộc có bộ “golden files” theo style chung để đối chiếu PPTX/Excel.
- Style sơ đồ phải tuân theo `docs/DIAGRAM_STYLE_SPEC.md`.

---

## 9. Quy tắc cập nhật tài liệu

- Mỗi thay đổi kiến trúc/topology/triển khai **phải cập nhật** file này.
- Mọi tác vụ liên quan luồng dữ liệu, worker, storage, export/import **phải đối chiếu** với file này.
