# PRD - Tài liệu yêu cầu sản phẩm

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-02-09  
> **Nguyên tắc:** Tối giản nhưng chính xác tuyệt đối, UX tiện dụng, không CLI.

---

## 1. Tầm nhìn sản phẩm

Web Network Sketcher là ứng dụng nội bộ giúp tạo/sửa/xuất sơ đồ mạng L1/L2/L3 từ dữ liệu chuẩn, đảm bảo đầu ra theo **style chung** (chuẩn nội bộ).

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
- **FR-06:** Xuất PPTX/Excel theo style chung.
- **FR-07:** Lưu/khôi phục trạng thái, lịch sử xuất.
- **FR-08:** Tìm kiếm nhanh thiết bị/kết nối trong project.
- **FR-09:** Quản lý style theo **Style Spec** (style chung + preset; Flexible có kiểm soát).
- **FR-10:** Chỉ một style chung, **không có lựa chọn layout mode** theo project.
- **FR-11:** Quản lý phiên bản topology (snapshot, xem, khôi phục).
- **FR-12:** Trang cấu hình quản trị preset/layout/validation (không hardcode).
- **FR-13:** Export/preview gắn metadata phiên bản (version label, time, user).
- **FR-14:** Cho phép người dùng **chỉnh thủ công anchor của port** (side + offset_ratio, cho phép `offset_ratio = null` để giữ auto offset) và **giữ override khi chạy lại auto-layout**.
- **FR-15:** Cho phép **xem/chỉnh/tạo/xóa kết nối L1 theo port** ngay trong bảng thuộc tính thiết bị, có kiểm tra trùng và port đã dùng.
- **FR-16:** Auto-layout tự chạy khi mở project và sau CRUD topology; thao tác viewport (`pan/zoom/reset view`) không được trigger auto-layout.
- **FR-16A:** Với project có `grid_row/grid_col` rõ ràng, macro layout phải bám lưới theo cơ chế **center-slot theo cột** để giữ area gần bố cục PDF chuẩn dù có area outlier rất rộng.
- **FR-17:** L1 port anchor mặc định theo chuẩn: **uplink gắn top**, **non-uplink gắn bottom**; override thủ công là ưu tiên cao nhất.
- **FR-17A:** Ở L1, endpoint link phải bám đúng ô port; tách lane/bundle chỉ bắt đầu sau đoạn stub rời port (không lane-shift trực tiếp tại anchor).
- **FR-18:** Trong L1, nhãn port phải hiển thị như **một phần của object** (port band top/bottom) và kích thước object tự nới theo số lượng/độ dài port để khớp sơ đồ chuẩn.
- **FR-19:** Render L1 theo phong cách kỹ thuật: ưu tiên đường orthogonal/góc vuông rõ và dùng màu trung tính cho link LAN/DEFAULT để giảm rối.
- **FR-20:** Khung Area ở L1 được phép hiển thị dạng compact theo cụm thiết bị để giảm khoảng trắng, nhưng không thay đổi dữ liệu Area lưu trong DB.
- **FR-21:** Link `STACK/HA/HSRP` trong L1 phải có style chuyên biệt (màu/nét/lane) và được tách hiển thị khỏi nhóm uplink/data.
- **FR-22:** Cho phép bật chế độ **Sửa vị trí** để kéo‑thả trực tiếp `Area/Device` trên canvas; lưu `position_x/position_y` ngay khi thả và **không trigger auto-layout** từ thao tác này.
- **FR-23:** Nhóm điều khiển `zoom/reset/L1/L2/L3/Sửa vị trí` đặt ở **main navigator panel**, hiển thị **canh giữa theo panel**; khi drag object trong chế độ sửa vị trí phải có **đường gióng/snap alignment** theo object liên quan.
- **FR-24:** Hệ tọa độ thủ công phải dùng **mốc chuẩn X/Y** (step mặc định 0.25 đv); thao tác drag hoặc nhập tay đều được chuẩn hóa về mốc này.
- **FR-25:** Tab **Bố cục** phải có thành phần **khai báo nhanh peer-control** (`HA/STACK/HSRP`) và hiển thị **legend màu/nét/chú giải** để vận hành nhận biết đúng loại kết nối.
- **FR-26:** L1 routing phải giữ khoảng cách an toàn với object (không xuyên device/area không liên quan), đồng thời bảo đảm điểm rẽ đầu tiên không dính sát port band ở sơ đồ mật độ cao.
- **FR-27:** Routing liên‑area phải hỗ trợ **multi-channel corridor** theo cặp Area để giảm dồn/chồng link khi mật độ kết nối cao.
- **FR-28:** Hệ thống phải ghi nhận **occupancy** cho cả tuyến A\* và tuyến pad/fallback để lựa chọn lane có độ tắc thấp hơn cho các link xử lý sau.
- **FR-29:** Fallback liên‑area không được đi ra ngoài đường bao sơ đồ; mọi tuyến phải nằm trong vùng thiết kế.
- **FR-27:** Micro layout trong Area phải **căn giữa các hàng thiết bị** khi layer tách nhiều hàng để tránh dồn trái và tăng độ đối xứng với sơ đồ chuẩn.
- **FR-28:** Hệ tọa độ chuẩn phải hỗ trợ nhập/xuất theo **grid Excel** (`A1:B2`) cho Area và Device; `grid_range` là nguồn chuẩn, `position_x/y` duy trì để tương thích.
- **FR-29:** Bổ sung CRUD **Device Port** độc lập theo từng Device (`name`, `side`, `offset_ratio`) để người dùng chủ động khai báo điểm kết nối trước khi vẽ link.
- **FR-30:** Tạo/sửa link phải kiểm tra endpoint port đã được khai báo trên đúng device; chặn lưu nếu thiếu port.
- **FR-31:** UI canvas phải render port band từ dữ liệu port đã khai báo (không chỉ suy diễn từ link), nhằm giữ object/port đồng nhất với sơ đồ chuẩn.

## 5. Yêu cầu phi chức năng (NFR)

- **Chính xác:** Đầu ra đúng logic và style chung (golden files hoặc rule-based).
- **UX:** Thao tác tối giản, lỗi hiển thị rõ ràng.
- **Hiệu năng:** Chấp nhận thấp hơn để đổi lấy độ đúng; vẫn cần phản hồi hợp lý cho ~5 người dùng.
- **Ổn định:** Job xuất không chạy trùng, có retry giới hạn.
- **An toàn tối thiểu:** Phân quyền project, kiểm soát upload/download.
- **Truy vết:** Có audit log cho thao tác thay đổi topology/cấu hình.

## 6. Nguyên tắc UX/UI

- Luồng thao tác ngắn (≤ 3 bước chính).
- Hiển thị trạng thái rõ ràng (loading/success/fail).
- Hệ màu, hình vẽ, nét vẽ thống nhất (design tokens).
- Style chung + preset để đảm bảo nhất quán.

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
