# BRD - Tài liệu yêu cầu nghiệp vụ

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-30  
> **Phạm vi:** Ứng dụng web Network Sketcher (port từ repo gốc)  
> **Nguyên tắc:** Tối giản, chính xác tuyệt đối, UX tiện dụng, **không triển khai CLI**.

---

## 1. Mục tiêu kinh doanh

- Thay thế hoàn toàn quy trình tạo sơ đồ từ Network Sketcher CLI/GUI bằng web app nội bộ.
- Bảo đảm **đầu ra theo chuẩn layout network phổ biến** (Cisco/ISO/custom); NS gốc chỉ là tham chiếu logic.
- Giảm thời gian thao tác và sai sót nhờ UI/UX trực quan.

## 2. Bối cảnh hiện tại

- Công cụ gốc là Network Sketcher CLI/GUI, thao tác thủ công nhiều bước.
- Người dùng nội bộ cần quy trình nhập liệu, chỉnh sửa, xuất sơ đồ nhanh hơn.

## 3. Phạm vi

- Web app quản lý project, **nhập liệu trực tiếp theo mẫu chuẩn**, chỉnh sửa sơ đồ L1/L2/L3, xuất PPTX/Excel.
- Có thư viện template dữ liệu chuẩn (JSON) để khởi tạo nhanh dự án.
- Hỗ trợ đa người dùng nội bộ (~5 đồng thời), không yêu cầu scale lớn.
- Lưu trữ dữ liệu nội bộ bằng SQLite và file system cục bộ.

## 4. Ngoài phạm vi

- Không xây dựng/duy trì CLI mới.
- Không triển khai Docker/Redis/Celery.
- Không tối ưu hiệu năng vượt yêu cầu (ưu tiên đúng logic hơn tốc độ).

## 5. Stakeholders

- **Owner nghiệp vụ:** Nhóm vận hành mạng (nội bộ).
- **Người dùng chính:** Kỹ sư mạng, người làm báo cáo sơ đồ.
- **Kỹ thuật:** Nhóm phát triển nội bộ.

## 6. Yêu cầu nghiệp vụ cấp cao

- Nhập liệu trực tiếp theo mẫu chuẩn (form/bảng) với kiểm tra hợp lệ tại chỗ.
- Thư viện template dữ liệu chuẩn để áp dụng nhanh cho project.
- (Tùy chọn) Hỗ trợ nhập từ Excel/CSV khi cần đối soát hoặc chuyển đổi dữ liệu cũ.
- Tạo/sửa sơ đồ trực quan L1/L2/L3 trong UI.
- Xuất PPTX/Excel theo **layout mode đã chọn**.
- Quản lý dự án và lịch sử xuất.
- Quản lý phiên bản topology (tạo snapshot, xem lại, khôi phục).
- Export/preview có thông tin phiên bản để truy vết.
- Lưu vết thay đổi (audit log) cho thao tác quan trọng.
- Hệ màu, hình vẽ, nét vẽ thống nhất giữa UI và export theo **Style Spec**.
- Có **layout mode chọn** (Cisco/ISO/custom) + preset; **Flexible** có kiểm soát khi cần.
- Validation logic L1→L2→L3 chặt chẽ hơn.
- Ràng buộc kết nối L1 theo tầng (Access/Distribution/Server) để đảm bảo đúng logic vật lý.
- Bảo vệ dữ liệu dự án (phân quyền theo project, kiểm soát upload/download).
- Cho phép quản trị preset/layout/validation qua trang cấu hình (không hardcode).

## 7. KPI/tiêu chí thành công

- Đầu ra đúng chuẩn layout đã chọn (golden files theo mode hoặc rule-based).
- 100% nghiệp vụ lõi thực thi qua UI (không cần CLI).
- Người dùng hoàn tất quy trình tạo sơ đồ trong ≤ 3 bước chính.
- Có thể khôi phục phiên bản topology trước đó trong ≤ 2 thao tác.

## 8. Ràng buộc & giả định

- Công nghệ cố định theo Option A (FastAPI + SQLite + Vue 3 + Konva).
- Hạ tầng triển khai tối giản (single host).
- Dữ liệu nhạy cảm nội bộ, không yêu cầu public internet.

## 9. Rủi ro chính

- Sai khác bố cục xuất PPTX so với layout mode đã chọn.
- Sai lệch logic nhập liệu do mapping không đầy đủ.
- UX phức tạp nếu không tối giản luồng thao tác.

---

## 10. Tài liệu liên quan

- `PROJECT_TOPOLOGY.md`
- `WEB_APP_DEVELOPMENT_PLAN.md`
- `docs/PRD.md`
- `docs/SRS.md`
- `docs/DIAGRAM_STYLE_SPEC.md`
- `docs/API_SPEC.md`
- `docs/TEMPLATE_SCHEMA.md`
- `docs/TEST_STRATEGY.md`
- `docs/NS_REFERENCE.md`
- `docs/ADMIN_CONFIG_SCHEMA.md`
- `docs/ADMIN_UI_FLOW.md`
