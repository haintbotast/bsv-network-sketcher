# PRD - Tài liệu yêu cầu sản phẩm

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-30  
> **Nguyên tắc:** Tối giản nhưng chính xác tuyệt đối, UX tiện dụng, không CLI.

---

## 1. Tầm nhìn sản phẩm

Web Network Sketcher là ứng dụng nội bộ giúp tạo/sửa/xuất sơ đồ mạng L1/L2/L3 từ dữ liệu chuẩn, đảm bảo đầu ra theo **layout mode** đã chọn (Cisco/ISO/custom).

## 2. Đối tượng người dùng (personas)

- **Kỹ sư mạng:** cần tạo sơ đồ nhanh, đúng chuẩn, ít thao tác.
- **Người làm báo cáo:** cần xuất PPTX/Excel chuẩn, đồng nhất layout.

## 3. Hành trình người dùng (user journey)

1) Tạo project → 2) Chọn template hoặc nhập liệu trực tiếp → 3) Kiểm tra/Chỉnh sửa sơ đồ → 4) Xuất PPTX/Excel → 5) Tải file

## 4. Yêu cầu chức năng (FR)

- **FR-01:** Quản lý project (tạo/sửa/xóa/nhân bản).
- **FR-02:** Nhập liệu trực tiếp bằng form/bảng theo schema chuẩn, có kiểm tra hợp lệ tức thì.
- **FR-03:** Thư viện template dữ liệu chuẩn (tạo/sửa/áp dụng phiên bản).
- **FR-04:** Hiển thị và chỉnh sửa sơ đồ L1/L2/L3 bằng canvas.
- **FR-05:** Đồng bộ dữ liệu giữa các lớp L1→L2→L3 theo quy tắc logic chuẩn.
- **FR-05A:** Ràng buộc kết nối L1 theo tầng: thiết bị HO/IT/Department/Project chỉ uplink tới Access cùng Area; Access uplink tới Distribution; Server chỉ nối tới Server Switch.
- **FR-06:** Xuất PPTX/Excel theo layout mode đã chọn.
- **FR-07:** Lưu/khôi phục trạng thái, lịch sử xuất.
- **FR-08:** Tìm kiếm nhanh thiết bị/kết nối trong project.
- **FR-09:** Quản lý style theo **Style Spec** (layout mode + preset; Flexible có kiểm soát).
- **FR-10:** Cho phép chọn layout mode (Cisco/ISO/custom) theo project.
- **FR-11:** Quản lý phiên bản topology (snapshot, xem, khôi phục).
- **FR-12:** Trang cấu hình quản trị preset/layout/validation (không hardcode).
- **FR-13:** Export/preview gắn metadata phiên bản (version label, time, user).

## 5. Yêu cầu phi chức năng (NFR)

- **Chính xác:** Đầu ra đúng logic và layout mode (golden files hoặc rule-based).
- **UX:** Thao tác tối giản, lỗi hiển thị rõ ràng.
- **Hiệu năng:** Chấp nhận thấp hơn để đổi lấy độ đúng; vẫn cần phản hồi hợp lý cho ~5 người dùng.
- **Ổn định:** Job xuất không chạy trùng, có retry giới hạn.
- **An toàn tối thiểu:** Phân quyền project, kiểm soát upload/download.
- **Truy vết:** Có audit log cho thao tác thay đổi topology/cấu hình.

## 6. Nguyên tắc UX/UI

- Luồng thao tác ngắn (≤ 3 bước chính).
- Hiển thị trạng thái rõ ràng (loading/success/fail).
- Hệ màu, hình vẽ, nét vẽ thống nhất (design tokens).
- Cho phép chọn layout mode (Cisco/ISO/custom) và preset để đảm bảo nhất quán.

## 7. Ngoài phạm vi

- Không CLI, không Docker/Redis/Celery.
- Không tối ưu hiệu năng cho quy mô lớn (> 20 người dùng).

## 8. Tiêu chí chấp nhận (Acceptance)

- Import/export đúng chuẩn, kiểm tra bằng golden files hoặc rule-based.
- UI cho phép chỉnh sửa sơ đồ mà không cần thao tác thủ công ngoài.
- Xử lý lỗi nhập liệu rõ ràng, không mất dữ liệu.
- Có thể khôi phục phiên bản topology trước đó.

---

## 9. Tài liệu liên quan

- `PROJECT_TOPOLOGY.md`
- `WEB_APP_DEVELOPMENT_PLAN.md`
- `docs/BRD.md`
- `docs/SRS.md`
- `docs/DIAGRAM_STYLE_SPEC.md`
- `docs/API_SPEC.md`
- `docs/TEMPLATE_SCHEMA.md`
- `docs/TEST_STRATEGY.md`
- `docs/NS_REFERENCE.md`
- `docs/ADMIN_CONFIG_SCHEMA.md`
- `docs/ADMIN_UI_FLOW.md`
