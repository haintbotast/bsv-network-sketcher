# SRS - Tài liệu đặc tả yêu cầu phần mềm

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-02-06  
> **Mục tiêu:** Đặc tả yêu cầu kỹ thuật để triển khai web app theo style chung (chuẩn nội bộ).

---

## 1. Mô tả hệ thống

Ứng dụng web gồm frontend SPA (Vue 3 + Konva) và backend FastAPI async. Dữ liệu lưu SQLite; job xuất chạy qua worker poller + ProcessPool.

## 2. Yêu cầu chức năng chi tiết

### 2.1 Quản lý dự án
- Tạo/sửa/xóa dự án.
- Dùng style chung (không có layout mode).
- Quản lý phiên bản topology (snapshot, xem lại, khôi phục).
- Cho phép cập nhật topology hiện có; trước khi export có thể tạo snapshot tự động.

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
- Đồng bộ dữ liệu L1→L2→L3 theo quy tắc logic chuẩn (validation chặt chẽ).
- Auto-layout theo **2 tầng** (macro Area + micro Device), ưu tiên bố cục top‑to‑bottom.
- Auto-layout tự động chạy khi **mở project** và sau mọi CRUD topology của project (area/device/link/port-link/anchor override), có debounce để giảm chạy dồn.
- Auto-layout **không được trigger** bởi thao tác viewport để xem sơ đồ (`pan`, `zoom`, `reset view`).
- Cho phép chạy lại auto-layout khi người dùng chủ động từ tab **Bố cục**.
- Nhóm điều khiển viewport/view mode (`zoom/reset view/L1/L2/L3/Sửa vị trí`) hiển thị ở **main navigator panel** để thao tác nhất quán toàn màn hình.
- Cụm điều khiển viewport/view mode ở main navigator được **canh giữa theo panel** để giảm lệch thị giác khi thao tác.
- Cho phép bật chế độ **Sửa vị trí** để kéo‑thả trực tiếp `Area/Device` trên canvas; vị trí mới được lưu vào DB tại thời điểm thả chuột.
- Luồng kéo‑thả chỉnh vị trí thủ công **không trigger auto-layout** để tránh ghi đè bố cục người dùng vừa tinh chỉnh.
- Khi kéo‑thả trong chế độ sửa vị trí, UI hiển thị **đường gióng căn chỉnh** và hỗ trợ **snap nhẹ** theo object liên quan (device cùng area hoặc area cùng cấp).
- Tọa độ `position_x/position_y` phải được chuẩn hóa theo **bảng vị trí chuẩn X/Y** với bước mặc định **0.25 đv** để tránh số lẻ khó kiểm soát.
- Tab **Bố cục** cần có thành phần khai báo nhanh kết nối peer-control (`HA/STACK/HSRP`) và hiển thị legend màu/nét/chú giải tương ứng.
- Với L1, điểm nối port tự động phải theo quy ước: **uplink ở cạnh trên (top)**, **kết nối không phải uplink ở cạnh dưới (bottom)**; chỉ cho phép lệch quy ước khi có **override thủ công**.
- Với L1, **nhãn port là một phần của object** (port band trên/dưới), không render nhãn nổi giữa đường link.
- Với L1, điểm đầu/cuối link phải **bám đúng anchor của ô port**; cơ chế tách lane chỉ được áp dụng **sau đoạn stub rời port**, không được dời trực tiếp anchor khỏi ô port.
- Kích thước object L1 phải **co giãn theo số lượng port và độ dài nhãn port** để giữ rõ ràng theo sơ đồ chuẩn PDF.
- Khoảng cách giữa thiết bị trong auto-layout **tính cả phần mở rộng theo port band** để tránh chồng lấn.
- Render L1 ưu tiên kiểu kỹ thuật: đường orthogonal/góc vuông rõ, giảm dùng màu nhấn cho link LAN/DEFAULT để hạn chế rối.
- L1 routing phải **không xuyên qua object khác** (device/area không liên quan); nếu tuyến chuẩn hóa gây va chạm thì phải fallback sang tuyến orthogonal tránh vật cản.
- Điểm rẽ đầu tiên của link phải có khoảng cách tối thiểu đủ lớn so với port band để tránh dính sát nhãn port ở sơ đồ dày.
- Với L1, khung Area hiển thị có thể ở dạng **compact theo cụm thiết bị** để giảm khoảng trắng; không thay đổi dữ liệu Area gốc.
- Các link peer-control (`STACK/HA/HSRP`) phải có quy ước hiển thị riêng (màu/nét/lane) để tách khỏi uplink/data links và dễ truy vết.
- Cho phép người dùng **override anchor per-port** bằng `side + offset_ratio` (cho phép `offset_ratio = null` để giữ auto offset); override **được lưu DB** và **không bị auto-layout ghi đè**.
- Bảng thuộc tính thiết bị cho phép **xem/chỉnh/tạo/xóa kết nối L1 theo port**, áp dụng kiểm tra **trùng link** và **port đã dùng** trước khi lưu.
- Overview (nếu bật) chỉ L1/flow; L2/L3 chỉ hiển thị ở view riêng.  
  **Lưu ý:** UI hiện không hiển thị Overview; dùng L1 thay thế.
- Liên kết khác Area bắt buộc qua **Waypoint area** (đuôi `_wp_`).
- Endpoint **không** được nối trực tiếp lên Distribution/Core (mặc định chặn ở L1).
- VPN Gateway là **chức năng Firewall** (device_type Firewall, tên có VPN).
- Area **Data Center** bao gồm Edge/Security/DMZ/Core/Distribution.
- Thiết bị Server/NAS/Storage/Server Switch bắt buộc nằm trong **Area Server** và **đặt cùng hàng hoặc ngay dưới DMZ**.
- Access Switch phải nằm trong **area nghiệp vụ** (Head Office/Department/Project/IT).
- Server chỉ được kết nối lên **Server Distribution Switch**.
 - Thiết bị Monitor/NOC/NMS được gộp vào **Area IT** (không tạo Area Monitor riêng).
- Thiết bị trong **Area HO/IT/Department/Project** (không phải Access Switch) chỉ được kết nối **duy nhất** đến **Access Switch cùng Area**.
- **Access Switch** chỉ được **uplink** lên **Distribution Switch**; các kết nối xuống chỉ được phép tới thiết bị **cùng Area**.
- **Server Switch** chỉ được kết nối tới **Server/Storage** và **Distribution Switch**.

### 2.5 Xuất dữ liệu
- Sinh PPTX/Excel theo style chung.
- Quản lý job, trạng thái, retry giới hạn.
- Gắn export với phiên bản topology (version_id).
- Preview/export hiển thị metadata phiên bản (label, time, user).

### 2.6 Thời gian thực
- WebSocket cập nhật khi có thay đổi.

### 2.7 API nhập liệu trực tiếp (tóm tắt yêu cầu)
- Hỗ trợ `bulk` cho từng thực thể (areas/devices/links/…).
- Hỗ trợ nhập template JSON hoặc áp dụng template lưu sẵn.
- Trả lỗi theo dòng/cột với mã lỗi ổn định để UI hiển thị.
- Chi tiết endpoint xem `docs/API_SPEC.md`.

### 2.8 Cấu hình hệ thống (admin)
- Preset layout/style/validation có thể cấu hình qua trang quản trị.
- Không hardcode danh sách preset trong UI/Backend.
- Schema cấu hình xem `docs/ADMIN_CONFIG_SCHEMA.md`.

## 3. Yêu cầu dữ liệu

- UUID v4 sinh ở tầng ứng dụng, lưu TEXT.
- JSON lưu TEXT.
- FK bắt buộc, unique constraint theo project.
- Template dữ liệu lưu dạng JSON có `schema_version` và `template_version`.
- Chi tiết schema/validation xem `docs/TEMPLATE_SCHEMA.md`.

### 3.1 Phiên bản topology (gợi ý tối thiểu)
- `project_versions`: snapshot JSON của topology, `version`, `created_by`, `created_at`.
- `export_jobs`: tham chiếu `version_id` để truy vết output.

**Schema gợi ý (SQLite):**
```sql
CREATE TABLE project_versions (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  version_number INTEGER NOT NULL,
  label TEXT,
  note TEXT,
  snapshot_json TEXT NOT NULL,
  created_by TEXT REFERENCES users(id),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  is_current INTEGER DEFAULT 0,
  UNIQUE(project_id, version_number)
);
```

### 3.2 Phiên bản cấu hình hệ thống (gợi ý tối thiểu)
- `config_versions`: snapshot JSON cấu hình admin, có lịch sử và restore.

**Schema gợi ý (SQLite):**
```sql
CREATE TABLE config_versions (
  id TEXT PRIMARY KEY,
  config_key TEXT NOT NULL DEFAULT 'global',
  version_number INTEGER NOT NULL,
  label TEXT,
  note TEXT,
  config_json TEXT NOT NULL,
  created_by TEXT REFERENCES users(id),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  is_current INTEGER DEFAULT 0,
  UNIQUE(config_key, version_number)
);
```

## 4. Yêu cầu giao diện

- UI web responsive cơ bản.
- Canvas Konva có zoom/pan, selection, drag.
- Drag trong canvas phải tách rõ hai ngữ cảnh: drag viewport (`pan`) và drag object (chỉnh vị trí thủ công).
- Grid nhập liệu có validate tại chỗ và báo lỗi theo dòng/cột.
- Hiển thị lỗi nhập liệu rõ ràng.
- Hệ style phải tuân theo `docs/DIAGRAM_STYLE_SPEC.md`.
- Chỉ một style chung và preset/flexible theo spec.

## 5. Ràng buộc kỹ thuật

- FastAPI async + SQLAlchemy 2.0 async.
- SQLite + aiosqlite (WAL, FK ON).
- Không Redis/Celery/Docker.
- Không CLI/CLI wrapper trong dự án web.

## 6. Thuộc tính chất lượng

- **Chính xác:** Ưu tiên số 1, so sánh output theo style chung (golden files hoặc rule-based).
- **Tối giản:** Giảm phụ thuộc, giảm thành phần.
- **Ổn định:** Job queue an toàn, idempotent.
- **An toàn tối thiểu:** Kiểm soát upload, phân quyền theo project, log lỗi đầy đủ.
- **Phục hồi:** Có quy trình backup/restore cho DB và exports.
- **Truy vết:** Audit log cho thay đổi topology và cấu hình.

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
- `docs/ADMIN_CONFIG_SCHEMA.md`
- `docs/ADMIN_UI_FLOW.md`
