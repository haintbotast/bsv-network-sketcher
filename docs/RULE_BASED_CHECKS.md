# Quy tắc kiểm tra rule-based (layout & logic)

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-27  
> **Mục tiêu:** Định nghĩa các kiểm tra tối thiểu thay cho golden files, đảm bảo đúng logic và không vỡ bố cục.

---

## 1. Phạm vi áp dụng

- Áp dụng cho **UI (validate tức thì)**, **backend (validate trước export)** và **regression test**.
- Dữ liệu đầu vào là **tọa độ logic (inch)**, không dùng pixel.
- Các kiểm tra chia mức độ: **ERROR** (chặn export), **WARN** (cho phép export nhưng hiển thị cảnh báo), **INFO** (ghi nhận).

---

## 2. Thông số mặc định (nếu layout mode không khai báo)

| Tham số | Giá trị mặc định | Ghi chú |
|---|---|---|
| `area_padding` | 0.15 inch | Khoảng cách tối thiểu device tới biên area |
| `device_gap` | 0.20 inch | Khoảng cách tối thiểu giữa bounding box device |
| `label_gap` | 0.05 inch | Khoảng cách tối thiểu label tới node/link |
| `link_gap` | 0.05 inch | Khoảng cách tối thiểu link tới node không liên quan |
| `overlap_epsilon` | 0.01 inch | Ngưỡng coi như chồng lấn do sai số float |
| `min_link_segment` | 0.10 inch | Độ dài tối thiểu của một đoạn link |

**Nguồn override:** preset theo layout mode hoặc cấu hình admin (xem `docs/ADMIN_CONFIG_SCHEMA.md`).

### 2.1 Khuyến nghị tinh chỉnh (khi cần)

- Ưu tiên giữ tỉ lệ khoảng cách **ổn định theo inch** để không làm lệch export PPTX.
- Chỉ thay đổi từng tham số và chạy lại regression trước khi áp dụng rộng.
- Khung giá trị gợi ý (để tránh bố cục quá chật hoặc quá thưa):
  - `area_padding`: 0.10 – 0.40
  - `device_gap`: 0.15 – 0.60
  - `label_gap`: 0.03 – 0.20
  - `link_gap`: 0.03 – 0.20
  - `overlap_epsilon`: 0.005 – 0.02
  - `min_link_segment`: 0.08 – 0.50

---

## 3. Quy tắc logic bắt buộc (ERROR)

- **RB-001:** L1 link phải trỏ tới device/port tồn tại.
- **RB-002:** Port-channel phải có member hợp lệ, không trùng lặp.
- **RB-003:** Virtual port không được xuất hiện trong L1 links.
- **RB-004:** L2 assignment chỉ gán lên interface tồn tại.
- **RB-005:** L3 address chỉ gán lên interface tồn tại.
- **RB-006:** Không được thay đổi số lượng node/link so với input sau layout.
- **RB-007:** Liên kết khác Area bắt buộc đi qua Waypoint area (đuôi `_wp_`).

---

## 4. Quy tắc hình học tối thiểu

### 4.1 Không chồng lấn (ERROR)
- **RB-101:** Device không được chồng lấn device khác (dùng `device_gap`).
- **RB-102:** Area không được chồng lấn area khác.
- **RB-103:** Device phải nằm trong area tương ứng, cách biên >= `area_padding`.
- **RB-104:** Link không được đi xuyên qua node không liên quan (trừ điểm đầu/cuối).

### 4.2 Nhãn không đè (ERROR)
- **RB-121:** Label của device/link/area không được chồng lên node/link khác (dùng `label_gap`).
- **RB-122:** Interface tag không được đè lên link/node không liên quan.

### 4.3 Khoảng cách tối thiểu (WARN nếu không gây chồng lấn)
- **RB-141:** Khoảng cách giữa device và device < `device_gap` → WARN.
- **RB-142:** Khoảng cách giữa label và node/link < `label_gap` → WARN.
- **RB-143:** Khoảng cách link tới node không liên quan < `link_gap` → WARN.

---

## 5. Quy tắc nhất quán với layout mode (WARN)

- **RB-201:** Hướng bố cục tuân theo layout mode đã chọn (cisco/iso/custom).
- **RB-202:** Nếu `custom` thiếu tham số bố cục, fallback ISO và sinh WARN.
- **RB-203:** Bố cục thiết bị trong Area tuân theo top‑to‑bottom tier (Core/Dist → Access → Endpoints).
- **RB-204:** Overview chỉ hiển thị L1/flow (không render nhãn L2/L3).

---

## 6. Cách xử lý vi phạm

- **ERROR:** Chặn export, highlight đối tượng lỗi trên UI, trả mã lỗi cụ thể.
- **WARN:** Cho phép export nhưng hiển thị cảnh báo + ghi log.
- **INFO:** Chỉ ghi log.

---

## 7. Kiểm thử tối thiểu (traceable)

- Mỗi rule **RB-xxx** phải có ít nhất 1 test unit hoặc integration.
- Regression không dùng golden files phải dựa trên rule set này.

---

## 8. Tài liệu liên quan

- `docs/DIAGRAM_STYLE_SPEC.md`
- `docs/TEMPLATE_SCHEMA.md`
- `docs/TEST_STRATEGY.md`
- `docs/NS_REFERENCE.md`
