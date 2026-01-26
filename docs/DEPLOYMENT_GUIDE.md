# Hướng dẫn triển khai (tối giản)

> **Phiên bản:** 1.1
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

## 1.1. Cấu trúc đường dẫn

| Mục đích | Đường dẫn |
|----------|-----------|
| Source code | `/home/<user>/Projects/bsv/bsv-network-sketcher/` |
| Deploy directory | `/opt/bsv-ns-deploy/` |
| Backend | `<deploy>/backend/` |
| Frontend source | `<deploy>/frontend/` |
| Frontend build | `<deploy>/frontend/dist/` |
| Database | `<deploy>/backend/data/app.db` |
| Backend logs | `<deploy>/backend/logs/` |
| Frontend logs | `<deploy>/frontend/logs/` |
| Export files | `<deploy>/backend/exports/` |

---

## 1.2. Cổng dịch vụ

| Dịch vụ | Cổng | Mô tả |
|---------|------|-------|
| Backend API | 8000 | FastAPI + Uvicorn |
| Frontend Dev | 5173 | Vite dev server (chỉ development) |
| WebSocket | 8000 | Dùng chung với backend |

**Lưu ý CORS:** Backend cấu hình `FRONTEND_URLS` để cho phép frontend gọi API. Mặc định: `http://localhost:5173`.

---

## 2. Cài đặt backend

### 2.1. Tạo virtual environment

```bash
cd /opt/bsv-ns-deploy/backend
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# hoặc: venv\Scripts\activate  # Windows
```

### 2.2. Cài dependencies

```bash
pip install -r requirements.txt
```

### 2.3. Thiết lập `.env`

```bash
cp .env.example .env
# Chỉnh sửa .env với các giá trị phù hợp
```

Các biến môi trường quan trọng:
- `DATABASE_URL`: Đường dẫn SQLite (mặc định: `sqlite+aiosqlite:///./data/app.db`)
- `SECRET_KEY`: Khóa bí mật cho JWT (bắt buộc thay đổi)
- `FRONTEND_URLS`: Danh sách URL frontend được phép (CORS)
- `ALLOW_SELF_REGISTER`: `true`/`false` cho phép đăng ký tự do

### 2.4. Chạy backend (development)

```bash
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Hoặc chạy nền:
```bash
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 &
```

---

## 3. Cài đặt frontend

### 3.1. Cài dependencies

```bash
cd /opt/bsv-ns-deploy/frontend
npm install
```

### 3.2. Build production

```bash
npm run build
# Output: dist/
```

### 3.3. Chạy dev server (development)

```bash
npm run dev -- --port 5173
# hoặc chạy nền:
npm run dev -- --port 5173 > logs/vite.log 2>&1 &
```

---

## 3.1. Sync code từ source sang deploy

```bash
rsync -av --exclude='node_modules' --exclude='.venv' --exclude='__pycache__' \
  --exclude='*.pyc' --exclude='.git' --exclude='*.db' \
  /home/<user>/Projects/bsv/bsv-network-sketcher/ /opt/bsv-ns-deploy/
```

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

## 8.1. Tạo admin ban đầu (bắt buộc khi tắt đăng ký)

- **Khuyến nghị:** tắt đăng ký tự do (`ALLOW_SELF_REGISTER=false`).
- Tạo admin trực tiếp trong DB bằng script nội bộ.
- Liên hệ người vận hành để lấy thông tin tài khoản admin.

---

## 9. Tài liệu liên quan

- `WEB_APP_DEVELOPMENT_PLAN.md`
- `docs/TEST_STRATEGY.md`
- `docs/API_SPEC.md`
