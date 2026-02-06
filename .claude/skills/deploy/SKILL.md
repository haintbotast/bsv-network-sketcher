---
name: deploy
description: Đồng bộ code từ repo sang thư mục triển khai /opt/bsv-ns-deploy. Dùng sau khi sửa code backend/frontend.
disable-model-invocation: false
---

Đồng bộ code từ repo sang thư mục triển khai.

## Quy tắc AN TOÀN (bắt buộc)

- **KHÔNG BAO GIỜ** sync thư mục `data/`, `venv/`, `logs/`, `exports/`, `uploads/`
- **KHÔNG BAO GIỜ** dùng `rsync --delete` mà không có đầy đủ exclude flags
- Uvicorn --reload tự nhận code mới, KHÔNG restart service

## Bước thực hiện

### 1. Sync backend
```bash
rsync -av \
  --exclude='data/' \
  --exclude='venv/' \
  --exclude='logs/' \
  --exclude='exports/' \
  --exclude='uploads/' \
  --exclude='__pycache__/' \
  /home/haint/Projects/bsv/bsv-network-sketcher/backend/ \
  /opt/bsv-ns-deploy/backend/
```

### 2. Sync frontend (nếu có thay đổi frontend)
```bash
rsync -av \
  --exclude='node_modules/' \
  --exclude='dist/' \
  /home/haint/Projects/bsv/bsv-network-sketcher/frontend/ \
  /opt/bsv-ns-deploy/frontend/
```

### 3. Báo cáo
- Liệt kê files đã sync
- Xác nhận uvicorn sẽ tự reload

Nếu argument `$ARGUMENTS` chứa "all" hoặc "frontend", sync cả frontend. Mặc định chỉ sync backend.
