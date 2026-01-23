# BRD - Tài liệu yêu cầu nghiệp vụ

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-23  
> **Phạm vi:** Ứng dụng web Network Sketcher (port từ repo gốc)  
> **Nguyên tắc:** Tối giản, chính xác tuyệt đối, UX tiện dụng, **không triển khai CLI**.

---

## 1. Mục tiêu kinh doanh

- Thay thế hoàn toàn quy trình tạo sơ đồ từ Network Sketcher CLI/GUI bằng web app nội bộ.
- Bảo đảm **đầu ra tương thích** với Network Sketcher gốc (PPTX/Excel/sơ đồ).
- Giảm thời gian thao tác và sai sót nhờ UI/UX trực quan.

## 2. Bối cảnh hiện tại

- Công cụ gốc là Network Sketcher CLI/GUI, thao tác thủ công nhiều bước.
- Người dùng nội bộ cần quy trình nhập liệu, chỉnh sửa, xuất sơ đồ nhanh hơn.

## 3. Phạm vi

- Web app quản lý project, nhập dữ liệu, chỉnh sửa sơ đồ L1/L2/L3, xuất PPTX/Excel.
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

- Nhập dữ liệu từ Excel/CSV đúng chuẩn NS gốc.
- Tạo/sửa sơ đồ trực quan L1/L2/L3 trong UI.
- Xuất PPTX/Excel với bố cục tương đương CLI gốc.
- Quản lý dự án và lịch sử xuất.
- Hệ màu, hình vẽ, nét vẽ thống nhất giữa UI và export.

## 7. KPI/tiêu chí thành công

- Độ tương thích đầu ra với NS gốc đạt mức chấp nhận (golden files).
- 100% nghiệp vụ lõi thực thi qua UI (không cần CLI).
- Người dùng hoàn tất quy trình tạo sơ đồ trong ≤ 3 bước chính.

## 8. Ràng buộc & giả định

- Công nghệ cố định theo Option A (FastAPI + SQLite + Vue 3 + Konva).
- Hạ tầng triển khai tối giản (single host).
- Dữ liệu nhạy cảm nội bộ, không yêu cầu public internet.

## 9. Rủi ro chính

- Sai khác bố cục xuất PPTX so với NS gốc.
- Sai lệch logic nhập liệu do mapping không đầy đủ.
- UX phức tạp nếu không tối giản luồng thao tác.

---

## 10. Tài liệu liên quan

- `PROJECT_TOPOLOGY.md`
- `WEB_APP_DEVELOPMENT_PLAN.md`
- `docs/PRD.md`
- `docs/SRS.md`
