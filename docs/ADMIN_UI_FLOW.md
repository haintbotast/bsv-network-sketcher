# Admin UI Flow (tối giản)

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-30  
> **Mục tiêu:** Gợi ý luồng UI cho trang quản trị cấu hình và lịch sử phiên bản topology.

---

## 1. Trang quản trị cấu hình (Admin Config)

**Luồng đề xuất:**
1) Mở project và chọn tab **Bố cục** trong panel phải (cạnh **Thuộc tính**)
2) Điều chỉnh nhóm **Bố cục tổng thể** hoặc **Đường nối & nhãn**
3) (Tuỳ chọn) Bấm **Chạy lại auto-layout** để áp dụng lại bố cục
4) Sửa giá trị → **Validate** → **Save**
5) Hiển thị diff + audit log entry
6) Lưu **config version** mới và cho phép khôi phục

**Hiển thị tối thiểu:**
- `layout.default_mode`, `layout.allowed_modes`
- `layout_tuning` (layer_gap, node_spacing, port_label_band, area_gap, area_padding, label_band, max_row_width_base, max_nodes_per_row, row_gap, row_stagger)
- `render_tuning` (bundle_gap, bundle_stub, area_clearance, area_anchor_offset, port_label_offset, label_gap_x/y, corridor_gap)
- `style.default_theme`, preset size
- `validation` rule cơ bản + `validation.layout_checks`
- `export` default format + include metadata

**Lịch sử cấu hình:**
- Bảng `version`, `created_at`, `created_by`, `note`
- Nút **Restore** (xác nhận + audit log)

---

## 2. Trang lịch sử phiên bản (Project Versions)

**Luồng đề xuất:**
1) Mở Project → **Versions**
2) Danh sách snapshot: `version`, `created_at`, `created_by`, `note`
3) Chọn version → **Preview** hoặc **Restore**
4) Restore yêu cầu xác nhận + ghi audit log

**Gợi ý UI:**
- Nút **Create Snapshot** trước khi export
- Hiển thị tag `current` cho version đang dùng
- Preview hiển thị **metadata** (version, time, user)

---

## 3. Tài liệu liên quan

- `docs/API_SPEC.md`
- `docs/SRS.md`
- `docs/SECURITY_SPEC.md`
