# Traceability Matrix (rút gọn)

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-23  
> **Mục tiêu:** Theo dõi liên kết tối giản giữa BRD → PRD → SRS → API/Schema.

---

## 1. Ma trận truy vết (tối giản)

| BRD (mục tiêu) | PRD (tính năng) | SRS (yêu cầu) | Tài liệu kỹ thuật |
|---|---|---|---|
| Nhập liệu trực tiếp, đúng chuẩn | FR-02, FR-03 | 2.2, 2.7, 3 | `docs/TEMPLATE_SCHEMA.md`, `docs/API_SPEC.md` |
| Xuất PPTX/Excel theo layout mode | FR-06, FR-10 | 2.5, 6 | `WEB_APP_DEVELOPMENT_PLAN.md`, Golden files |
| UI/UX tối giản, rõ lỗi | NFR UX | 4, 6 | `docs/DIAGRAM_STYLE_SPEC.md` |
| Đồng bộ L1→L2→L3 | FR-05 | 2.4 | `WEB_APP_DEVELOPMENT_PLAN.md` |
| An toàn tối thiểu | NFR Security | 6 | `WEB_APP_DEVELOPMENT_PLAN.md` |
| Versioning topology | FR-11 | 2.1, 2.5, 3.1 | `docs/API_SPEC.md` |
| Cấu hình preset/layout | FR-12 | 2.8 | `docs/API_SPEC.md` |
| Preview/Export có metadata phiên bản | FR-13 | 2.5 | `docs/API_SPEC.md` |

---

## 2. Quy tắc sử dụng

- Chỉ dùng để **đối chiếu nhanh**, không mở rộng thành quy trình nặng.
- Khi thêm/sửa yêu cầu, cập nhật dòng tương ứng.

---

## 3. Tài liệu liên quan

- `docs/BRD.md`
- `docs/PRD.md`
- `docs/SRS.md`
- `docs/API_SPEC.md`
- `docs/TEMPLATE_SCHEMA.md`
- `docs/DIAGRAM_STYLE_SPEC.md`
- `docs/TEST_STRATEGY.md`
- `docs/NS_REFERENCE.md`
