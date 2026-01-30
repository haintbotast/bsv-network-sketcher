# Hướng dẫn triển khai (tối giản)

> **Phiên bản:** 1.1
> **Tạo:** 2026-01-23
> **Cập nhật:** 2026-01-30
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

## 3.4. Hot deploy khi đang phát triển

Khi backend và frontend dev server đang chạy, bạn có thể cập nhật code mà không cần restart:

### Frontend hot reload (Vite HMR)

```bash
# Sync frontend code từ source sang deploy
rsync -av --delete \
  --exclude='node_modules' --exclude='dist' --exclude='logs' \
  /home/<user>/Projects/bsv/bsv-network-sketcher/frontend/ \
  /opt/bsv-ns-deploy/frontend/

# Vite dev server sẽ tự động hot reload (HMR)
# Kiểm tra log: tail -f /opt/bsv-ns-deploy/frontend/logs/vite.log
```

### Backend reload (Uvicorn --reload)

```bash
# Sync backend code từ source sang deploy
rsync -av --delete \
  --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='data' --exclude='logs' --exclude='exports' \
  /home/<user>/Projects/bsv/bsv-network-sketcher/backend/ \
  /opt/bsv-ns-deploy/backend/

# Uvicorn với --reload sẽ tự động restart khi phát hiện thay đổi
# Kiểm tra log: tail -f /opt/bsv-ns-deploy/backend/logs/uvicorn.log
```

### Sync toàn bộ dự án

```bash
rsync -av --exclude='node_modules' --exclude='venv' --exclude='__pycache__' \
  --exclude='*.pyc' --exclude='.git' --exclude='*.db' --exclude='dist' \
  --exclude='logs' --exclude='exports' \
  /home/<user>/Projects/bsv/bsv-network-sketcher/ /opt/bsv-ns-deploy/
```

**Lưu ý:**
- Sử dụng `--delete` để xóa file không còn tồn tại trong source
- Exclude các thư mục build/runtime để tránh mất dữ liệu
- Frontend HMR nhanh hơn (~100ms), backend reload chậm hơn (~1-2s)

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

## 8. Quản lý process (kiểm tra / dừng / khởi động lại)

### 8.1. Kiểm tra process đang chạy

```bash
# Kiểm tra tất cả process BE/FE
ps aux | grep -E "uvicorn|vite" | grep -v grep

# Chỉ kiểm tra backend (Uvicorn)
ps aux | grep uvicorn | grep -v grep

# Chỉ kiểm tra frontend (Vite)
ps aux | grep vite | grep -v grep

# Kiểm tra cổng đang lắng nghe
ss -tlnp | grep -E "8000|5173"
```

Nếu không có kết quả → process không chạy, cần khởi động lại.

### 8.2. Kiểm tra sức khỏe nhanh

```bash
# Backend: gọi API health
curl -s http://localhost:8000/health
# Kỳ vọng: {"status":"healthy"}

# Frontend: kiểm tra Vite dev server
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173
# Kỳ vọng: 200
```

### 8.3. Dừng process

```bash
# Dừng backend (Uvicorn)
pkill -f "uvicorn app.main:app"

# Dừng frontend (Vite)
pkill -f "vite.*--port 5173"

# Dừng cả hai
pkill -f "uvicorn app.main:app" ; pkill -f "vite.*--port 5173"

# Nếu pkill không dừng được, dùng kill -9
pkill -9 -f "uvicorn app.main:app"
pkill -9 -f "vite.*--port 5173"
```

### 8.4. Khởi động lại

```bash
# --- Backend ---
cd /opt/bsv-ns-deploy/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 &
echo "Backend PID: $!"

# --- Frontend ---
cd /opt/bsv-ns-deploy/frontend
npm run dev -- --port 5173 > logs/vite.log 2>&1 &
echo "Frontend PID: $!"
```

### 8.5. Khởi động lại toàn bộ (stop + sync + start)

Khi cần restart sạch kèm cập nhật code mới nhất:

```bash
# 1. Dừng tất cả
pkill -f "uvicorn app.main:app" ; pkill -f "vite.*--port 5173"
sleep 2

# 2. Sync code mới nhất
rsync -av --delete \
  --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='data' --exclude='logs' --exclude='exports' \
  /home/<user>/Projects/bsv/bsv-network-sketcher/backend/ \
  /opt/bsv-ns-deploy/backend/

rsync -av --delete \
  --exclude='node_modules' --exclude='dist' --exclude='logs' \
  /home/<user>/Projects/bsv/bsv-network-sketcher/frontend/ \
  /opt/bsv-ns-deploy/frontend/

# 3. Khởi động backend
cd /opt/bsv-ns-deploy/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 &

# 4. Khởi động frontend
cd /opt/bsv-ns-deploy/frontend
npm run dev -- --port 5173 > logs/vite.log 2>&1 &

# 5. Kiểm tra
sleep 3
ps aux | grep -E "uvicorn|vite" | grep -v grep
curl -s http://localhost:8000/health
```

### 8.6. Xem log khi gặp sự cố

```bash
# Backend log (theo dõi real-time)
tail -f /opt/bsv-ns-deploy/backend/logs/uvicorn.log

# Frontend log (theo dõi real-time)
tail -f /opt/bsv-ns-deploy/frontend/logs/vite.log

# Xem 50 dòng cuối
tail -50 /opt/bsv-ns-deploy/backend/logs/uvicorn.log
tail -50 /opt/bsv-ns-deploy/frontend/logs/vite.log
```

### 8.7. Xử lý sự cố thường gặp

| Triệu chứng | Nguyên nhân có thể | Cách xử lý |
|---|---|---|
| `curl localhost:8000` không phản hồi | Uvicorn không chạy hoặc crash | Kiểm tra log, khởi động lại backend |
| `curl localhost:5173` không phản hồi | Vite không chạy | Kiểm tra log, khởi động lại frontend |
| Cổng bị chiếm (`Address already in use`) | Process cũ chưa dừng hẳn | `pkill -9 -f uvicorn` hoặc `pkill -9 -f vite`, đợi 2s rồi start lại |
| Backend crash liên tục | Lỗi code hoặc thiếu dependency | Xem log, sửa code hoặc chạy `pip install -r requirements.txt` |
| Frontend HMR không hoạt động | Vite watcher lỗi | Restart Vite; kiểm tra `fs.inotify.max_user_watches` trên Linux |
| API trả 500 | Lỗi backend logic | Xem `logs/uvicorn.log` để tìm traceback |
| DB bị khóa (`database is locked`) | Nhiều writer đồng thời hoặc WAL | Đợi hoặc restart backend; kiểm tra WAL mode |

---

## 9. Khắc phục sự cố khác

- Import lỗi → xem logs + kiểm tra schema.
- Export timeout → tăng timeout hoặc kiểm tra ProcessPool.

---

## 9.1. Tạo admin ban đầu (bắt buộc khi tắt đăng ký)

- **Khuyến nghị:** tắt đăng ký tự do (`ALLOW_SELF_REGISTER=false`).
- Tạo admin trực tiếp trong DB bằng script nội bộ.
- Liên hệ người vận hành để lấy thông tin tài khoản admin.

---

## 10. Tài liệu liên quan

- `WEB_APP_DEVELOPMENT_PLAN.md`
- `docs/TEST_STRATEGY.md`
- `docs/API_SPEC.md`
