---
name: import-template
description: Import template JSON vào project trên deploy server. Dùng khi cần reset hoặc nạp dữ liệu mới.
argument-hint: "[template_file] [project_id]"
disable-model-invocation: true
---

Import file template JSON vào project qua REST API.

## Thông tin kết nối

- **API base**: `http://localhost:8000/api/v1`
- **Auth**: POST `/auth/login` → `{"email":"admin@example.com","password":"Bsvns2026"}`
- **Import endpoint**: POST `/projects/{project_id}/import`

## Tham số

- `$0` hoặc `$ARGUMENTS[0]`: Đường dẫn file template JSON (bắt buộc)
- `$1` hoặc `$ARGUMENTS[1]`: Project ID (mặc định: `837f6a3a-e288-46af-a42e-f23e299beb1a`)

## Templates có sẵn

| File | Mô tả |
|------|-------|
| `templates/samples/network_diagram_rebuild.json` | Template "Network diagram" đầy đủ (14 areas, 72 devices) |
| `templates/samples/minimal.json` | Template tối thiểu |
| `templates/samples/small.json` | Template nhỏ |
| `templates/samples/medium.json` | Template trung bình |

## Bước thực hiện

### 1. Đọc file template
Đọc file JSON template từ đường dẫn argument.

### 2. Lấy token

### 3. Import qua API

Request body phải có dạng:
```json
{
  "mode": "json",
  "payload": { /* nội dung file template */ },
  "options": {
    "merge_strategy": "replace"
  }
}
```

```bash
curl -s -X POST "http://localhost:8000/api/v1/projects/{PID}/import" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d @/tmp/import_body.json
```

### 4. Báo cáo kết quả
- Số areas, devices, links đã import
- Có lỗi không

## Chú ý

- `merge_strategy: "replace"` sẽ XÓA toàn bộ dữ liệu cũ trong project
- Sau import nên chạy `/run-layout` để tính lại layout
