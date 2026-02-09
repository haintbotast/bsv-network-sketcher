# BRD - Tài liệu yêu cầu nghiệp vụ

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-02-06  
> **Phạm vi:** Ứng dụng web Network Sketcher (port từ repo gốc)  
> **Nguyên tắc:** Tối giản, chính xác tuyệt đối, UX tiện dụng, **không triển khai CLI**.

---

## 1. Mục tiêu kinh doanh

- Thay thế hoàn toàn quy trình tạo sơ đồ từ Network Sketcher CLI/GUI bằng web app nội bộ.
- Bảo đảm **đầu ra theo một style chung** (chuẩn nội bộ); NS gốc chỉ là tham chiếu logic.
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
- Xuất PPTX/Excel theo **style chung**.
- Quản lý dự án và lịch sử xuất.
- Quản lý phiên bản topology (tạo snapshot, xem lại, khôi phục).
- Export/preview có thông tin phiên bản để truy vết.
- Lưu vết thay đổi (audit log) cho thao tác quan trọng.
- Hệ màu, hình vẽ, nét vẽ thống nhất giữa UI và export theo **Style Spec**.
- Có **style chung + preset**; **Flexible** có kiểm soát khi cần.
- Validation logic L1→L2→L3 chặt chẽ hơn.
- Ràng buộc kết nối L1 theo tầng (Access/Distribution/Server) để đảm bảo đúng logic vật lý.
- Cho phép **chỉnh anchor port thủ công** (side + offset_ratio) để tinh chỉnh đường kết nối; `offset_ratio` có thể để `null` để giữ **auto offset**.
- Cho phép **xem/chỉnh/tạo/xóa kết nối L1 theo port** ngay trong bảng thuộc tính thiết bị, có kiểm tra trùng và port đã dùng.
- Auto-layout tự chạy khi mở project và sau CRUD topology; thao tác viewport (`pan/zoom/reset view`) không làm thay đổi layout.
- Khi có placement map `grid_row/grid_col`, macro layout phải bám lưới theo cơ chế **cột center-slot** để giữ area gần bố cục PDF chuẩn dù có area rộng bất thường.
- Cho phép bật chế độ chỉnh vị trí thủ công để kéo‑thả `Area/Device`; vị trí được lưu ngay sau drag‑end và không bị auto-layout tự động ghi đè ngay lập tức.
- Cụm điều khiển chính (`zoom/reset/L1/L2/L3/Sửa vị trí`) cần nằm ở main navigator panel và **canh giữa theo panel**; khi drag object phải có gióng/snap để căn chỉnh nhanh theo object liên quan.
- Tọa độ chỉnh tay cần theo bộ mốc chuẩn X/Y (step mặc định 0.25 đv) để vận hành dễ kiểm soát và đồng nhất giữa người dùng.
- Quy ước L1 bắt buộc theo sơ đồ chuẩn: **uplink đặt ở top của object**, **kết nối còn lại đặt ở bottom** (trừ khi người dùng override thủ công).
- Endpoint của link L1 phải bám đúng ô port trên object; lane separation chỉ áp dụng sau đoạn stub rời port để tránh lệch điểm nối so với nhãn port.
- Nhãn port trong L1 phải là **thành phần của object** (không là nhãn nổi trên link); kích thước object co giãn theo số lượng/độ dài port để giữ bố cục rõ ràng như PDF chuẩn.
- L1 phải ưu tiên phong cách kỹ thuật dễ đọc: đường orthogonal/góc vuông rõ và giảm màu nhấn cho kết nối LAN/DEFAULT.
- L1 routing phải tránh xuyên object không liên quan và giữ khoảng cách rẽ đầu tiên đủ xa port band để sơ đồ dày vẫn đọc được.
- Liên‑area routing phải tách được nhiều corridor channel theo cặp Area, tránh hiện tượng “spaghetti” khi số link lớn.
- Hệ thống phải ưu tiên lane ít tắc bằng cơ chế occupancy cho cả tuyến A\* và tuyến pad/fallback.
- Fallback liên‑area phải giữ tuyến trong vùng thiết kế sơ đồ, không chạy vòng ngoài canvas.
- Micro layout trong từng Area cần căn giữa các hàng thiết bị khi xuống nhiều hàng để bố cục object cân đối và chuyên nghiệp hơn.
- UI L1 cần hiển thị khung Area theo dạng compact bám cụm thiết bị (giảm khoảng trắng lớn) nhưng không làm đổi dữ liệu Area gốc.
- Kết nối peer-control (`STACK/HA/HSRP`) cần được thể hiện riêng bằng màu/nét/lane để đội vận hành nhận biết nhanh trong sơ đồ dày; tab **Bố cục** cần có khối khai báo nhanh và legend màu/nét/chú giải cho nhóm kết nối này.
- Bảo vệ dữ liệu dự án (phân quyền theo project, kiểm soát upload/download).
- Cho phép quản trị preset/layout/validation qua trang cấu hình (không hardcode).

## 7. KPI/tiêu chí thành công

- Đầu ra đúng chuẩn style chung (golden files hoặc rule-based).
- 100% nghiệp vụ lõi thực thi qua UI (không cần CLI).
- Người dùng hoàn tất quy trình tạo sơ đồ trong ≤ 3 bước chính.
- Có thể khôi phục phiên bản topology trước đó trong ≤ 2 thao tác.

## 8. Ràng buộc & giả định

- Công nghệ cố định theo Option A (FastAPI + SQLite + Vue 3 + Konva).
- Hạ tầng triển khai tối giản (single host).
- Dữ liệu nhạy cảm nội bộ, không yêu cầu public internet.

## 9. Rủi ro chính

- Sai khác bố cục xuất PPTX so với style chung.
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
