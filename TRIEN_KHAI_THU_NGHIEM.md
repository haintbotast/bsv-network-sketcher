# Tài liệu triển khai thử nghiệm (tóm tắt)

Tài liệu chi tiết xem: `docs/DEPLOYMENT_TRIAL_PLAN.md`.

## Mục tiêu
- Triển khai thử nghiệm nội bộ, single host.
- Bảo đảm kiểm thử tối thiểu và tiêu chí chấp nhận trước khi dùng thực tế.

## Tham chiếu bắt buộc
- `docs/DEPLOYMENT_TRIAL_PLAN.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `docs/TEST_STRATEGY.md`
- `docs/RELEASE_CHECKLIST.md`

---

## Quy trình phát triển và deploy

### Cấu trúc thư mục

| Thư mục | Mục đích |
|---------|----------|
| `/home/haint/Projects/bsv/bsv-network-sketcher/` | **Source code** - nơi phát triển, commit git |
| `/opt/bsv-ns-deploy/` | **Deploy** - nơi chạy thực tế, có venv + DB |

### Quy trình làm việc

1. **Phát triển** trong thư mục source (`bsv-network-sketcher/`)
2. **Sync code** sang thư mục deploy khi cần test/chạy thực tế
3. **Chạy backend** trong thư mục deploy (có venv sẵn)

### Lệnh sync code

```bash
# Sync backend code
rsync -av --exclude='venv/' --exclude='__pycache__/' --exclude='*.pyc' \
  --exclude='data/' --exclude='logs/' --exclude='exports/' --exclude='uploads/' \
  /home/haint/Projects/bsv/bsv-network-sketcher/backend/app/ \
  /opt/bsv-ns-deploy/backend/app/

# Copy requirements.txt nếu có thay đổi
cp /home/haint/Projects/bsv/bsv-network-sketcher/backend/requirements.txt \
   /opt/bsv-ns-deploy/backend/requirements.txt
```

### Chạy backend (trong thư mục deploy)

```bash
cd /opt/bsv-ns-deploy/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Cài thêm dependencies (nếu cần)

```bash
cd /opt/bsv-ns-deploy/backend
source venv/bin/activate
pip install -r requirements.txt
```

---

## Ghi chú triển khai nhanh (pilot)
- Thư mục triển khai: `/opt/bsv-ns-deploy`
- Backend: `backend/` (FastAPI + SQLite)
- Worker: `backend/app/workers/export_worker.py`
- Frontend: `frontend/` (Vue 3 + Vite)

## Lưu ý
- Ghi nhận commit/tag triển khai trong bảng phiên bản ở `docs/DEPLOYMENT_TRIAL_PLAN.md`.
- Luôn backup SQLite trước khi chạy thử nghiệm chính thức.
- **Không commit thư mục venv, data/*.db, logs/, exports/, uploads/** (đã có trong .gitignore).
- **Cấm** dùng `rsync --delete` nếu **không exclude** `backend/data`, `backend/exports`, `backend/logs`, `backend/uploads`.
- **Không** đồng bộ hoặc ghi đè thư mục `backend/data` khi sync sang `/opt/bsv-ns-deploy`.

## Ghi chú sản phẩm
- Đây là **BSV Network Sketcher**, được port từ **Network Sketcher** gốc.
