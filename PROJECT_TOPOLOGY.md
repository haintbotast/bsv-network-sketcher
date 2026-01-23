# Topology dự án Web Network Sketcher

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-23  
> **Trạng thái:** Tài liệu kiến trúc vận hành  
> **Nguyên tắc:** Dự án web port từ Network Sketcher gốc, **không triển khai CLI**; ưu tiên chính xác logic và UX tối giản nhưng dùng được ngay.

---

## 1. Mục tiêu tài liệu

Tài liệu này mô tả **topology tổng thể** của hệ thống (thành phần, luồng dữ liệu, triển khai tối giản) để:
- Làm nguồn chuẩn khi thiết kế/triển khai.
- Dễ kiểm tra tính tương thích với Network Sketcher gốc.
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
| Service Layer | Logic nghiệp vụ | Tương thích NS gốc |
| SQLite | Lưu trữ bền vững | WAL + FK bắt buộc |
| File Storage | Tệp upload/xuất | Local FS |
| Job Worker | Sinh PPTX/Excel | Poller + ProcessPool |

---

## 4. Luồng dữ liệu chính

### 4.1 Luồng chỉnh sửa sơ đồ
```
UI thao tác → REST API → Service → DB → phản hồi → UI render
```

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

---

## 7. Topology an toàn & toàn vẹn (tối giản nhưng bắt buộc)

- **FK bật** cho mọi kết nối SQLite.
- **Transaction ngắn** theo lô thao tác.
- **Idempotency** cho job (không chạy trùng).
- **Claim job nguyên tử** (status + locked_at + worker_id).
- **Kiểm soát upload/download** (kích thước/đuôi file/đường dẫn).

---

## 8. Chuẩn tương thích Network Sketcher gốc

- Không dùng CLI trong dự án web.
- Dữ liệu/logic/đầu ra phải tương đương NS gốc.
- Bắt buộc có bộ “golden files” để đối chiếu PPTX/Excel.
- Style sơ đồ phải tuân theo `docs/DIAGRAM_STYLE_SPEC.md`.

---

## 9. Quy tắc cập nhật tài liệu

- Mỗi thay đổi kiến trúc/topology/triển khai **phải cập nhật** file này.
- Mọi tác vụ liên quan luồng dữ liệu, worker, storage, export/import **phải đối chiếu** với file này.
