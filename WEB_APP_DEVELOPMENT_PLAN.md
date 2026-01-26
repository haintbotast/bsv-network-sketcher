# Kế hoạch phát triển Ứng dụng Web Network Sketcher (rút gọn)

> **Phiên bản:** 1.4  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-26  
> **Trạng thái:** Đang triển khai  
> **Mục tiêu:** Tối giản tài liệu kế hoạch, giữ nội dung cốt lõi và dẫn chiếu chi tiết sang các tài liệu chuyên biệt.

---

## 1. Mục tiêu & tiêu chí thành công

- Xây dựng web app vẽ sơ đồ mạng (tham chiếu Network Sketcher về logic).
- Layout/output **theo chuẩn layout network phổ biến** với chế độ lựa chọn (Cisco-style / ISO/IEC generic / custom).
- UX tối giản, thao tác nhanh, lỗi hiển thị rõ.
- Cho phép lưu vết phiên bản topology và cấu hình preset qua trang quản trị.

**Tiêu chí thành công:**
- Tạo L1/L2/L3 từ dữ liệu nhập trực tiếp hoặc template chuẩn (Excel/CSV tùy chọn).
- Xuất PPTX/Excel theo **layout mode đã chọn** và quy chuẩn style.
- Hỗ trợ 1000+ thiết bị/project (ưu tiên đúng logic, hiệu năng chấp nhận thấp hơn).

---

## 2. Phạm vi & nguyên tắc

**Phạm vi:**
- Quản lý project, nhập liệu, chỉnh sửa sơ đồ, xuất PPTX/Excel.
- Multi-user nội bộ (~5 đồng thời), hạ tầng single host.

**Nguyên tắc cốt lõi:**
- **Layout mode có thể chọn** (Cisco-style / ISO/IEC generic / custom) và tuân theo `docs/DIAGRAM_STYLE_SPEC.md`.
- Nhập liệu **template-first** (Excel/CSV tùy chọn cho dữ liệu cũ).
- **Không CLI**, không Docker/Redis/Celery.
- Logic L1→L2→L3 giữ nguyên, **validation chặt chẽ hơn**.
 - Cấu hình preset/layout/validation không hardcode.

---

## 3. Kiến trúc tổng quan (tóm tắt)

```
Frontend (Vue 3 + Konva)
   | REST/WS
Backend (FastAPI)
   |
Service Layer
   |-- SQLite (WAL, FK ON)
   |-- Storage (uploads/exports/templates)
   `-- Job Queue (DB) -> Worker -> ProcessPool
```

Chi tiết topology xem `PROJECT_TOPOLOGY.md`.

---

## 4. Ngăn xếp công nghệ (Option A)

- Backend: FastAPI async + SQLAlchemy 2.0 async
- CSDL: SQLite + aiosqlite (UUID TEXT, JSON TEXT)
- Frontend: Vue 3 + Vite + Konva
- Job: DB poller + ProcessPool
- WebSocket: native

---

## 5. Lộ trình phát triển (tóm tắt)

- **GĐ1-2:** Nền tảng + CRUD + nhập liệu trực tiếp + validation.
- **GĐ3-4:** Frontend core + editor + data grid.
- **GĐ5:** Render sơ đồ + layout mode + style preset.
- **GĐ6:** Nhập liệu + template + versioning + (tùy chọn) Excel/CSV.
- **GĐ7:** Kiểm thử + triển khai tối giản.

## 5.1. Tiến độ hiện tại (tóm tắt)

- **Hoàn thành:** Phase 1, 2A, 2B, 2C, 3, 4, 5, 6, 7 (backend đầy đủ, frontend khung + data grid đã nối API cơ bản).
- **Đang thiếu:** Hoàn thiện chỉnh sửa/sync dữ liệu canvas theo nghiệp vụ, layout mode + style preset, UI import/export, kiểm thử.

## 5.2. TODO tiếp theo (ưu tiên)

1) **Frontend ↔ Backend**
   - Tích hợp auth/login và lưu token.
   - Kết nối CRUD thật cho projects/areas/devices/links.
   - Đồng bộ realtime qua WebSocket (export events, cập nhật dữ liệu).
2) **Canvas editor**
   - Tạo/sửa/xóa area, device, link trên canvas.
   - Kéo‑thả, resize, snap/grid theo dữ liệu thật.
3) **Layout mode + style**
   - Áp dụng `docs/DIAGRAM_STYLE_SPEC.md`.
   - Bổ sung lựa chọn Cisco/ISO/Custom.
4) **Import/Export UI**
   - UI import template/JSON + validate.
   - UI export PPTX/Excel và theo dõi trạng thái job.
5) **Kiểm thử**
   - Unit tests (pytest) theo `docs/TEST_STRATEGY.md`.
   - Integration tests + `docs/RELEASE_CHECKLIST.md`.

---

## 6. Rủi ro chính & giảm thiểu (tóm tắt)

| Rủi ro | Giảm thiểu |
|---|---|
| Sai khác xuất PPTX/Excel | Golden files hoặc rule-based checks |
| Toàn vẹn dữ liệu | FK + validation matrix + transaction ngắn |
| Job queue treo/trùng | Claim job + heartbeat + retry giới hạn |
| UX rối | Layout mode chuẩn + UI tối giản |
| Cấu hình sai | Audit log + restore version |

---

## 7. Tài liệu liên quan (nguồn chuẩn)

- Xem danh mục: `docs/DOCS_INDEX.md`
- `docs/ADMIN_CONFIG_SCHEMA.md`
- `docs/ADMIN_UI_FLOW.md`

---

*Document Version: 1.4 | Last Updated: 2026-01-23*
