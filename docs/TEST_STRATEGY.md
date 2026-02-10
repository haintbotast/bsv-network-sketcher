# Chiến lược kiểm thử

> **Phiên bản:** 1.2
> **Tạo:** 2026-01-23
> **Cập nhật:** 2026-02-10  
> **Mục tiêu:** Quy định chiến lược kiểm thử và golden files.

## 1. Kiểm thử backend

### 1.1 Kiểm thử layout (AI Context)
- **group_by_area:** thiết bị không vượt biên Area; macro/micro layout tách tầng.
- **grid placement map ưu tiên:** khi dữ liệu có `grid_row/grid_col` tạo thành lưới nhiều hàng và nhiều cột, macro layout phải bám theo placement map.
- **grid_center_slot_policy:** macro grid phải căn giữa area theo trục cột và dùng bề rộng cột đại diện (trung vị) để tránh cột bị kéo giãn bởi area outlier.
- **top‑to‑bottom:** Core/Dist ở hàng trên, Access giữa, Endpoints dưới (ưu tiên cha ở trên con).
- **_AIR_ spacing:** giữ thẳng cột, không chồng lấn.
- **same_type_row:** thiết bị cùng loại ưu tiên ở cùng hàng khi `max_nodes_per_row` cho phép.
- **micro_row_center_policy:** khi 1 layer tách thành nhiều hàng, các hàng phải được căn giữa theo chiều ngang để bố cục cân đối.
- **port_label_band:** giãn khoảng cách thiết bị có tính đến kích thước nhãn cổng.
- **port_embedded_render:** L1 port label phải nằm trong object (port band top/bottom), không hiển thị overlay label trên link.
- **l1_technical_render:** L1 giữ nét kỹ thuật (đường orthogonal, góc vuông rõ, giảm dùng màu nhấn cho link LAN/DEFAULT).
- **area_compact_render:** L1 hiển thị Area dạng compact theo cụm thiết bị để giảm khoảng trắng nhưng không làm sai dữ liệu area gốc.
- **peer_control_link_render:** `STACK/HA/HSRP` phải có style hiển thị riêng (màu/nét/lane) và không hòa lẫn với uplink/data.
- **port_anchor_override:** override anchor per-port **được ưu tiên** và **không bị auto-layout ghi đè**; kiểm tra thêm trường hợp `offset_ratio = null` để giữ auto offset.
- **port_anchor_swap_quick_action:** thao tác nhanh đổi vị trí 2 port cùng device trong `Anchor port (override)` phải swap đúng `side + offset_ratio`, chỉ ảnh hưởng đúng 2 port được chọn.
- **uplink_anchor_policy:** L1 auto-anchor phải đặt **uplink ở top** và **non-uplink ở bottom**; chỉ lệch khi có override thủ công.
- **endpoint_anchor_alignment_policy:** endpoint của link L1 phải bám đúng anchor ô port (không dời anchor để tách lane).
- **port_cell_center_alignment_policy:** với port band top/bottom, tọa độ anchor X của link phải trùng tâm ô port render (sai số <= 1px).
- **l1_auto_side_stability_policy:** auto-pass L1 không tự ép `left/right`; side tự động chỉ dùng `top/bottom` khi không có override thủ công.
- **l1_override_side_normalization_policy:** ở L1, override side phải được chuẩn hóa theo port band (`top` giữ nguyên, `left/right/bottom` về `bottom`) để tránh lệch anchor so với điểm render port.
- **l1_no_object_crossing_policy:** tuyến L1 sau chuẩn hóa orthogonal không được xuyên qua device/area không liên quan.
- **l1_path_validity_gate_policy:** mọi tuyến candidate/fallback sau khi dựng path đều phải pass `pathBlocked`; không được giữ tuyến bị chặn để render.
- **l1_boundary_escape_fallback_policy:** khi fallback cục bộ thất bại, router phải thử hành lang biên theo cụm obstacle lân cận link trước, chỉ mở rộng phạm vi khi cần.
- **l1_fallback_detour_guard_policy:** candidate fallback có quãng đường vòng quá xa so với khoảng cách trực tiếp phải bị loại.
- **l1_offset_reduction_retry_policy:** trước khi dùng fallback xa, router phải thử giảm dần độ tách `bundle/stem` để tìm tuyến gần hơn và ít méo hơn.
- **port_turn_clearance_policy:** điểm rẽ đầu tiên của link L1 phải cách port band đủ xa để không dính nhãn port.
- **l1_stub_fan_rank_policy:** fan-out đoạn stub phải dựa trên rank endpoint active theo `(device, side)`, không phụ thuộc trực tiếp vào bề rộng/cao device.
- **l1_short_same_side_fan_sync_policy:** link nội‑area ngắn có hai đầu cùng side phải đồng bộ fan hai đầu để tránh “hộp nhỏ” gần port band.
- **l1_direct_intra_priority_policy:** với cặp nội‑area theo phương ngang, cùng side `top/top` hoặc `bottom/bottom`, nếu tuyến direct/orthogonal ngắn không bị cản thì phải ưu tiên trước lane U theo purpose.
- **l1_vertical_pair_routing_policy:** với cặp nội‑area xếp dọc trên‑dưới, routing không ép theo rule direct ngang; phải giữ tuyến orthogonal dọc dễ đọc.
- **l1_vertical_bundle_separation_policy:** với bundle ưu tiên trục dọc, khoảng tách lane phải được tăng so với trục ngang để giảm chồng đoạn đứng.
- **l1_stem_deoverlap_policy:** sau stub rời port, router phải cho phép lệch nhỏ theo rank endpoint để giảm hiện tượng các đoạn đứng/đoạn ngang dính sát nhau.
- **l1_global_lane_two_axis_policy:** router phải tách làn chung theo cả 2 hướng ngang/dọc trong cùng cụm gần để giảm dính bó giữa các cặp link khác nhau.
- **l1_parallel_segment_nudge_policy:** hậu xử lý phải nudge các segment ngang/dọc song song trong cùng corridor, đồng thời bảo toàn segment `anchor→stub` hai đầu để không lệch điểm xuất phát tại port.
- **l1_no_edge_hugging_policy:** segment link chạy trùng mép object (colinear với cạnh rect trong clearance) phải bị coi là va chạm và được reroute.
- **l1_port_exit_orthogonality_policy:** khi dịch tách lane sau stub, tuyến phải giữ các đoạn orthogonal tuần tự, không xuất hiện segment chéo ngay sau port.
- **auto_layout_trigger_policy:** auto-layout tự chạy khi mở project và CRUD topology (area/device/link/port-link/anchor); thao tác viewport (`pan/zoom/reset view`) không được trigger.
- **main_navigator_center_policy:** cụm điều khiển viewport/view mode (`zoom/reset/L1/L2/L3/Sửa vị trí`) hiển thị canh giữa trong main navigator panel.
- **manual_position_edit_policy:** khi bật chế độ sửa vị trí, kéo‑thả `Area/Device` phải lưu `position_x/position_y` về DB ở `drag-end` và không trigger `/auto-layout`.
- **drag_alignment_policy:** trong chế độ sửa vị trí phải hiển thị guide ngang/dọc và snap nhẹ khi object gần mốc align của object liên quan.
- **position_standard_table_policy:** `position_x/position_y` sau drag hoặc nhập tay phải nằm trên mốc chuẩn (bội số step 0.25 đv).
- **layout_db_grid_sync_policy:** khi apply auto-layout vào DB (L1/L2/L3 + waypoint), phải đồng bộ chặt `position_*` và `grid_range`; `grid_row/grid_col` của Area được giữ như placement map logic (không bị auto-layout ghi đè).
- **peer_control_quick_create_policy:** tab Bố cục có form khai báo nhanh peer-control (`STACK/HA/HSRP`), tạo link đúng purpose/line_style và trigger auto-layout theo reason `link-crud`.
- **peer_control_legend_policy:** legend peer-control hiển thị đúng mapping màu/nét/chú giải cho `STACK/HA/HSRP`.
- **link_update_validation:** cập nhật link phải chặn **trùng link** và **port đã dùng** (kể cả khi chỉ đổi đầu còn lại).
- **inter‑area:** link khác Area bắt buộc qua Waypoint area (`_wp_`).
- **inter_area_simple_corridor_policy:** cặp Area dùng hành lang orthogonal đơn giản + lane offset nhẹ theo bundle index, không tạo spaghetti lane.
- **inter_area_no_outside_bounds_policy:** fallback liên‑area không được đi ngoài đường bao sơ đồ.
- **routing_single_pass_policy:** pipeline routing L1 phải chạy single-pass (không A\*, không pass-2 anchor refinement) và vẫn trả tuyến hợp lệ.
- **peer_lane_side_policy:** với link peer-control, lane phải bám theo side anchor (`bottom/bottom` đi dưới, `top/top` đi trên) để tránh cắt xuyên thân thiết bị.

### 1.2 Kiểm thử overview/L2/L3
- Overview (nếu bật) chỉ L1/flow; L2/L3 không render nhãn trong overview.
- L2/L3 view hiển thị nhãn đúng, không đè lên thiết bị (band nhãn).

- Bao phủ kiểm tra liên lớp L1→L2→L3 (interface tồn tại, port-channel, virtual port).

```python
# tests/test_validation_service.py
import pytest
from app.services.validation_service import ValidationService

class TestPortNameNormalization:
    def setup_method(self):
        self.validator = ValidationService()

    def test_normalize_gigabit_ethernet(self):
        assert self.validator.normalize_port_name("Gi 0/1") == "GigabitEthernet 0/1"
        assert self.validator.normalize_port_name("GE 0/1") == "GigabitEthernet 0/1"
        assert self.validator.normalize_port_name("GigabitEthernet 0/1") == "GigabitEthernet 0/1"

    def test_normalize_loopback(self):
        assert self.validator.normalize_port_name("Lo 0") == "Loopback 0"
        assert self.validator.normalize_port_name("Loopback0") == "Loopback 0"

    def test_normalize_vlan(self):
        assert self.validator.normalize_port_name("Vlan 10") == "Vlan 10"
        assert self.validator.normalize_port_name("Vl10") == "Vlan 10"

    def test_invalid_port_name(self):
        assert self.validator.normalize_port_name("invalid") is None
        assert self.validator.normalize_port_name("") is None

class TestIPValidation:
    def setup_method(self):
        self.validator = ValidationService()

    def test_valid_ip(self):
        is_valid, _ = self.validator.validate_ip_address("192.168.1.1/24")
        assert is_valid

    def test_invalid_prefix(self):
        is_valid, msg = self.validator.validate_ip_address("192.168.1.1/33")
        assert not is_valid
        assert "prefix" in msg.lower()

    def test_invalid_octet(self):
        is_valid, msg = self.validator.validate_ip_address("256.168.1.1/24")
        assert not is_valid
        assert "octet" in msg.lower()
```

## 2. Kiểm thử tích hợp API

```python
# tests/test_api_projects.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_project():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login first
        login_response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123"
        })
        token = login_response.json()["access_token"]

        # Create project
        response = await client.post(
            "/api/v1/projects/",
            json={"name": "Test Network", "description": "Test project"},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Network"
        assert "id" in data

@pytest.mark.asyncio
async def test_add_device():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # ... auth ...

        # Create area first
        await client.post(f"/api/v1/projects/{project_id}/areas/", json={
            "name": "Core",
            "grid_row": 1,
            "grid_col": 1
        }, headers=headers)

        # Add device
        response = await client.post(
            f"/api/v1/projects/{project_id}/devices/",
            json={
                "name": "Core-SW-1",
                "area_name": "Core",
                "device_type": "Switch",
                "grid_row": 1,
                "grid_col": 1
            },
            headers=headers
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Core-SW-1"
```

## 3. Kiểm thử E2E

```typescript
// tests/e2e/diagram-editor.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Diagram Editor', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('[data-testid="email"]', 'test@example.com')
    await page.fill('[data-testid="password"]', 'testpass123')
    await page.click('[data-testid="login-button"]')
    await expect(page).toHaveURL('/dashboard')
  })

  test('should create new project and add devices', async ({ page }) => {
    // Create project
    await page.click('[data-testid="new-project-button"]')
    await page.fill('[data-testid="project-name"]', 'E2E Test Network')
    await page.click('[data-testid="create-project-submit"]')

    // Should redirect to editor
    await expect(page).toHaveURL(/\/projects\/.*\/editor/)

    // Add area
    await page.click('[data-testid="add-area-button"]')
    await page.fill('[data-testid="area-name"]', 'Core')
    await page.click('[data-testid="save-area"]')

    // Verify area appears on canvas
    await expect(page.locator('[data-testid="area-Core"]')).toBeVisible()

    // Add device
    await page.click('[data-testid="add-device-button"]')
    await page.fill('[data-testid="device-name"]', 'Core-SW-1')
    await page.selectOption('[data-testid="device-area"]', 'Core')
    await page.click('[data-testid="save-device"]')

    // Verify device appears
    await expect(page.locator('[data-testid="device-Core-SW-1"]')).toBeVisible()
  })

  test('should export L1 diagram', async ({ page }) => {
    await page.goto('/projects/existing-project/editor')

    // Click export
    await page.click('[data-testid="export-button"]')
    await page.click('[data-testid="export-l1-pptx"]')

    // Wait for job completion
    await expect(page.locator('[data-testid="export-status"]')).toHaveText('Completed', {
      timeout: 60000
    })

    // Download should be available
    await expect(page.locator('[data-testid="download-button"]')).toBeEnabled()
  })
})
```

---

## 4. Regression testing

**Mục tiêu:** đảm bảo đầu ra PPTX/Excel đúng logic và style chung.

> **Lưu ý:** Dự án không yêu cầu tương thích 1:1 với Network Sketcher gốc. Thay vào đó, tự định nghĩa expected output dựa trên `docs/DIAGRAM_STYLE_SPEC.md`.

**Thiết lập:**
- Tạo bộ input chuẩn (small/medium/large) trong `templates/samples/`.
- Tạo expected output **theo style chung** làm baseline.
- Script so sánh: kiểm tra cấu trúc slide/shape + bảng Excel.

**Nếu bỏ golden files (chỉ kiểm tra rule-based):** Xem chi tiết tại `docs/RULE_BASED_CHECKS.md`.
- Không chồng lấn node/link.
- Khoảng cách tối thiểu giữa node.
- Nhãn không đè lên node/link.
- Đúng số lượng node/link và quan hệ logic L1→L2→L3.

**Ma trận kiểm thử tối thiểu (rule-based):**

| Rule | Loại test | Mô tả tối thiểu |
|---|---|---|
| RB-001..RB-005 | Unit | Validate liên kết/port/interface tồn tại, L1/L2/L3 hợp lệ |
| RB-008..RB-012 | Unit | Validate endpoint uplink, VPN/Firewall, Server area, Access placement, Server uplink |
| RB-010A | Unit | Validate Monitor/NOC/NMS vào Area IT |
| RB-006 | Integration | So sánh số lượng node/link trước & sau layout |
| RB-101..RB-104 | Integration | Kiểm tra chồng lấn, nằm trong area, link xuyên node |
| RB-121..RB-122 | Integration | Kiểm tra va chạm nhãn/nhãn lên node/link |
| RB-141..RB-143 | Integration | Cảnh báo khoảng cách tối thiểu |
| RB-201..RB-202 | Unit/Integration | Kiểm tra hướng layout theo style chung |

**Checklist regression bắt buộc (rule-based):**
- [ ] RB-001..RB-005: dữ liệu liên lớp hợp lệ, không tạo interface ảo sai.
- [ ] RB-008..RB-012: endpoint không uplink trực tiếp lên core/dist; VPN nhận diện đúng; Server/NAS/Storage vào Area Server; Access vào area nghiệp vụ; Server chỉ uplink lên Server Distribution.
- [ ] RB-010A: Monitor/NOC/NMS vào Area IT.
- [ ] RB-006: số lượng node/link trước & sau layout không đổi.
- [ ] RB-101..RB-104: không chồng lấn; device nằm trong area; link không xuyên node.
- [ ] L1 routing: khi đường thẳng bị cản bởi area/device, link phải bẻ hướng để tránh vật cản.
- [ ] L1 routing: liên‑area/waypoint không đi ngoài đường bao sơ đồ; fallback luôn chọn tuyến nội vùng hợp lệ.
- [ ] L1 routing: cặp area có nhiều link vẫn bám hành lang orthogonal đơn giản, lane offset theo bundle đủ để tránh dính sát nhau.
- [ ] L1 routing: pipeline single-pass (không A\*) vẫn trả tuyến hợp lệ, không tạo vòng lặp dựng đường.
- [ ] L1 routing: link peer-control `top/top` đi trên và `bottom/bottom` đi dưới thiết bị, không cắt xuyên thân thiết bị.
- [ ] Trigger policy: mở project chạy auto-layout đúng 1 lượt.
- [ ] Trigger policy: CRUD area/device/link/port-link/anchor đều trigger auto-layout.
- [ ] Trigger policy: pan/zoom/reset view không phát sinh request `/auto-layout`.
- [ ] Main navigator panel: cụm `zoom/reset/L1/L2/L3/Sửa vị trí` hiển thị canh giữa panel ở desktop.
- [ ] Trigger policy: CRUD dồn dập khi đang chạy auto-layout chỉ tạo thêm 1 lượt chạy bù sau cùng.
- [ ] Trigger policy: auto-run chỉ báo lỗi, không báo success.
- [ ] Grid center-slot: cột chứa area rất rộng không được kéo lệch toàn bộ cột; area nhỏ trong cùng cột vẫn căn giữa theo cột.
- [ ] Micro row center: layer nhiều hàng phải căn giữa, hàng ngắn không dồn trái cứng.
- [ ] Manual position edit: bật chế độ sửa vị trí, kéo‑thả `Area/Device` và thả chuột sẽ lưu `position_x/position_y` thành công.
- [ ] Manual position edit: thao tác kéo‑thả chỉnh vị trí không phát sinh request `/auto-layout`.
- [ ] Manual position edit: khi tắt chế độ sửa vị trí, kéo chuột trên object không thay đổi tọa độ lưu DB.
- [ ] Manual position edit: khi drag gần trục giữa/mép của object liên quan, phải hiện guide ngang/dọc và object snap nhẹ vào trục đó.
- [ ] Position standard table: tọa độ lưu DB sau drag luôn là bội số 0.25 đv (không còn số lẻ rời rạc như 12.13).
- [ ] Uplink anchor policy: endpoint uplink (tier thấp -> tier cao) luôn neo ở top; chiều ngược lại neo ở bottom.
- [ ] Uplink anchor policy: khi không suy ra tier, heuristic `port index = 1` phải neo top.
- [ ] Uplink anchor policy: override thủ công (`side + offset_ratio`) phải giữ ưu tiên cao nhất.
- [ ] Port anchor swap quick action: đổi vị trí 2 port cùng device phải cập nhật đúng cặp anchor của 2 port đó, không làm thay đổi anchor các port còn lại.
- [ ] Endpoint anchor alignment: endpoint link L1 trùng anchor port-cell tương ứng (sai số render <= 1px), lane separation bắt đầu sau stub.
- [ ] Port-cell center alignment: với device có port dài/ngắn khác nhau, điểm xuất phát link vẫn trùng tâm ô port tương ứng (không lệch sang khe giữa ô).
- [ ] L1 auto-side stability: khi không có override thủ công, auto anchor không phát sinh side `left/right`.
- [ ] L1 override side normalization: dữ liệu override `left/right` ở L1 vẫn phải cho endpoint bám đúng side port band và không tạo đoạn lệch khỏi ô port.
- [ ] L1 no-object crossing: link sau chuẩn hóa orthogonal không xuyên device/area không liên quan trong các cụm dày.
- [ ] L1 path validity gate: không có link nào được render nếu còn va chạm obstacle sau các nhánh fallback.
- [ ] L1 boundary escape fallback: trong ca dense obstacles, router ưu tiên hành lang biên theo cụm gần; chỉ mở rộng xa khi các cách gần đều không hợp lệ.
- [ ] Port turn clearance: điểm rẽ đầu tiên không dính sát port band/label ở scale 1x (đạt khoảng cách tối thiểu theo profile tuning).
- [ ] Stub fan rank: endpoint active cùng `(device, side)` được tách fan theo thứ tự ổn định; spread fan không vượt ngưỡng style tại scale hiện hành.
- [ ] Short same-side fan sync: link nội‑area ngắn có hai đầu cùng side không tạo “hộp nhỏ” sát port (fan hai đầu đồng bộ).
- [ ] Direct intra priority: cặp ngang `top/top` hoặc `bottom/bottom` không vật cản phải đi tuyến direct/orthogonal ngắn, không bị ép chữ U chỉ vì purpose.
- [ ] Vertical pair routing: cặp xếp dọc trên‑dưới không dùng rule direct ngang; tuyến giữ dạng orthogonal dọc nhất quán.
- [ ] Vertical bundle separation: cụm link ưu tiên trục dọc không bị dính/chồng đoạn đứng khi số link tăng.
- [ ] Stem de-overlap: với cụm port dày, các đoạn đứng rời port và đoạn chuyển tiếp không còn đè lên nhau thành một nét.
- [ ] Global lane two-axis: trong cụm dày, cả bó ngang và bó dọc đều được tách làn ổn định giữa nhiều cặp link khác nhau.
- [ ] Parallel segment nudge: trong cụm line ngang/dọc dày, các segment giữa được tách rõ, còn đoạn `anchor→stub` sát port vẫn giữ ổn định.
- [ ] Fallback detour guard: tuyến fallback không xuất hiện vòng xa bất thường (độ dài route trong ngưỡng cho phép theo profile scale).
- [ ] Offset reduction retry: khi tăng spacing làm route thất bại, router tự giảm dần offset và vẫn tìm được tuyến hợp lệ gần endpoint.
- [ ] No edge-hugging: link không bám trùng mép trái/phải/top/bottom của object trong các ca dense routing.
- [ ] Port exit orthogonality: sau điểm rời port/stub không có đoạn chéo; chỉ có chuỗi bước ngang/dọc.
- [ ] Port embedded render: port label hiển thị trong object theo dải top/bottom, không còn nhãn port nổi trên link ở view L1.
- [ ] Port embedded render: object tự nới rộng/nới cao theo số lượng và độ dài port để không đè chữ.
- [ ] Dense row spacing: với cụm nhiều uplink giữa 2 hàng thiết bị, auto-layout phải tăng khoảng cách hàng đủ để giảm chèn/đè link.
- [ ] L1 technical render: tuyến L1 giữ orthogonal/góc vuông, không bị bo cong quá mức.
- [ ] L1 technical render: link LAN/DEFAULT ở L1 dùng màu trung tính, chỉ purpose đặc biệt mới dùng màu nhấn.
- [ ] Area compact render: khung Area hiển thị co theo cụm thiết bị (giảm khoảng trắng lớn) và không làm thay đổi lưu trữ area trong DB.
- [ ] Peer-control render: link `STACK/HA/HSRP` dùng màu/nét đúng quy ước và dễ phân biệt với link mặc định.
- [ ] Peer-control quick create: tạo link từ form nhanh trong tab Bố cục phải tạo đúng `from_device/from_port/to_device/to_port/purpose/line_style`.
- [ ] Peer-control legend: panel hiển thị đủ 3 dòng `STACK/HA/HSRP` với màu/nét/chú giải đúng mapping style.
- [ ] Peer-control routing: với thiết bị cùng hàng trong nội-area, link `STACK/HA/HSRP` ưu tiên tuyến ngắn, ít giao cắt.
- [ ] RB-121..RB-122: nhãn không đè lên node/link; port cell/nhãn cổng hợp lệ.
- [ ] RB-141..RB-143: cảnh báo khoảng cách hiển thị đúng khi vi phạm ngưỡng.
- [ ] RB-201..RB-202: hướng layout đúng style chung.
- [ ] RB-205..RB-206: cảnh báo đúng khi Edge/Security/DMZ/Core/Dist nằm ngoài Data Center; Server placement gần DMZ.

**Bộ dữ liệu:**
- **Small:** ~10 devices, 10–20 links → `templates/samples/small.json`
- **Medium:** ~20 devices, 25–40 links → `templates/samples/medium.json`
- **Large:** ~1000 devices, 1500+ links (tạo bằng script khi cần; chỉ dùng cho regression định kỳ)

**Quy trình:**
1) Chạy export từ web app.
2) So sánh với expected output (do dự án tự định nghĩa).
3) Chênh lệch → cập nhật spec hoặc sửa logic.

---

## 5. Cấu trúc test fixtures

### 5.1 Thư mục và files

```
bsv-network-sketcher/
├── schemas/
│   └── template.json              # JSON Schema chính thức
├── templates/
│   └── samples/
│       ├── minimal.json           # 1 area, 2 devices, 1 link
│       └── small.json             # 3 areas, 10 devices, 10 links
└── scripts/
    ├── validate_template.py       # Validate JSON theo schema
    └── extract_metadata.py        # Trích metadata từ PPTX/Excel
```

### 5.2 Sử dụng

**Validate template:**
```bash
python3 scripts/validate_template.py templates/samples/small.json
python3 scripts/validate_template.py --all  # Validate tất cả
```

**Trích metadata từ output (khi có PPTX generator):**
```bash
python3 scripts/extract_metadata.py output.pptx -o metadata.json --pretty
```

### 5.3 Tạo expected output samples

Khi PPTX generator hoàn thành:
1. Chạy export với `templates/samples/small.json`
2. Kiểm tra output đúng theo `docs/DIAGRAM_STYLE_SPEC.md`
3. Lưu metadata làm baseline cho regression test

### 5.4 Script trích metadata

```python
# scripts/extract_metadata.py (đã có sẵn)
def extract_pptx_metadata(pptx_path: str) -> dict:
    """Trích xuất metadata từ PPTX"""
    prs = Presentation(pptx_path)
    metadata = {
        "slide_count": len(prs.slides),
        "shapes": [],
        "text_content": []
    }

    for slide_idx, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            shape_data = {
                "slide": slide_idx,
                "type": shape.shape_type.name if hasattr(shape.shape_type, 'name') else str(shape.shape_type),
                "left": round(shape.left.inches, 3),
                "top": round(shape.top.inches, 3),
                "width": round(shape.width.inches, 3),
                "height": round(shape.height.inches, 3),
            }

            # Trích xuất màu nếu có
            if hasattr(shape, 'fill') and shape.fill.type is not None:
                if shape.fill.fore_color and shape.fill.fore_color.rgb:
                    shape_data["fill_color"] = str(shape.fill.fore_color.rgb)

            # Trích xuất text nếu có
            if shape.has_text_frame:
                text = shape.text_frame.text.strip()
                if text:
                    shape_data["text"] = text
                    metadata["text_content"].append(text)

            metadata["shapes"].append(shape_data)

    return metadata

def extract_excel_metadata(xlsx_path: str) -> dict:
    """Trích xuất metadata từ Excel"""
    wb = load_workbook(xlsx_path)
    metadata = {
        "sheet_names": wb.sheetnames,
        "sheets": {}
    }

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        metadata["sheets"][sheet_name] = {
            "row_count": ws.max_row,
            "col_count": ws.max_column,
            "headers": [cell.value for cell in ws[1] if cell.value]
        }

    return metadata

```

### 5.5 Ngưỡng chấp nhận

| Tiêu chí | Ngưỡng | Ghi chú |
|---------|--------|---------|
| Số lượng shapes | Exact match | Không chấp nhận chênh lệch |
| Nội dung text | Exact match | Không chấp nhận chênh lệch |
| Vị trí (x, y) | ± 0.05 inch | Cho phép sai số nhỏ |
| Kích thước (w, h) | ± 0.02 inch | Cho phép sai số nhỏ |
| Màu sắc | Theo DIAGRAM_STYLE_SPEC | Tuân theo spec riêng |

---

## 6. Tài liệu liên quan

- `docs/DIAGRAM_STYLE_SPEC.md` - Quy chuẩn style output
- `docs/TEMPLATE_SCHEMA.md` - Schema validate input
- `docs/RULE_BASED_CHECKS.md` - Rule-based checks tối thiểu
- `docs/RELEASE_CHECKLIST.md` - Checklist phát hành tối thiểu
- `schemas/template.json` - JSON Schema chính thức
- `templates/samples/` - Mẫu dữ liệu test

---

## 7. Bổ sung test regression (2026-02-09)

- **Grid Excel canonical**
  - [ ] `grid_range` Area/Device parse đúng (`A1`, `A1:B3`, đảo chiều `B3:A1`).
  - [ ] Cập nhật `position_x/y/width/height` phải tự đồng bộ `grid_range`.
  - [ ] Sau khi chạy `/auto-layout` với `apply_to_db=true`, `Area/Device` không được lệch giữa dữ liệu `position_*` và `grid_range`.
  - [ ] Waypoint area (`_wp_`) tạo/cập nhật sau auto-layout phải có `grid_range` hợp lệ và giữ `grid_row/grid_col = 99`.
- **Device Port CRUD**
  - [ ] Tạo/sửa/xóa port theo device (`name`, `side`, `offset_ratio`).
  - [ ] Chặn đổi tên/xóa port khi port đang được dùng trong link.
- **Link endpoint validation theo port khai báo**
  - [ ] Tạo/sửa link thất bại khi `from_port` hoặc `to_port` chưa khai báo trên đúng device.
  - [ ] Port format chấp nhận `Gi 0/1`, `Gi0/1`, `P1`; từ chối chuỗi ký tự không hợp lệ.
- **UI data flow**
  - [ ] Load project phải tải đồng thời areas/devices/device_ports/links/anchor overrides.
  - [ ] Canvas port band hiển thị theo `device_ports`, không phụ thuộc hoàn toàn vào links.
