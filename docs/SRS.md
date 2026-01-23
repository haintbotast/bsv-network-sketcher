# SRS - Tài liệu đặc tả yêu cầu phần mềm

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-23  
> **Mục tiêu:** Đặc tả yêu cầu kỹ thuật để triển khai web app tương thích Network Sketcher gốc.

---

## 1. Mô tả hệ thống

Ứng dụng web gồm frontend SPA (Vue 3 + Konva) và backend FastAPI async. Dữ liệu lưu SQLite; job xuất chạy qua worker poller + ProcessPool.

## 2. Yêu cầu chức năng chi tiết

### 2.1 Quản lý dự án
- Tạo/sửa/xóa dự án.
- Gán theme/mẫu layout.

### 2.2 Nhập liệu trực tiếp & template dữ liệu
- Nhập liệu trực tiếp bằng form/bảng theo schema chuẩn.
- Thư viện template dữ liệu chuẩn (JSON) có version để áp dụng nhanh.
- Hỗ trợ dán dữ liệu dạng bảng (clipboard CSV) vào grid.
- Kiểm tra hợp lệ tại chỗ (port, IP, VLAN, trùng tên).
- Hỗ trợ validate-only (không ghi DB) để trả lỗi theo dòng/cột.
- Chuẩn hóa dữ liệu theo `docs/TEMPLATE_SCHEMA.md`.

### 2.3 Nhập dữ liệu từ Excel/CSV (tùy chọn)
- Hỗ trợ nhập Excel/CSV theo thứ tự phụ thuộc (Areas → Devices → Links → ...).
- Dùng cho chuyển đổi dữ liệu cũ hoặc đối soát.

### 2.4 Sơ đồ & đồng bộ lớp
- Sơ đồ L1/L2/L3 hiển thị và chỉnh sửa.
- Đồng bộ dữ liệu L1→L2→L3 theo quy tắc NS gốc.

### 2.5 Xuất dữ liệu
- Sinh PPTX/Excel theo bố cục NS gốc.
- Quản lý job, trạng thái, retry giới hạn.

### 2.6 Thời gian thực
- WebSocket cập nhật khi có thay đổi.

### 2.7 API nhập liệu trực tiếp (tóm tắt yêu cầu)
- Hỗ trợ `bulk` cho từng thực thể (areas/devices/links/…).
- Hỗ trợ nhập template JSON hoặc áp dụng template lưu sẵn.
- Trả lỗi theo dòng/cột với mã lỗi ổn định để UI hiển thị.
 - Chi tiết endpoint xem `docs/API_SPEC.md`.

## 3. Yêu cầu dữ liệu

- UUID v4 sinh ở tầng ứng dụng, lưu TEXT.
- JSON lưu TEXT.
- FK bắt buộc, unique constraint theo project.
- Template dữ liệu lưu dạng JSON có `schema_version` và `template_version`.
 - Chi tiết schema/validation xem `docs/TEMPLATE_SCHEMA.md`.

## 4. Yêu cầu giao diện

- UI web responsive cơ bản.
- Canvas Konva có zoom/pan, selection, drag.
- Grid nhập liệu có validate tại chỗ và báo lỗi theo dòng/cột.
- Hiển thị lỗi nhập liệu rõ ràng.
- Hệ style phải tuân theo `docs/DIAGRAM_STYLE_SPEC.md`.
- Cần hỗ trợ **Strict NS** (mặc định) và **Flexible** (giới hạn).

## 5. Ràng buộc kỹ thuật

- FastAPI async + SQLAlchemy 2.0 async.
- SQLite + aiosqlite (WAL, FK ON).
- Không Redis/Celery/Docker.
- Không CLI/CLI wrapper trong dự án web.

## 6. Thuộc tính chất lượng

- **Chính xác:** Ưu tiên số 1, so sánh output với NS gốc.
- **Tối giản:** Giảm phụ thuộc, giảm thành phần.
- **Ổn định:** Job queue an toàn, idempotent.
- **An toàn tối thiểu:** Kiểm soát upload, phân quyền theo project, log lỗi đầy đủ.
- **Phục hồi:** Có quy trình backup/restore cho DB và exports.

## 7. Giả định

- Người dùng nội bộ, ít đồng thời.
- Hạ tầng single host.

---

## 8. Tài liệu liên quan

- `PROJECT_TOPOLOGY.md`
- `WEB_APP_DEVELOPMENT_PLAN.md`
- `docs/BRD.md`
- `docs/PRD.md`
- `docs/DIAGRAM_STYLE_SPEC.md`
- `docs/API_SPEC.md`
- `docs/TEMPLATE_SCHEMA.md`
- `docs/TEST_STRATEGY.md`
- `docs/NS_REFERENCE.md`
