# Kế hoạch phát triển Ứng dụng Web Network Sketcher (rút gọn)

> **Phiên bản:** 1.4  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-23  
> **Trạng thái:** Lập kế hoạch  
> **Mục tiêu:** Tối giản tài liệu kế hoạch, giữ nội dung cốt lõi và dẫn chiếu chi tiết sang các tài liệu chuyên biệt.

---

## 1. Mục tiêu & tiêu chí thành công

- Xây dựng web app vẽ sơ đồ mạng (lấy cảm hứng từ Network Sketcher).
- Tự định nghĩa output spec riêng, không yêu cầu tương thích 1:1 với NS gốc.
- UX tối giản, thao tác nhanh, lỗi hiển thị rõ.

**Tiêu chí thành công:**
- Tạo L1/L2/L3 từ dữ liệu nhập trực tiếp hoặc template chuẩn (Excel/CSV tùy chọn).
- Xuất PPTX/Excel theo spec riêng của dự án.
- Hỗ trợ 1000+ thiết bị/project (ưu tiên đúng logic, hiệu năng chấp nhận thấp hơn).

---

## 2. Phạm vi & nguyên tắc

**Phạm vi:**
- Quản lý project, nhập liệu, chỉnh sửa sơ đồ, xuất PPTX/Excel.
- Multi-user nội bộ (~5 đồng thời), hạ tầng single host.

**Nguyên tắc cốt lõi:**
- Tự định nghĩa style/layout spec (xem `docs/DIAGRAM_STYLE_SPEC.md`).
- Nhập liệu **template-first** (Excel/CSV tùy chọn cho dữ liệu cũ).
- **Không CLI**, không Docker/Redis/Celery.

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
- **GĐ5:** Render sơ đồ + style strict.
- **GĐ6:** Nhập liệu + template + (tùy chọn) Excel/CSV.
- **GĐ7:** Kiểm thử + triển khai tối giản.

---

## 6. Rủi ro chính & giảm thiểu (tóm tắt)

| Rủi ro | Giảm thiểu |
|---|---|
| Sai khác xuất PPTX/Excel | Golden files + regression test |
| Toàn vẹn dữ liệu | FK + validation matrix + transaction ngắn |
| Job queue treo/trùng | Claim job + heartbeat + retry giới hạn |
| UX rối | Strict NS + UI tối giản |

---

## 7. Tài liệu liên quan (nguồn chuẩn)

- `PROJECT_TOPOLOGY.md`
- `docs/BRD.md`
- `docs/PRD.md`
- `docs/SRS.md`
- `docs/DIAGRAM_STYLE_SPEC.md`
- `docs/API_SPEC.md`
- `docs/TEMPLATE_SCHEMA.md`
- `docs/TEST_STRATEGY.md`
- `docs/NS_REFERENCE.md`
- `docs/SECURITY_SPEC.md`
- `docs/TRACEABILITY_MATRIX.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `docs/APPENDIX.md`

---

*Document Version: 1.4 | Last Updated: 2026-01-23*
