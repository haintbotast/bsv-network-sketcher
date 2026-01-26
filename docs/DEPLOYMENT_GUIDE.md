# Hướng dẫn triển khai (tối giản)

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-26  
> **Mục tiêu:** Hướng dẫn triển khai tối giản cho môi trường nội bộ.

---

## 1. Yêu cầu hệ thống

- Python 3.11+
- Node.js 18+
- SQLite 3
- Hệ điều hành: Windows/Linux

---

## 2. Cài đặt backend (tóm tắt)

- Tạo venv, cài dependencies.
- Thiết lập `.env` (DB path, SECRET_KEY, FRONTEND_URLS).
- Chạy `uvicorn` hoặc service (systemd/NSSM).

---

## 3. Cài đặt frontend (tóm tắt)

- `npm install`
- `npm run build`
- Serve static qua backend hoặc nginx.

---

## 4. Chạy service (production tối giản)

- **Linux:** systemd
- **Windows:** NSSM
- **Worker export:** chạy `python -m app.workers.export_worker` như một service riêng.
- **WebSocket:** dùng chung service backend (port 8000).

---

## 5. Nginx reverse proxy (tùy chọn)

- Proxy `/api` và `/ws` tới backend.
- Serve `/dist` và `/exports` nếu cần.

---

## 6. Sao lưu & khôi phục

**Backup:**
- SQLite `.backup`
- Thư mục `exports/`

**Restore:**
- Dừng service
- Khôi phục DB + exports
- Khởi động lại service

---

## 7. Kiểm tra sức khỏe

- `GET /health` → `status: healthy`

---

## 8. Khắc phục sự cố

- DB bị khóa → chờ, kiểm tra WAL/worker.
- Import lỗi → xem logs + kiểm tra schema.
- Export timeout → tăng timeout hoặc kiểm tra ProcessPool.

---

## 9. Tài liệu liên quan

- `WEB_APP_DEVELOPMENT_PLAN.md`
- `docs/TEST_STRATEGY.md`
- `docs/API_SPEC.md`
