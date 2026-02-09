# Checklist phát hành & tiêu chí chấp nhận (Release Checklist)

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-02-09  
> **Mục tiêu:** Đảm bảo hệ thống đạt mức tối thiểu để phát hành ổn định, đúng logic và dễ vận hành.

---

## 1. Phạm vi

- Áp dụng cho **MVP nội bộ** và các lần phát hành kế tiếp.
- Ưu tiên **tính đúng logic** và **truy vết**, chấp nhận hiệu năng vừa phải.

---

## 2. Tiêu chí chấp nhận (Acceptance Criteria)

### 2.1 Dữ liệu & logic
- Template đầu vào **hợp lệ theo schema** (`schemas/template.json`).
- Rule-based checks **không có lỗi mức ERROR** (`docs/RULE_BASED_CHECKS.md`).
- Liên lớp L1→L2→L3 đúng (không tạo interface ảo sai).

### 2.2 Xuất dữ liệu
- Export L1/L2/L3 thành công cho **small** và **medium**.
- File xuất có metadata version (version_id + timestamp nếu cấu hình bật).
- Job export có trạng thái rõ ràng: pending → processing → completed/failed.

### 2.3 UI/UX tối thiểu
- Tạo project → thêm area/device/link → export được qua UI.
- Có thông báo lỗi rõ ràng khi validate thất bại.
- L1 liên‑area không tạo spaghetti nghiêm trọng: cùng cặp Area có thể tách multi-channel corridor.
- Tuyến fallback liên‑area không đi ngoài đường bao sơ đồ.

### 2.4 Ổn định & giới hạn
- Không crash khi xử lý small/medium.
- Không mất dữ liệu khi refresh hoặc thao tác đồng thời (mức nội bộ ~5 user).

---

## 3. Giới hạn vận hành (mặc định MVP)

> Các giới hạn này **có thể điều chỉnh** theo thực tế và cấu hình admin.

- **Small:** ≤ 50 devices, ≤ 100 links.
- **Medium:** ≤ 300 devices, ≤ 600 links.
- **Large:** ≤ 1000 devices, ≤ 1500 links (chỉ chạy regression định kỳ).

---

## 4. Versioning & retention

- Snapshot project: mặc định giữ **20 phiên bản gần nhất**.
- Cấu hình hệ thống: mặc định giữ **10 phiên bản gần nhất**.
- Mọi thao tác restore phải ghi audit log.

---

## 5. Vận hành tối giản

- Backup SQLite **trước mỗi phát hành** và **trước khi đổi cấu hình**.
- Có quy trình restore nhanh (restore file DB + restart service).
- Audit log bật mặc định cho thao tác quản trị.

---

## 6. Bảo mật tối thiểu

- Tối thiểu có **role Admin/User** và phân quyền export/restore.
- Input validation áp dụng cho mọi endpoint quan trọng.
- JWT secret key đủ mạnh và có chính sách đổi định kỳ (nếu cần).

---

## 7. Checklist phát hành (release gate)

- [ ] Validate template small/medium đều **VALID**.
- [ ] Rule-based checks không có ERROR.
- [ ] Export PPTX L1/L2/L3 với small/medium thành công.
- [ ] UI flow tạo project → nhập dữ liệu → export chạy trơn tru.
- [ ] Audit log hoạt động cho thao tác quản trị.
- [ ] Line jump/arc hiển thị đúng tại giao điểm link (intra-area và inter-area).
- [ ] Cặp Area có mật độ link cao được tách multi-channel corridor và không dồn vào 1 lane duy nhất.
- [ ] Không có tuyến fallback liên‑area chạy ngoài vùng thiết kế sơ đồ.
- [ ] Backup DB trước khi phát hành.

---

## 8. Tài liệu liên quan

- `docs/TEST_STRATEGY.md`
- `docs/RULE_BASED_CHECKS.md`
- `docs/TEMPLATE_SCHEMA.md`
- `docs/SECURITY_SPEC.md`
- `docs/ADMIN_CONFIG_SCHEMA.md`
