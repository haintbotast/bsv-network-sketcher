---
name: sync-check
description: Kiểm tra tài liệu cần cập nhật sau thay đổi code. Đối chiếu với quy tắc trong CLAUDE.md.
argument-hint: "[số commit hoặc range, VD: 3 hoặc HEAD~5..HEAD]"
context: fork
agent: Explore
---

Kiểm tra xem có tài liệu nào cần cập nhật sau các thay đổi code gần đây.

## Quy tắc đồng bộ tài liệu (từ CLAUDE.md)

| Loại thay đổi | Tài liệu cần cập nhật |
|---------------|----------------------|
| API hoặc schema | `docs/API_SPEC.md`, `docs/TEMPLATE_SCHEMA.md` |
| Hình khối/màu/nét/chữ | `docs/DIAGRAM_STYLE_SPEC.md` |
| Kiểm thử | `docs/TEST_STRATEGY.md` |
| Triển khai | `docs/DEPLOYMENT_GUIDE.md` |
| Admin config | `docs/ADMIN_CONFIG_SCHEMA.md`, `docs/ADMIN_UI_FLOW.md` |
| Rule-based checks | `docs/RULE_BASED_CHECKS.md` |
| Topology/deploy/luồng dữ liệu | `PROJECT_TOPOLOGY.md` |
| Tiêu chí phát hành | `docs/RELEASE_CHECKLIST.md` |
| NS reference | `docs/NS_REFERENCE.md` |
| Yêu cầu nghiệp vụ/sản phẩm/kỹ thuật | `docs/BRD.md`, `docs/PRD.md`, `docs/SRS.md` |

## Bước thực hiện

### 1. Xác định range commits

- Nếu argument là số (VD: `3`) → kiểm tra 3 commits gần nhất: `HEAD~3..HEAD`
- Nếu argument là range (VD: `abc123..HEAD`) → dùng trực tiếp
- Mặc định: `HEAD~1..HEAD` (commit gần nhất)

### 2. Lấy danh sách files thay đổi
```bash
git diff --name-only {RANGE}
```

### 3. Phân loại thay đổi

Dựa trên path của files thay đổi:
- `backend/app/api/` hoặc `backend/app/schemas/` → API/schema
- `frontend/src/components/Canvas*` hoặc chứa style/color/font → Style
- `backend/tests/` hoặc `frontend/tests/` → Test
- `backend/app/services/export*` hoặc deploy-related → Deploy
- `backend/app/api/v1/endpoints/admin*` → Admin
- `backend/app/api/v1/endpoints/layout*` hoặc `topology_normalizer*` → Topology
- `templates/` → Template

### 4. Đối chiếu với tài liệu

Với mỗi loại thay đổi, kiểm tra:
- File tài liệu tương ứng có được cập nhật trong cùng range không
- Nếu chưa → đánh dấu cần review

### 5. Báo cáo

Danh sách:
- [OK] Docs đã cập nhật cùng commit
- [REVIEW] Docs cần kiểm tra/cập nhật (kèm lý do)
- [SKIP] Thay đổi không ảnh hưởng tài liệu
