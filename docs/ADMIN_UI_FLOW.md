# Admin UI Flow (tối giản)

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-23  
> **Mục tiêu:** Gợi ý luồng UI cho trang quản trị cấu hình và lịch sử phiên bản topology.

---

## 1. Trang quản trị cấu hình (Admin Config)

**Luồng đề xuất:**
1) Mở **Admin → Config**
2) Chọn tab: Layout / Style / Validation / Export
3) Sửa giá trị → **Validate** → **Save**
4) Hiển thị diff + audit log entry

**Hiển thị tối thiểu:**
- `layout.default_mode`, `layout.allowed_modes`
- `style.default_theme`, preset size
- `validation` rule cơ bản
- `export` default format + include metadata

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

---

## 3. Tài liệu liên quan

- `docs/API_SPEC.md`
- `docs/SRS.md`
- `docs/SECURITY_SPEC.md`
