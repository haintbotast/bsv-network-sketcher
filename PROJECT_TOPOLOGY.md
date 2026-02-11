# Topology dự án Web Network Sketcher

> **Phiên bản:** 1.1  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-02-10  
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
- Auto-layout tự chạy khi mở project **nếu dữ liệu chưa ổn định tọa độ** (thiếu `grid_range` hoặc thiếu `position_x/position_y`) và sau CRUD topology (area/device/link/port-link/anchor override).
- Thao tác viewport (`pan/zoom/reset view`) chỉ đổi góc nhìn trên client, **không** trigger auto-layout.
- Auto-layout thủ công từ tab **Bố cục** có 2 chế độ:
  - `preserve_existing_positions=true` (mặc định, khuyến nghị): giữ tọa độ Area/Device đã có trong DB, chỉ điền vị trí còn thiếu.
  - `preserve_existing_positions=false`: ghi đè toàn bộ tọa độ theo kết quả auto-layout mới.
- Macro layout L1 khi có `grid_row/grid_col` dùng cơ chế **center-slot theo cột** (độ rộng cột đại diện theo trung vị) để giữ area bám bố cục chuẩn PDF và giảm lệch do area outlier quá rộng.
- Micro layout L1 căn giữa các hàng thiết bị trong cùng layer khi phải tách nhiều hàng, giúp vị trí object cân đối hơn theo mẫu kỹ thuật.
- Kéo‑thả thủ công `Area/Device` (khi bật chế độ sửa vị trí) lưu trực tiếp `position_x/position_y` về DB tại `drag-end` và không trigger auto-layout.
- Lưu thuộc tính `Area/Device` nếu chỉ thay đổi nhóm vị trí (`position_x/position_y/grid_range`) thì cập nhật trực tiếp DB, không tự chạy lại auto-layout.
- Thuộc tính màu/style lưu DB theo từng thực thể: `areas.style_json`, `devices.color_rgb_json`, `l1_links.color_rgb_json`; UI chỉ cho chọn trong palette preset, link không override màu sẽ tự map theo `purpose`.
- Control viewport/view mode (`zoom/reset/L1/L2/L3/Sửa vị trí`) tập trung ở main navigator panel và canh giữa theo panel; khi drag object có guide + snap alignment theo object liên quan để chỉnh tay nhanh.
- Tọa độ thủ công được chuẩn hóa theo mốc chuẩn X/Y (step 0.25 đv) trước khi lưu DB để đồng nhất dữ liệu.
- Tọa độ chuẩn bổ sung `grid_range` kiểu Excel (`A1:B2`) cho `Area`/`Device`; backend tự đồng bộ `grid_range` ↔ `position_x/position_y/width/height`.
- Khi startup backend, dữ liệu cũ thiếu `grid_range` sẽ được backfill tự động từ tọa độ/kích thước hiện có để chuẩn hóa về cấu trúc grid mới.
- Mọi luồng apply layout (L1/L2/L3 + waypoint) phải ghi đồng thời `position_*` và `grid_range` để tránh lệch dữ liệu render giữa frontend/backend.
- `grid_row/grid_col` của Area là placement map logic (phục vụ macro layout), không tự ghi đè theo tọa độ tuyệt đối sau mỗi lần auto-layout.
- Quy ước anchor L1: uplink đi ra từ **cạnh trên** object, non-uplink đi ra từ **cạnh dưới** object; override thủ công được ưu tiên.
- Routing liên‑area L1 dùng **hành lang orthogonal đơn giản theo cặp Area** với lane offset nhẹ theo bundle index để giảm chồng lấn.
- Routing L1 dùng pipeline **single-pass, không A\***; ưu tiên thuật toán tuyến tính/địa phương để giữ UI mượt và ổn định.
- Fallback liên‑area chỉ đi trong phạm vi đường bao sơ đồ, không dùng tuyến vòng ngoài canvas.
- Bổ sung thực thể `device_ports` (DB-driven) để khai báo port độc lập trước khi nối link; endpoint link phải tham chiếu port đã khai báo.
- Render L1 dùng **port band gắn trực tiếp vào object** (top/bottom); kích thước object được nới theo số lượng/độ dài port.
- Render routing L1 theo phong cách kỹ thuật (orthogonal/góc vuông rõ, ưu tiên màu trung tính cho link LAN/DEFAULT).
- UI L1 render khung Area theo dạng compact quanh cụm thiết bị để giảm khoảng trắng hiển thị (không đổi dữ liệu Area gốc).
- Link peer-control (`STACK/HA/HSRP`) dùng lane/style riêng để tách khỏi các luồng uplink/data trong cùng khu vực.
- Tab Bố cục cung cấp luồng khai báo nhanh peer-control (`STACK/HA/HSRP`) và legend màu/nét/chú giải để chuẩn hóa thao tác vận hành.

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
