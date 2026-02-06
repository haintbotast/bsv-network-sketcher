---
name: run-layout
description: Chạy auto-layout cho project trên deploy server qua API. Dùng sau khi sửa layout code hoặc import template.
argument-hint: "[project_id]"
disable-model-invocation: true
---

Chạy auto-layout cho project qua REST API trên deploy server (localhost:8000).

## Thông tin kết nối

- **API base**: `http://localhost:8000/api/v1`
- **Auth**: POST `/auth/login` → `{"email":"admin@example.com","password":"Bsvns2026"}`
- **Layout endpoint**: POST `/projects/{project_id}/auto-layout`

## Project mặc định

Nếu không có argument, dùng project "Network diagram":
- **ID**: `837f6a3a-e288-46af-a42e-f23e299beb1a`

## Bước thực hiện

### 1. Lấy token
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"Bsvns2026"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
```

### 2. Gọi auto-layout
```bash
curl -s -X POST "http://localhost:8000/api/v1/projects/{PROJECT_ID}/auto-layout" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"layout_scope":"project","apply_to_db":true,"group_by_area":true,"normalize_topology":false,"anchor_routing":true,"overview_mode":"l1-only"}'
```

### 3. Parse và hiển thị kết quả

Dùng python3 inline để parse JSON response:
- Danh sách areas (tên, width x height) — bỏ qua areas có tên kết thúc `_wp_`
- Tổng số devices
- Tổng số areas (không tính waypoint)

## Tham số layout

| Tham số | Giá trị | Ghi chú |
|---------|---------|---------|
| layout_scope | project | Toàn bộ project |
| apply_to_db | true | Lưu kết quả vào DB |
| group_by_area | true | Nhóm devices theo area |
| normalize_topology | false | Không di chuyển devices giữa areas |
| anchor_routing | true | Routing qua anchors |
| overview_mode | l1-only | Chỉ layout L1 |
