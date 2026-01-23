# PRD - Tài liệu yêu cầu sản phẩm

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-23  
> **Nguyên tắc:** Tối giản nhưng chính xác tuyệt đối, UX tiện dụng, không CLI.

---

## 1. Tầm nhìn sản phẩm

Web Network Sketcher là ứng dụng nội bộ giúp tạo/sửa/xuất sơ đồ mạng L1/L2/L3 từ dữ liệu chuẩn, đảm bảo đầu ra tương thích Network Sketcher gốc.

## 2. Đối tượng người dùng (personas)

- **Kỹ sư mạng:** cần tạo sơ đồ nhanh, đúng chuẩn, ít thao tác.
- **Người làm báo cáo:** cần xuất PPTX/Excel chuẩn, đồng nhất layout.

## 3. Hành trình người dùng (user journey)

1) Tạo project → 2) Nhập Excel/CSV → 3) Kiểm tra/Chỉnh sửa sơ đồ → 4) Xuất PPTX/Excel → 5) Tải file

## 4. Yêu cầu chức năng (FR)

- **FR-01:** Quản lý project (tạo/sửa/xóa/nhân bản).
- **FR-02:** Nhập dữ liệu Excel/CSV theo chuẩn NS gốc.
- **FR-03:** Hiển thị và chỉnh sửa sơ đồ L1/L2/L3 bằng canvas.
- **FR-04:** Đồng bộ dữ liệu giữa các lớp L1→L2→L3 theo quy tắc NS.
- **FR-05:** Xuất PPTX/Excel theo layout tương đương NS gốc.
- **FR-06:** Lưu/khôi phục trạng thái, lịch sử xuất.
- **FR-07:** Tìm kiếm nhanh thiết bị/kết nối trong project.

## 5. Yêu cầu phi chức năng (NFR)

- **Chính xác:** Đầu ra phải tương thích NS gốc (golden files).
- **UX:** Thao tác tối giản, lỗi hiển thị rõ ràng.
- **Hiệu năng:** Chấp nhận thấp hơn để đổi lấy độ đúng; vẫn cần phản hồi hợp lý cho ~5 người dùng.
- **Ổn định:** Job xuất không chạy trùng, có retry giới hạn.

## 6. Nguyên tắc UX/UI

- Luồng thao tác ngắn (≤ 3 bước chính).
- Hiển thị trạng thái rõ ràng (loading/success/fail).
- Hệ màu, hình vẽ, nét vẽ thống nhất (design tokens).

## 7. Ngoài phạm vi

- Không CLI, không Docker/Redis/Celery.
- Không tối ưu hiệu năng cho quy mô lớn (> 20 người dùng).

## 8. Tiêu chí chấp nhận (Acceptance)

- Import/export đúng chuẩn, so sánh được với output của NS gốc.
- UI cho phép chỉnh sửa sơ đồ mà không cần thao tác thủ công ngoài.
- Xử lý lỗi nhập liệu rõ ràng, không mất dữ liệu.

---

## 9. Tài liệu liên quan

- `PROJECT_TOPOLOGY.md`
- `WEB_APP_DEVELOPMENT_PLAN.md`
- `docs/BRD.md`
- `docs/SRS.md`
