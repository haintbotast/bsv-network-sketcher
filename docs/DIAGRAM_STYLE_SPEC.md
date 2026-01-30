# Đặc tả Style sơ đồ (Diagram Style Spec)

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-30  
> **Mục tiêu:** Chuẩn hóa hình khối, nét vẽ, màu sắc, chữ và nền cho toàn hệ thống (UI + Konva + export).

---

## 1. Phạm vi

- Áp dụng cho **UI/Konva** và **xuất PPTX**.
- Không áp dụng cho Excel (chỉ dữ liệu).
- Ưu tiên **chuẩn layout network phổ biến**; NS gốc chỉ là tham chiếu.

---

## 2. Chế độ layout & style

### 2.1 Layout mode (bắt buộc chọn)
- `cisco`: bố cục core–distribution–access, trái → phải.
- `iso`: bố cục phân tầng trung tính (top → down hoặc left → right).
- `custom`: cho phép định nghĩa quy tắc bố cục riêng (có kiểm soát).

### 2.2 Preset (mặc định)
- Dùng preset màu/nét/chữ/shape theo layout mode đã chọn.
- Không cho phép tùy biến tự do ngoài bộ preset.

### 2.3 Flexible (tùy chọn)
- Cho phép chọn trong **tập lựa chọn giới hạn** (shape, màu, nét).
- Phải map được sang PPTX không làm vỡ layout.
- Cần cảnh báo khi xuất nếu có override không tương thích.

### 2.4 Quy tắc bố cục theo mode (tối thiểu)

- **Cisco-style:** core → distribution → access theo trục ngang (left → right); link ưu tiên ngang.
- **ISO/IEC generic:** phân tầng top → down (hoặc left → right), trung tính về màu/nhãn.
- **Custom:** phải khai báo hướng bố cục, khoảng cách tối thiểu, và quy tắc nhóm; nếu thiếu thì fallback về ISO.

### 2.5 Bố cục phân tầng 2 tầng (Area/Device) theo AI Context

**Nguyên tắc chung (bắt buộc):**
- **Macro (Area):** sắp xếp các Area theo location/tầng; không để thiết bị xuyên Area.
- **Micro (Device):** mỗi Area là một lưới **top‑to‑bottom** (Core/Distribution ở trên, Access ở giữa, Endpoints ở dưới).
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

**Liên kết liên‑area:**
- Bắt buộc đi qua **Waypoint area** (đuôi `_wp_`), không nối Area‑Area trực tiếp.
- Link đi qua **anchor** trên biên Area để giảm cắt xuyên.
- Ưu tiên tuyến **corridor** (ngoài biên Area) cho liên‑area để tránh đi xuyên vùng thiết bị.
- Routing link ưu tiên **tránh vật cản** (area/device/**interface tag**) và **giảm chồng lấn**; nếu không bị cản thì giữ đường thẳng ngắn nhất.
- Liên‑area **tách lane rộng hơn** so với bundle nội‑area để giảm chồng/đè.

**Macro layout (Area):**
- Kích thước Area được **tính lại từ bounding thiết bị** + padding + band nhãn khi auto‑layout toàn dự án (cho phép **co lại** nếu dư thừa).
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
- **Server Switch** được xem là **Distribution Switch** trong lớp Server; server chỉ kết nối lên **Server Distribution Switch**.

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
| Area | Rectangle bo góc | Nền nhạt xám nhẹ, label góc trên trái, **không viền**, có **đổ bóng nhẹ** |
| Device | Rectangle bo góc | Màu theo loại thiết bị, **không viền**, có **đổ bóng nhẹ** |
| Waypoint | Diamond hoặc Circle | Không hiện label khi zoom out |
| Link | Line | L1 ưu tiên **đường thẳng ngắn nhất** giữa port; nếu bị cản thì dùng Manhattan tránh vật cản; L2/L3 dùng Manhattan; màu theo purpose; nét liền/đứt; **bo góc mềm** (lineJoin/lineCap round) |
| Interface Tag | Text + background | Hiển thị tên port ở L1, neo theo **port anchor**, có thể xoay theo hướng link; auto-scale theo zoom (0.6-1.15) và tự giãn để tránh chồng lấn |

- Auto-layout cần **tính thêm vùng đệm Interface Tag** khi giãn khoảng cách giữa thiết bị để tránh chồng lấn.
- **Quy tắc nhãn port:** định dạng **chữ cái + khoảng trắng + số hiệu**.  
  Ví dụ: `Gi 0/1`, `Gi 1/0/48`, `HA 1`, `Port 1`.

### 4.1 Kích thước chuẩn (tham chiếu)

| Đối tượng | Kích thước chuẩn | Ghi chú |
|----------|------------------|--------|
| Area | Tối thiểu 3.0 x 1.5 | Tự co giãn theo nội dung |
| Device | 1.2 x 0.5 | Theo preset layout |
| Waypoint | 0.25 x 0.25 | Kích thước cố định |
| Interface Tag | 0.6 x 0.2 | Auto-fit theo text |

---

## 5. Nét vẽ & kiểu đường (line)

- **Primary:** nét liền, strokeWidth chuẩn.
- **Backup/MGMT:** nét đứt theo preset.
- **Arrow:** chỉ dùng khi cần hướng; mặc định tắt.

### 5.1 Preset nét vẽ (theo layout mode)

| Đối tượng | Stroke | StrokeWidth | Dash |
|----------|--------|-------------|------|
| Area | #333333 | 1 | None |
| Device | #333333 | 1 | None |
| Link Primary | Theo purpose | 1.5 | None |
| Link Backup | Theo purpose | 1.5 | 4,2 |
| Link MGMT | Theo purpose | 1.5 | 6,3 |
| Interface Tag | #333333 | 0.5 | None |

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

### 6.3 Bảng preset màu (theo layout mode)

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

| Purpose | Màu (RGB) |
|---------|-----------|
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

### 7.1 Preset chữ (theo layout mode)

| Đối tượng | Font | Size | Màu chữ |
|----------|------|------|--------|
| Area Label | Calibri | 14 | #333333 |
| Device Label | Calibri | 10 | #000000 |
| Link Label | Calibri | 9 | #000000 |
| Interface Tag | Calibri | 9 | #000000 |

### 7.2 Preset nền (theo layout mode)

| Đối tượng | Nền |
|----------|-----|
| Area | #F0F0F0 |
| Interface Tag | #FFFFFF (80% opacity) |
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
| Device | Rect: `fill`, `stroke`, `strokeWidth`, `cornerRadius` | Rectangle (rounded) | Fill solid, line solid |
| Device Label | Text: `fontFamily`, `fontSize`, `fill` | TextBox | Font + size + color |
| Waypoint | Rect/Circle | Diamond/Ellipse | Fill solid, line solid |
| Link | Line: `stroke`, `strokeWidth`, `dash` | Line | Line color + width + dash |
| Link Label | Text: `fontFamily`, `fontSize`, `fill` | TextBox | Font + size + color |
| Interface Tag | Rect + Text | Rectangle + TextBox | Fill (alpha) + line |

**Lưu ý:**
- Không dùng gradient trong chế độ preset.
- Mọi color map từ preset RGB → PPTX RGB.

---

## 12. Quy tắc zoom/LOD (giảm rối khi sơ đồ lớn)

| Ngưỡng zoom | Hiển thị |
|------------|----------|
| ≥ 1.0 | Hiển thị đầy đủ label + interface tag |
| 0.7 – 0.99 | Ẩn interface tag, giữ device label |
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
- Gradient/opacity tự do (trừ interface tag theo preset).
- Thay đổi font family ngoài `Calibri` khi xuất PPTX.

---

## 14. Kiểm tra rule-based (tham chiếu)

- Bộ quy tắc kiểm tra tối thiểu (không chồng lấn, khoảng cách tối thiểu, nhãn không đè, số lượng node/link, logic L1→L2→L3) được chuẩn hóa tại `docs/RULE_BASED_CHECKS.md`.
- Layout mode có thể override các tham số khoảng cách theo preset hoặc cấu hình admin.
