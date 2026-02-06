# Admin UI Flow (tối giản)

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-02-06  
> **Mục tiêu:** Gợi ý luồng UI cho trang quản trị cấu hình và lịch sử phiên bản topology.

---

## 1. Trang quản trị cấu hình (Admin Config)

**Luồng đề xuất:**
1) Mở project và chọn tab **Bố cục** trong panel phải (cạnh **Thuộc tính**) → hệ thống tự chạy auto-layout một lượt.
2) Thực hiện CRUD topology (area/device/link/port-link/anchor override) → hệ thống tự chạy lại auto-layout (debounce).
3) Điều chỉnh nhóm **Bố cục tổng thể** hoặc **Đường nối & nhãn**
4) Dùng cụm điều khiển ở **main navigator panel** (`zoom/reset/L1/L2/L3/Sửa vị trí`) để chuyển chế độ xem/chỉnh; cụm này hiển thị **canh giữa theo panel**
5) (Tuỳ chọn) Bấm **Chạy lại auto-layout** để áp dụng lại bố cục
6) (Tuỳ chọn) Khai báo nhanh link peer-control (`STACK/HA/HSRP`) từ tab **Bố cục** và đối chiếu legend màu/nét/chú giải
7) (Tuỳ chọn) Bật **Sửa vị trí** trên canvas để kéo‑thả `Area/Device` và lưu tọa độ thủ công (có guide/snap alignment, tọa độ chuẩn theo step 0.25 đv)
8) Sửa giá trị → **Validate** → **Save**
9) Hiển thị diff + audit log entry
10) Lưu **config version** mới và cho phép khôi phục

**Ngoại lệ bắt buộc:**
- Thao tác viewport để xem sơ đồ (`pan`, `zoom`, `reset view`) **không được trigger auto-layout**.
- Kéo‑thả chỉnh vị trí thủ công (`Area/Device`) **không được trigger auto-layout**.

**Hiển thị tối thiểu:**
- `layout.default_mode`, `layout.allowed_modes` (cố định `standard`)
- `layout_tuning` (layer_gap, node_spacing, port_label_band, area_gap, area_padding, label_band, max_row_width_base, max_nodes_per_row, row_gap, row_stagger)
- `render_tuning` (bundle_gap, bundle_stub, area_clearance, area_anchor_offset, port_label_offset, label_gap_x/y, corridor_gap)
- `peer_control` quick editor + legend (`STACK/HA/HSRP`, màu/nét/chú giải)
- `style.default_theme`, preset size
- `validation` rule cơ bản + `validation.layout_checks`
- `export` default format + include metadata

**Profile khuyến nghị cho sơ đồ dày link (L1):**
- Tăng `layout_tuning.row_gap` (>= 0.9) để giảm chèn giữa các hàng thiết bị.
- Tăng `render_tuning.bundle_stub` và `render_tuning.port_label_offset` để điểm rẽ đầu tiên rời xa port band.
- Tăng `render_tuning.area_clearance` và `render_tuning.corridor_gap` để giảm tuyến xuyên vùng object khi mật độ cao.

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
