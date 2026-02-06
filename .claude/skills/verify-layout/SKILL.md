---
name: verify-layout
description: Kiểm tra tất cả devices nằm trong area bounds sau auto-layout. Phát hiện overflow.
argument-hint: "[project_id]"
disable-model-invocation: false
---

Sau khi chạy auto-layout, verify rằng tất cả devices nằm trong area bounds.

## Thông tin kết nối

- **API base**: `http://localhost:8000/api/v1`
- **Auth**: POST `/auth/login` → `{"email":"admin@example.com","password":"Bsvns2026"}`

## Project mặc định

Nếu không có argument, dùng project "Network diagram":
- **ID**: `837f6a3a-e288-46af-a42e-f23e299beb1a`

## Bước thực hiện

### 1. Lấy token (giống run-layout)

### 2. Fetch layout result
```bash
# Gọi auto-layout hoặc đọc layout hiện tại
curl -s -X POST "http://localhost:8000/api/v1/projects/{PID}/auto-layout" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"layout_scope":"project","apply_to_db":false,"group_by_area":true,"normalize_topology":false,"anchor_routing":true,"overview_mode":"l1-only"}' \
  > /tmp/layout_result.json
```

Chú ý: `apply_to_db: false` để không thay đổi DB, chỉ lấy kết quả.

### 3. Fetch device names
```bash
curl -s "http://localhost:8000/api/v1/projects/{PID}/devices" \
  -H "Authorization: Bearer $TOKEN" > /tmp/devices.json
```

### 4. Verify bằng python3 script

Dùng python3 heredoc inline:
- Load layout_result.json và devices.json
- Build name map: device_id → device_name
- Với mỗi device trong layout:
  - Tìm area chứa device (theo area_id)
  - Kiểm tra device position nằm trong area bounds
  - Đánh dấu [OK] hoặc [OVERFLOW]
- In summary: X/Y devices OK, liệt kê OVERFLOW nếu có

### 5. Kiểm tra thêm

- Area nào có tỉ lệ height/width bất thường (> 3.0 hoặc < 0.1)
- Area nào quá lớn (width > 20 hoặc height > 20)
- Device nào nằm sát cạnh area (< 0.1 inch margin)
