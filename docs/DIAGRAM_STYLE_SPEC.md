# Đặc tả Style sơ đồ (Diagram Style Spec)

> **Phiên bản:** 1.1  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-02-10  
> **Mục tiêu:** Chuẩn hóa hình khối, nét vẽ, màu sắc, chữ và nền cho toàn hệ thống (UI + Konva + export).

---

## 1. Phạm vi

- Áp dụng cho **UI/Konva** và **xuất PPTX**.
- Không áp dụng cho Excel (chỉ dữ liệu).
- Ưu tiên **chuẩn layout network phổ biến**; NS gốc chỉ là tham chiếu.

---

## 2. Style chung & preset

### 2.1 Style chung (bắt buộc)
- **Chỉ một style chung**, không có lựa chọn layout mode theo project.
- Bố cục phân tầng **top‑to‑bottom** là mặc định; liên kết ưu tiên **ngang/dọc** để dễ đọc.

### 2.2 Preset (mặc định)
- Dùng preset màu/nét/chữ/shape theo **style chung**.
- Không cho phép tùy biến tự do ngoài bộ preset.

### 2.3 Flexible (tùy chọn)
- Cho phép chọn trong **tập lựa chọn giới hạn** (shape, màu, nét).
- Phải map được sang PPTX không làm vỡ layout.
- Cần cảnh báo khi xuất nếu có override không tương thích.

### 2.4 Quy tắc bố cục theo style chung (tối thiểu)

- **Phân tầng:** Core/Distribution ở trên, Access ở giữa, Endpoints ở dưới.
- **Hướng ưu tiên:** top‑to‑bottom; liên kết ưu tiên ngang/dọc, tránh chéo không cần thiết.

### 2.5 Bố cục phân tầng 2 tầng (Area/Device) theo AI Context

**Nguyên tắc chung (bắt buộc):**
- **Macro (Area):** sắp xếp các Area theo location/tầng; không để thiết bị xuyên Area.
- **Micro (Device):** mỗi Area là một lưới **top‑to‑bottom** theo thứ tự: **Router/Firewall → Core Switch → Distribution/Access Switch → Server Switch → Server/Storage → Endpoints**.
- **Micro row alignment:** khi một layer phải xuống nhiều hàng, các hàng phải được **căn giữa theo chiều ngang** trong chính layer đó (không dồn trái cứng).
- **Hiển thị Area (L1):** UI có thể render Area theo khung **compact theo cụm thiết bị** để giảm khoảng trắng; không thay đổi tọa độ/kích thước Area gốc trong dữ liệu.
- Cho phép **nhiều hàng trong cùng tầng** và **so‑le nhẹ** để giảm đường vòng liên kết; vẫn giữ hướng top‑down.
- Ưu tiên **thiết bị cùng loại ở cùng một hàng** nếu kích thước hàng cho phép (ví dụ cụm HA/Sync).
- Ưu tiên **gom nhóm thiết bị có cùng prefix tên** (ví dụ `HN-SW-CORE-xx`, `HN-SW-DIST-xx`) để các thiết bị liên quan đứng gần nhau.
- Dùng `_AIR_` (ô trống) để canh cột, giữ thẳng hàng theo chiều dọc khi cần.

**Quy tắc hiển thị theo view:**
- **Overview (nếu bật):** chỉ L1/flow; không render nhãn L2/L3 để tránh đè chữ/đường.  
  **Lưu ý:** UI hiện không hiển thị Overview; dùng L1 thay thế.
- **L2/L3:** chỉ hiển thị nhãn L2/L3 trong view tương ứng; có **band nhãn** để không chồng lên thiết bị.
- **Khi pan/drag:** UI có thể **tạm ẩn nhãn port/L2/L3** để tối ưu hiệu năng; nhãn hiển thị lại khi dừng kéo.
- **Khi zoom:** UI ưu tiên **scale nhanh** và **không tái tính toán** trong lúc zoom; chỉ tính lại khi dữ liệu/layout đổi.
- Cụm điều khiển viewport/view mode (`zoom/reset/L1/L2/L3/Sửa vị trí`) đặt ở **main navigator panel** và hiển thị **canh giữa theo panel** để ổn định trọng tâm thao tác.
- Trigger auto-layout chỉ đến từ **mở project** và CRUD dữ liệu topology; thao tác viewport (`pan/zoom/reset view`) chỉ đổi góc nhìn và **không được phép** kích auto-layout.
- **Kéo‑thả object thủ công:** chỉ có hiệu lực khi bật chế độ **Sửa vị trí**; áp dụng cho `Area/Device`, lưu `position_x/position_y` tại `drag-end`, và không kích hoạt auto-layout từ chính thao tác kéo‑thả này.
- **Align guide khi drag:** trong chế độ sửa vị trí, UI hiển thị đường gióng ngang/dọc và snap nhẹ theo object liên quan (device cùng area hoặc area cùng cấp) để chỉnh tay chính xác.
- **Mốc tọa độ chuẩn:** X/Y thủ công dùng step mặc định **0.25 đv**; drag và nhập tay đều chuẩn hóa về mốc này để tránh số lẻ rời rạc.
- Tab **Bố cục** có khối khai báo nhanh link peer-control (`STACK/HA/HSRP`), cho phép chọn nhanh 2 thiết bị + port và áp style theo purpose.
- Legend peer-control bắt buộc hiển thị cùng panel khai báo:  
  - `STACK`: xanh dương, nét liền.  
  - `HA`: xanh lá ngọc, nét đứt.  
  - `HSRP`: tím, nét chấm.

**Liên kết liên‑area:**
- Bắt buộc đi qua **Waypoint area** (đuôi `_wp_`), không nối Area‑Area trực tiếp.
- Link đi qua **anchor trong vùng đệm (pad)** của Area; hành lang liên‑area ưu tiên tuyến Manhattan (ngang/dọc) đơn giản.
- Liên‑area đi trong **khoảng trống giữa Area** khi cần, **không dùng corridor global ngoài biên Area**.
- Mỗi cặp Area dùng hành lang orthogonal đơn giản, chỉ thêm **lane offset nhẹ** theo bundle index để giảm chồng.
- **Không cho phép tuyến liên‑area/waypoint đi ra ngoài đường bao sơ đồ**; nếu thiếu chỗ thì tăng `area_padding` hoặc nới layout.
- **Liên‑area qua waypoint:**  
  - **L1/L2/L3:** giữ **Manhattan (ngang/dọc)**, ưu tiên góc vuông rõ ràng; không dùng shortcut chéo.
- Routing link ưu tiên **tránh vật cản** (area/device/**port cell**) và dùng pipeline **single-pass**:
  - Dựng stub từ anchor port.
  - Nối orthogonal bằng thuật toán tuyến tính.
  - Nếu bị cản thì fallback orthogonal đơn giản (không dùng tối ưu toàn cục/A\*).
- Sau bước chuẩn hóa orthogonal, nếu tuyến cắt qua object thì fallback tuyến orthogonal thay thế để bảo toàn tính hợp lệ.
- **Pair alignment:** với nhiều link giữa 2 thiết bị kề nhau, anchor được **xếp đồng bộ theo thứ tự port phía đối diện** để giảm chéo.
- **Same-row alignment:** link giữa **2 thiết bị cùng hàng/cùng cột** sẽ ưu tiên **canh thẳng anchor + ô port** (ngang hoặc dọc). Chỉ áp dụng khi **đường thẳng không bị vật cản**; nếu bị cản thì giữ routing tránh vật cản.
- **Stub theo port band (L1):** đoạn link đi ra khỏi thiết bị phải đủ dài để tách rõ khỏi biên object/ô port và tránh gãy góc ngay sát mép thiết bị.
- **Port turn clearance (L1):** điểm rẽ đầu tiên phải có khoảng cách đủ xa port band (khuyến nghị >= 28px ở scale 1x; có thể tăng theo mật độ bundle).
- **Thứ tự thiết bị (L1 micro):** **Router ở hàng trên**, Firewall **ở hàng dưới Router**, Core/Distro nằm dưới Firewall.
- **Nhãn port (L1):** nhãn là **thành phần của object** (ô port trong dải top/bottom), không hiển thị dạng nhãn nổi trên link.
- **Quy ước side tự động (L1):** mặc định chỉ dùng **top/bottom** cho anchor port:
  - **uplink => top**
  - **non-uplink => bottom**
  - **left/right** chỉ dùng khi có **override thủ công**.
- **Port side stability (L1):** side tự động chỉ theo policy `top/bottom`; không tự ép sang `left/right` trong auto pass để tránh lệch giữa anchor và port band.
- **Exit bundle (L1):** nhóm link theo **(device, exit side)** và **tách đều offset** để giảm chồng khi nhiều link đi cùng hướng; offset tối thiểu bằng **max(`bundle_gap`, `grid cell`)** và **tự nhân hệ số theo `total`** (nhiều link → khoảng cách lớn hơn). **Lane shift** được áp **sau đoạn stub rời port**, không dịch trực tiếp endpoint khỏi anchor của ô port.
- **Stub fan theo rank active (L1):** fan-out đoạn stub được tính theo **thứ tự endpoint active** trên cùng `(device, side)` với spread chuẩn `0..20px * scale`, tránh phụ thuộc trực tiếp vào kích thước object.
- **Short same-side fan sync (L1):** với link nội‑area ngắn và hai đầu cùng side, fan hai đầu được đồng bộ để tránh tạo “hộp nhỏ” sát port band.
- **Direct intra ưu tiên theo hình học (L1):** với cặp thiết bị nội‑area theo phương ngang, hai đầu cùng side (`top/top` hoặc `bottom/bottom`) và không bị vật cản, router phải ưu tiên tuyến trực tiếp/orthogonal ngắn trước khi áp lane U cho purpose đặc biệt.
- **Cặp dọc top-bottom (L1):** khi hai thiết bị xếp dọc (một trên, một dưới), không ép dùng rule direct ngang; giữ routing theo hành lang dọc/orthogonal để tránh tuyến khó đọc.
- **Endpoint anchoring (L1):** điểm đầu/cuối link phải trùng side + tọa độ anchor của ô port (sai số render cho phép <= 1px).
- **Bundle song song (L1):** nếu 2 thiết bị **cùng hàng/cột**, không bị vật cản thì ưu tiên **đường thẳng song song** cho các link bundle (bỏ A\*), để tránh “uốn cong” ngay tại port label.
- **Peer control links (L1):** `STACK/HA/HSRP` ưu tiên tuyến nội‑area ngắn, tách lane riêng theo loại link để không hòa vào bó uplink/data.
- **Waypoint (L1):** khi có waypoint giữa 2 Area, link đi qua **nhiều tọa độ neo** trên waypoint (theo lane index) để **không chồng lên nhau**.
- **Override thủ công (per-port):** người dùng có thể **cố định side + offset_ratio** cho từng port; `offset_ratio` có thể để `null` để **giữ auto offset** theo side đã chọn. Override **giữ side là ưu tiên cao nhất**, nhưng **có thể tự căn lại tọa độ** để **giữ link thẳng hàng** khi 2 thiết bị cùng hàng/cột và side đã phù hợp.
- **Xác định uplink (L1):** ưu tiên theo quan hệ phân tầng thiết bị (tier thấp nối lên tier cao); nếu không phân biệt được thì fallback theo heuristic `port index = 1`.
- Liên‑area **tách lane rộng hơn** so với bundle nội‑area để giảm chồng/đè.
- Intra‑area: nếu đường thẳng cắt thiết bị khác thì bẻ góc (Manhattan) để tránh xuyên qua device.

**Macro layout (Area):**
- Kích thước Area được **tính lại từ bounding thiết bị** + padding + band nhãn khi auto‑layout toàn dự án (cho phép **co lại** nếu dư thừa).
- Khi project có **placement map rõ ràng** (`grid_row/grid_col` tạo thành lưới nhiều hàng và nhiều cột), macro layout **ưu tiên bám theo lưới này** để giữ bố cục gần template/PDF chuẩn; vẫn giữ quy tắc top‑to‑bottom.
- Với placement map rõ ràng, mỗi cột dùng cơ chế **center-slot** (độ rộng cột đại diện theo trung vị), Area trong cột được căn giữa theo trục cột để giảm méo bố cục khi có area outlier quá rộng.
- Trong cùng tier, **được phép hoán vị theo kết nối** (barycenter + local swap) để giảm đường vòng liên‑area, nhưng **không đổi thứ tự tier theo trục dọc**.
- Barycenter có thể chạy **nhiều vòng** để ưu tiên rút ngắn liên‑area khi số lượng Area lớn.
- Sắp xếp Area theo **11 tiers** (0-10):
  - **Tier 0: Edge/WAN** (ISP, Internet, Edge routers)
  - **Tier 1: Security** (Firewalls, IDS/IPS, VPN)
  - **Tier 2: DMZ** (DMZ servers, proxy)
  - **Tier 3: Core** (Core switches, core routers)
  - **Tier 4: Distribution** (Distribution switches)
  - **Tier 5: Campus** (Campus-wide access, HQ, main sites)
  - **Tier 6: Branch** (Branch sites, remote offices)
  - **Tier 7: Office** (Office floors, building access) - **mặc định**
  - **Tier 8: Department** (Department-specific networks)
  - **Tier 9: Project** (Project-specific networks)
  - **Tier 10: Servers/Storage** (servers, storage)
  - **Quy tắc ưu tiên:** Tier 10 **không được đứng trước** Tier 0/1; nếu thiếu Tier 1/2 thì **xếp Tier 10 sau Tier 0**.
- Mỗi tier có **width factor** riêng:
  - Tier 0-4 (Infrastructure): rộng hơn (1.3-1.5x), tối đa 2 areas/hàng
  - Tier 5-6 (Campus/Branch): vừa phải (1.1-1.2x), tối đa 3 areas/hàng
  - Tier 7-9 (Office/Dept/Project): hẹp hơn (1.0x), tối đa 4 areas/hàng
  - Tier 10 (Servers): vừa phải (1.2x), tối đa 3 areas/hàng
- Mỗi tier **tự xuống dòng (wrap)** theo hàng dựa trên max width của tier đó.
- Khoảng cách giữa Area: 0.8 inch (AREA_GAP).

**Quy ước bổ sung (bắt buộc):**
- **VPN Gateway là chức năng của Firewall** → thể hiện bằng `device_type=Firewall` và tên có `VPN` (màu firewall), **không tạo device_type riêng**.
- **Area Data Center** bao gồm **Edge/Security/DMZ/Core/Distribution** (không tách rời thành các area con nếu không cần).
- **Area Server** ưu tiên đặt **cùng hàng hoặc ngay dưới DMZ** (không rơi sâu xuống các tầng Office/Department/Project).
- Thiết bị **Server/NAS/Storage/Server Switch** không được nằm trong area Project/Office/IT; phải gom về **Area Server**.
- Thiết bị **Monitor/NOC/NMS** được gộp vào **Area IT** (không tạo Area Monitor riêng).
- **Access Switch** phải nằm **trong area nghiệp vụ** (Head Office/Department/Project/IT), **không tạo area Access riêng**.
- **Server Switch** nằm dưới lớp Distribution/Access, đóng vai trò Distribution trong lớp Server; server chỉ kết nối lên **Server Switch**.

---

## 3. Design Tokens (nguồn chuẩn)

**Nguồn chuẩn:** `frontend/src/styles/diagram-tokens.ts`  
**CSS map (tùy chọn):** `frontend/src/styles/diagram-tokens.css`

**Nguyên tắc:**
- Token là **nguồn duy nhất** cho màu/nét/chữ.
- Konva **không đọc CSS variables**, phải map từ tokens.
- PPTX dùng cùng token để đảm bảo thống nhất.
- Preset có thể cấu hình qua trang quản trị; không hardcode trong UI/Backend.

---

## 4. Quy ước hình khối theo đối tượng

| Đối tượng | Shape | Ghi chú |
|----------|-------|--------|
| Area | Rectangle bo góc nhẹ | Nền trong suốt, label góc trên trái, **viền mảnh rõ**, không đổ bóng |
| Device | Rectangle (ưu tiên góc vuông khi có port band) | Màu theo loại thiết bị, có viền rõ để tách thân thiết bị và dải port |
| Waypoint | Diamond hoặc Circle | Không hiện label khi zoom out |
| Link | Line | **L1 ưu tiên Manhattan (ngang/dọc)** theo tuyến tối ưu tránh vật cản, **không shortcut chéo**, **lineJoin miter/lineCap butt** để rõ nét kỹ thuật; **LAN/DEFAULT ở L1 dùng màu trung tính** để giảm rối. **L2/L3 ưu tiên any‑angle (Theta\*) + bo góc nhẹ**; màu theo purpose; nét liền/đứt |
| Port Cell (L1) | Rect + Text (gắn vào object) | Hiển thị tên port trực tiếp trên dải top/bottom của object; ưu tiên rõ ràng và ổn định theo số lượng port |

- Auto-layout cần **tính thêm vùng đệm port band** khi giãn khoảng cách giữa thiết bị để tránh chồng lấn.
- Auto-layout cần **tính thêm băng nhãn** khi xác định kích thước node và khoảng cách:
  - **L1:** cộng `port_label_band` vào kích thước node (rộng/cao) và vào `node_spacing`/`layer_gap`.
  - **L1 (thực tế):** ước lượng **bề ngang dải port (port band)** theo số lượng/độ dài port để tăng `node_spacing`/`row_gap` (tránh object chèn lên nhau).
  - **L2/L3:** cộng `label_band` vào chiều cao node để chừa chỗ nhãn L2/L3 dưới thiết bị; đồng thời chừa band nhãn cho group (VLAN/Subnet).
- **Kích thước thiết bị (Device):** tự động **nới rộng theo số lượng/độ dài port** và giữ vùng thân thiết bị đủ chỗ cho tên thiết bị.
- Micro layout sử dụng **kích thước thiết bị sau auto-resize** để tính bounding và sắp xếp trước khi tính macro layout.
- **Quy tắc nhãn port:** định dạng **chữ cái + khoảng trắng + số hiệu**.  
  Ví dụ: `Gi 0/1`, `Gi 1/0/48`, `HA 1`, `Port 1`.

### 4.1 Kích thước chuẩn (tham chiếu)

| Đối tượng | Kích thước chuẩn | Ghi chú |
|----------|------------------|--------|
| Area | Tối thiểu 3.0 x 1.5 | Tự co giãn theo nội dung |
| Device | 1.2 x 0.5 | Theo preset layout |
| Waypoint | 0.25 x 0.25 | Kích thước cố định |
| Port Cell (L1) | Auto-fit theo text | Nằm trong dải port top/bottom của object |

---

## 5. Nét vẽ & kiểu đường (line)

- **Primary:** nét liền, strokeWidth chuẩn.
- **Backup/MGMT:** nét đứt theo preset.
- **Arrow:** chỉ dùng khi cần hướng; mặc định tắt.

### 5.1 Preset nét vẽ (theo style chung)

| Đối tượng | Stroke | StrokeWidth | Dash |
|----------|--------|-------------|------|
| Area | #333333 | 1 | None |
| Device | #333333 | 1 | None |
| Link Primary | Theo purpose | 1.5 | None |
| Link Backup | Theo purpose | 1.5 | 4,2 |
| Link MGMT | Theo purpose | 1.5 | 6,3 |
| Port Cell (L1) | #2b2a28 | 1 | None |

### 5.2 Line Jump/Arc tại giao điểm

Khi hai đường link cắt nhau, đường link có **index render cao hơn** sẽ hiển thị **semicircle arc (jump)** tại điểm giao để phân biệt với kết nối thực.

| Thuộc tính | Giá trị |
|------------|---------|
| Arc radius | 5 px |
| Hướng nhảy (đoạn ngang) | Lên trên (negative Y) |
| Hướng nhảy (đoạn dọc) | Sang phải (positive X) |
| Convention | Link index cao nhảy qua link index thấp |
| Áp dụng | Tất cả links: inter-area, intra-area, bundled |
| Epsilon loại trừ | 1px từ endpoint segment |
| Khoảng cách tối thiểu giữa 2 arc | 2.5 × radius |

Kỹ thuật: Dùng `v-shape` Konva với custom `sceneFunc` (`context.arc()`), thay thế `v-line`.

---

## 6. Màu sắc

### 6.1 Màu thiết bị
- Dùng bảng mapping theo prefix tên (tham chiếu NS).
- Không cho phép nhập màu tự do trong chế độ preset.

### 6.2 Màu link theo purpose
- Dùng bảng mapping (WAN/DMZ/LAN/MGMT/HA/STORAGE/BACKUP/VPN).

### 6.3 Bảng preset màu (theo style chung)

**Thiết bị (theo prefix tên):**

| Prefix | Màu (RGB) | Ghi chú |
|--------|-----------|---------|
| Router / ISP | 70,130,180 | Steel Blue |
| FW / Firewall | 220,80,80 | Red |
| VPN / VPN-Gateway | 220,80,80 | Dùng màu Firewall (VPN là chức năng Firewall) |
| Core-SW / Core | 34,139,34 | Green |
| Dist | 60,179,113 | Green |
| Access-SW / Access | 0,139,139 | Cyan |
| Server / App / Web / DB | 106,90,205 / 138,43,226 / 75,0,130 / 148,0,211 | Server group |
| NAS / SAN / Storage / Backup | 210,105,30 / 184,134,11 / 205,133,63 / 139,90,43 | Storage |
| _DEFAULT_ | 128,128,128 | Gray |

**Link (theo purpose):**

| Purpose | Màu (RGB) | Màu (HEX) |
|---------|-----------|-----------|
| DEFAULT | 43,42,40 | #2b2a28 |
| INTERNET | 231,76,60 | #e74c3c |
| WAN | 230,126,34 | #e67e22 |
| DMZ | 241,196,15 | #f1c40f |
| LAN | 39,174,96 | #27ae60 |
| MGMT | 41,128,185 | #2980b9 |
| HA | 22,160,133 | #16a085 |
| HSRP | 155,89,182 | #9b59b6 |
| STACK / STACKWISE | 45,140,240 | #2d8cf0 |
| STORAGE | 26,188,156 | #1abc9c |
| BACKUP | 127,140,141 | #7f8c8d |
| VPN | 155,89,182 | #9b59b6 |
| UPLINK / INTER‑AREA | 230,126,34 | #e67e22 |
| WAN / INTERNET | 0,112,192 |
| DMZ | 237,125,49 |
| LAN | 112,173,71 |
| MGMT | 112,48,160 |
| STORAGE | 165,105,63 |
| BACKUP | 127,127,127 |
| HA | 96,96,96 |
| VPN | 192,0,0 |
| DEFAULT | 0,0,0 |

---

## 7. Chữ & nền

- Font mặc định: `Calibri`.
- Size chữ: theo token (area/device/link).
- Màu chữ: đen/xám đậm để đảm bảo tương phản.
- Nền area: màu nhạt trung tính.

### 7.1 Preset chữ (theo style chung)

| Đối tượng | Font | Size | Màu chữ |
|----------|------|------|--------|
| Area Label | Calibri | 14 | #333333 |
| Device Label | Calibri | 10 | #000000 |
| Link Label | Calibri | 9 | #000000 |
| Port Cell (L1) | Calibri | 9 | #000000 |

### 7.2 Preset nền (theo style chung)

| Đối tượng | Nền |
|----------|-----|
| Area | Transparent |
| Port Cell (L1) | #FFFFFF |
| Canvas | #FFFFFF |

---

## 7.3 Quy ước đơn vị & làm tròn

- **Đơn vị chuẩn:** inch cho toàn bộ kích thước/tọa độ logic.
- **Lưu DB:** số thực (REAL) theo inch, làm tròn **2 chữ số thập phân**.
- **Render UI:** nhân với `SCALE` để ra pixel; không làm tròn sớm.
- **Export PPTX:** giữ inch, làm tròn **2 chữ số** cho kích thước, **3 chữ số** cho tọa độ để tránh lệch.
- **Text size:** số nguyên theo preset, không làm tròn.

---

## 8. Mapping UI → Konva → PPTX

- **UI/Konva:** map trực tiếp từ tokens sang `fill`, `stroke`, `strokeWidth`, `fontSize`, `fontFamily`.
- **PPTX:** map màu/nét/chữ tương ứng; không dùng giá trị ngoài preset.
- **Preset:** bắt buộc mapping đúng preset, không override tự do.
- **Flexible:** chỉ cho phép override trong danh sách cho phép; log cảnh báo nếu không export được.

---

## 9. Ràng buộc tương thích

- Nếu dùng **golden files**, chỉ được thay đổi preset khi đã cập nhật golden files tương ứng.
- Nếu dùng **rule-based**, phải cập nhật `docs/RULE_BASED_CHECKS.md` và chạy lại regression.
- Mọi thay đổi token phải cập nhật kiểm thử snapshot PPTX.
- Nếu thay đổi shape/line, phải cập nhật mapping export.

---

## 10. Quy tắc cập nhật

- Mọi thay đổi style phải cập nhật tài liệu này.
- Đồng bộ với `WEB_APP_DEVELOPMENT_PLAN.md`, `docs/PRD.md`, `docs/SRS.md`.

---

## 11. Bảng mapping chi tiết (UI/Konva ↔ PPTX)

| Đối tượng | Konva Props | PPTX Shape | PPTX Style |
|----------|-------------|-----------|------------|
| Area | Rect: `fill`, `stroke`, `strokeWidth`, `cornerRadius` | Rectangle (rounded) | Fill solid, line solid |
| Area Label | Text: `fontFamily`, `fontSize`, `fill` | TextBox | Font + size + color |
| Device | Rect: `fill`, `stroke`, `strokeWidth`, `cornerRadius` | Rectangle | Fill solid, line solid |
| Device Label | Text: `fontFamily`, `fontSize`, `fill` | TextBox | Font + size + color |
| Waypoint | Rect/Circle | Diamond/Ellipse | Fill solid, line solid |
| Link | Line: `stroke`, `strokeWidth`, `dash` | Line | Line color + width + dash |
| Link Label | Text: `fontFamily`, `fontSize`, `fill` | TextBox | Font + size + color |
| Port Cell (L1) | Rect + Text | Rectangle + TextBox | Fill solid + line |

**Lưu ý:**
- Không dùng gradient trong chế độ preset.
- Mọi color map từ preset RGB → PPTX RGB.

---

## 12. Quy tắc zoom/LOD (giảm rối khi sơ đồ lớn)

| Ngưỡng zoom | Hiển thị |
|------------|----------|
| ≥ 1.0 | Hiển thị đầy đủ label + port cell |
| 0.7 – 0.99 | Rút gọn hiển thị port cell, giữ device label |
| 0.4 – 0.69 | Ẩn device label, giữ area label |
| < 0.4 | Ẩn tất cả label, chỉ giữ shape + link |

**Nguyên tắc:** LOD chỉ áp dụng UI; export luôn dùng full detail.

---

## 13. Danh sách override hợp lệ (Flexible)

**Chỉ cho phép:**
- Đổi preset theme (default/contrast/dark/light).
- Đổi dash style trong danh sách: `primary`, `backup`, `mgmt`.
- Đổi shape trong danh sách: `rect`, `rounded-rect`, `diamond`, `circle`.
- Đổi màu trong **bảng preset** đã định nghĩa.

**Không cho phép:**
- Màu tùy ý ngoài preset.
- Gradient/opacity tự do (trừ port cell theo preset).
- Thay đổi font family ngoài `Calibri` khi xuất PPTX.

---

## 14. Kiểm tra rule-based (tham chiếu)

- Bộ quy tắc kiểm tra tối thiểu (không chồng lấn, khoảng cách tối thiểu, nhãn không đè, số lượng node/link, logic L1→L2→L3) được chuẩn hóa tại `docs/RULE_BASED_CHECKS.md`.
- Style chung có thể override các tham số khoảng cách theo preset hoặc cấu hình admin.

---

## 15. Cập nhật style grid/port (2026-02-09)

- Tọa độ chuẩn của Area/Device được mô tả bằng `grid_range` kiểu Excel (`A1:B2`), backend tự đồng bộ với tọa độ inch logic.
- `Port label` là một phần của object: danh sách port hiển thị lấy từ dữ liệu `device_ports` (không chỉ suy diễn từ link).
- Quy tắc side của port:
  - `top`: ưu tiên uplink/peer-control.
  - `bottom`: ưu tiên downlink.
  - `left/right`: chỉ dùng khi cần bám hình học đặc thù hoặc người dùng override.
- Khi render L1, nếu có xung đột giữa khai báo port và anchor override thủ công: **anchor override** có ưu tiên cao hơn.
