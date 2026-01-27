# Tham chiếu logic NS gốc

> **Phiên bản:** 1.1
> **Tạo:** 2026-01-23
> **Cập nhật:** 2026-01-27
> **Nguồn:** Trích từ `WEB_APP_DEVELOPMENT_PLAN.md`.

Section này cung cấp mapping chi tiết giữa source code gốc của Network Sketcher và các component tương ứng trong Web App, **chỉ để tham chiếu** logic nghiệp vụ.

**Lưu ý phạm vi:** Dự án web **không triển khai CLI/CLI wrapper**; các tệp/luồng CLI bên dưới chỉ dùng để đối chiếu logic, **không làm tiêu chí 1:1** cho layout/output.

### 13.0 Kho mã nguồn tham chiếu

Dự án này dựa trên source gốc của Network Sketcher để tham chiếu tính năng/chức năng/logic.

```
https://github.com/cisco-open/network-sketcher
```

### 13.0.1 AI Context (nguồn tham chiếu bổ sung)

**Nguồn gốc:** `docs/[AI_Context]no_data.txt` (tiếng Anh, file gốc do NS sinh).  
**Mục tiêu:** Trích các ràng buộc layout/logic quan trọng để áp dụng cho web app.

**Tóm tắt ràng buộc bắt buộc:**
- **Bố cục phân tầng top‑to‑bottom:** Core/Distribution ở hàng trên, Access ở giữa, Endpoints ở dưới; quan hệ cha‑con phải theo chiều dọc.
- **Grid theo hàng/cột** và dùng `_AIR_` làm ô trống để canh cột, giữ thẳng hàng.
- **Liên kết khác Area bắt buộc qua Waypoint area** (tên kết thúc `_wp_`); không nối trực tiếp Area‑Area.
- **Physical vs Logical:** Area = phân tách vật lý; VRF/VLAN = phân tách logic (không tạo Area riêng cho VRF).
- **Ưu tiên bảo toàn layout gốc** khi đã có bố cục; auto‑layout chỉ là hỗ trợ.

**Áp dụng cho web app:**
- Auto‑layout phải theo **2 tầng**: macro (Area) + micro (thiết bị trong Area).
- Overview mặc định **chỉ L1/flow** để giữ sạch bố cục; L2/L3 chỉ hiển thị ở view riêng.

### 13.1 Tổng quan tệp nguồn

```
network-sketcher/
├── ns_def.py                    # Core definitions, utilities, colors
├── ns_cli.py                    # CLI commands, validation (tham chiếu)
├── ns_ddx_figure.py             # PPTX generation engine
├── ns_l1_master_create.py       # L1 diagram data creation
├── ns_l2_diagram_create.py      # L2 diagram generation
├── ns_l3_diagram_create.py      # L3 diagram generation
├── ns_sync_between_layers.py    # L1↔L2↔L3 synchronization
└── scripts/
    ├── ns_cli_wrapper.py        # CLI wrapper with themes (tham chiếu)
    ├── import_from_excel.py     # Excel import logic
    └── create_excel_template.py # Template generation
```

### 13.2 Định nghĩa cốt lõi (`ns_def.py`)

#### 13.2.1 Kiểm tra hợp lệ tên cổng

**Original Function:** `split_portname()` (line ~200-250)

```python
# ns_def.py - Phân tách tên cổng thành loại và số
def split_portname(portname):
    """
    Tách port name thành (interface_type, number)
    VD: "Ethernet 1/1" → ("Ethernet", "1/1")
        "Gi 0/0/0" → ("Gi", "0/0/0")

    IMPORTANT: NS requires space between type and number!
    "Eth1/1" is INVALID, must be "Eth 1/1"
    """
```

**Web App Equivalent:**
```python
# services/validation_service.py
class ValidationService:
    PORT_PATTERN = re.compile(r'^([A-Za-z-]+)\s+(.+)$')

    def validate_port_name(self, port_name: str) -> tuple[str, str]:
        match = self.PORT_PATTERN.match(port_name)
        if not match:
            raise ValidationError(f"Invalid port format: {port_name}. Must have space between type and number.")
        return match.groups()
```

#### 13.2.2 Định nghĩa màu theo ngành

**Original Location:** `ns_def.py` (line ~50-100) và hệ theme gốc (CLI)

```python
# Ánh xạ INDUSTRY_COLORS - màu thiết bị theo tiền tố tên
DEVICE_COLORS = {
    # Routers
    'Router': [70, 130, 180],    # Steel Blue
    'ISP': [70, 130, 180],

    # Firewalls
    'FW': [220, 60, 60],         # Crimson Red
    'Firewall': [220, 60, 60],

    # Switches
    'Core-SW': [34, 139, 34],    # Forest Green
    'Dist': [60, 179, 113],      # Medium Sea Green
    'Access-SW': [0, 139, 139],  # Dark Cyan

    # Máy chủs
    'Server': [106, 90, 205],    # Slate Blue
    'DB': [148, 0, 211],         # Dark Violet
    'App': [138, 43, 226],       # Blue Violet
    'Web': [75, 0, 130],         # Indigo

    # Storage
    'NAS': [210, 105, 30],       # Chocolate
    'SAN': [184, 134, 11],       # Dark Goldenrod

    # End Devices
    'PC': [119, 136, 153],       # Light Slate Gray
    'Workstation': [112, 128, 144],

    # Wireless
    'WiFi': [135, 206, 250],     # Light Sky Blue
    'AP': [135, 206, 250],

    # Default
    '_DEFAULT_': [235, 241, 222],
}

# Màu mục đích liên kết (theme tương phản gốc)
LINK_PURPOSE_COLORS = {
    'WAN': [70, 130, 180],       # Blue
    'INTERNET': [70, 130, 180],
    'DMZ': [255, 165, 0],        # Orange
    'LAN': [34, 139, 34],        # Green
    'MGMT': [128, 0, 128],       # Purple
    'HA': [128, 128, 128],       # Gray
    'STORAGE': [139, 69, 19],    # Brown
    'BACKUP': [64, 64, 64],      # Dark Gray
    'VPN': [139, 0, 0],          # Dark Red
}
```

**Web App Equivalent:**
```python
# utils/colors.py
def get_device_color(device_name: str) -> list[int]:
    """Auto-assign color based on device name prefix"""
    name_upper = device_name.upper()
    for prefix, color in DEVICE_COLORS.items():
        if prefix.upper() in name_upper:
            return color
    return DEVICE_COLORS['_DEFAULT_']

def get_link_color(purpose: str) -> list[int]:
    """Get link color based on purpose"""
    return LINK_PURPOSE_COLORS.get(purpose.upper(), [0, 0, 0])
```

### 13.3 Lệnh gốc (CLI) → API (tham chiếu)

#### 13.3.1 Ánh xạ lệnh → API

| Lệnh gốc (CLI) | Original Function | Web API Endpoint |
|-------------|-------------------|------------------|
| `add area_location` | `add_area_location()` | `POST /api/v1/projects/{id}/areas` |
| `add device_location` | `add_device_location()` | `POST /api/v1/projects/{id}/devices` |
| `add l1_link` | `add_l1_link()` | `POST /api/v1/projects/{id}/links` |
| `add l1_link_bulk` | `add_l1_link_bulk()` | `POST /api/v1/projects/{id}/links/bulk` |
| `add portchannel_bulk` | `add_portchannel_bulk()` | `POST /api/v1/projects/{id}/port-channels/bulk` |
| `add virtual_port_bulk` | `add_virtual_port_bulk()` | `POST /api/v1/projects/{id}/virtual-ports/bulk` |
| `add l2_segment_bulk` | `add_l2_segment_bulk()` | `POST /api/v1/projects/{id}/l2-segments/bulk` |
| `add ip_address_bulk` | `add_ip_address_bulk()` | `POST /api/v1/projects/{id}/l3-addresses/bulk` |
| `export l1_diagram` | `export_l1_diagram()` | `POST /api/v1/projects/{id}/export` body: `{type: "l1"}` |
| `export l2_diagram` | `export_l2_diagram()` | `POST /api/v1/projects/{id}/export` body: `{type: "l2"}` |
| `export l3_diagram` | `export_l3_diagram()` | `POST /api/v1/projects/{id}/export` body: `{type: "l3"}` |
| `show device` | `show_device()` | `GET /api/v1/projects/{id}/devices` |
| `show l1_link` | `show_l1_link()` | `GET /api/v1/projects/{id}/links` |

#### 13.3.2 Logic kiểm tra hợp lệ

**Original:** `ns_cli.py` lines ~100-200

```python
# Quy tắc kiểm tra hợp lệ từ ns_cli.py

def validate_area_exists(area_name, master_data):
    """Area trong devices.csv phải tồn tại trong areas.csv"""
    if area_name not in master_data['areas']:
        raise ValueError(f"Area '{area_name}' not found")

def validate_device_exists(device_name, master_data):
    """Device trong l1_links.csv phải tồn tại trong devices.csv"""
    if device_name not in master_data['devices']:
        raise ValueError(f"Device '{device_name}' not found")

def validate_port_exists(device_name, port_name, master_data):
    """Port trong l2_segments/ip_addresses phải tồn tại"""
    device_ports = master_data['devices'][device_name]['ports']
    if port_name not in device_ports:
        raise ValueError(f"Port '{port_name}' not found on '{device_name}'")
```

**Web App Equivalent:**
```python
# services/validation_service.py
class ValidationService:
    async def validate_topology_integrity(self, project_id: str) -> list[ValidationError]:
        errors = []

        # Check all device areas exist
        devices = await self.device_repo.get_all(project_id)
        areas = {a.name for a in await self.area_repo.get_all(project_id)}
        for device in devices:
            if device.area_name not in areas:
                errors.append(ValidationError(
                    level="error",
                    entity="device",
                    entity_id=device.id,
                    message=f"Device '{device.name}' references non-existent area '{device.area_name}'"
                ))

        # Check all link endpoints exist
        links = await self.link_repo.get_all(project_id)
        device_names = {d.name for d in devices}
        for link in links:
            if link.from_device not in device_names:
                errors.append(...)
            if link.to_device not in device_names:
                errors.append(...)

        return errors
```

### 13.4 Sinh PPTX (`ns_ddx_figure.py`)

#### 13.4.1 Lớp và phương thức chính

**File:** `ns_ddx_figure.py` (~1200 lines)

| Method | Line Range | Purpose | Web App Equivalent |
|--------|------------|---------|-------------------|
| `__init__()` | 50-90 | Initialize with meta Excel template | `PPTXGenerator.__init__()` |
| `add_root_folder()` | 100-150 | Create slide with root folder | `PPTXGenerator.create_slide()` |
| `add_sub_folder()` | 160-300 | Add area folder shapes | `PPTXGenerator.add_area()` |
| `add_shape()` | 350-600 | Add device shapes | `PPTXGenerator.add_device()` |
| `add_line()` | 620-750 | Draw connection lines | `PPTXGenerator.add_link()` |
| `add_line_tag()` | 780-900 | Add interface labels | `PPTXGenerator.add_interface_tag()` |
| `get_shape_width()` | 1077-1120 | Get shape dimensions | Style cache lookup |
| `get_shape_hight()` | 1123-1180 | Get shape height | Style cache lookup |

#### 13.4.2 Tối ưu bộ nhớ đệm

**Original Issue:** `ns_ddx_figure.py` scans 50,000 rows repeatedly for each shape lookup.

```python
# Đoạn code gốc chưa tối ưu (dòng ~1080)
def get_shape_width(self, shape_name):
    for row in range(1, 50001):
        if str(self.input_ppt_mata_excel.active.cell(row, 1).value) == '<<STYLE_SHAPE>>':
            for row2 in range(row + 1, 50001):
                if str(self.input_ppt_mata_excel.active.cell(row2, 1).value) == shape_name:
                    return float(self.input_ppt_mata_excel.active.cell(row2, 2).value)
```

**Web App Optimized:**
```python
# generators/pptx_generator.py
class PPTXGenerator:
    def __init__(self, template_path: str):
        self._style_cache = self._build_style_cache(template_path)

    def _build_style_cache(self, template_path: str) -> dict:
        """Build complete cache at initialization - O(n) once"""
        cache = {}
        wb = openpyxl.load_workbook(template_path)
        ws = wb.active

        in_style_section = False
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
            cell_value = str(row[0].value)
            if cell_value == '<<STYLE_SHAPE>>':
                in_style_section = True
                continue
            if in_style_section:
                if cell_value.startswith('<<'):
                    break
                cache[cell_value] = {
                    'width': float(row[1].value or 1.0),
                    'height': float(row[2].value or 0.5),
                    'degree': float(row[3].value or 0.0),
                    'color': row[4].value,
                }
        return cache

    def get_shape_dimensions(self, shape_name: str) -> tuple[float, float]:
        """O(1) lookup from cache"""
        style = self._style_cache.get(shape_name, self._style_cache['_DEFAULT_'])
        return style['width'], style['height']
```

#### 13.4.3 Logic điểm kết nối

**Original:** `ns_ddx_figure.py` lines 687-714

```python
# Logic kết nối giản lược - chỉ xét vị trí theo chiều dọc
def add_line(self, from_coords, to_coords):
    fx_left, fx_mid, fx_right = from_coords[1:4]
    fy_top, fy_mid, fy_down = from_coords[4:7]
    tx_left, tx_mid, tx_right = to_coords[1:4]
    ty_top, ty_mid, ty_down = to_coords[4:7]

    # Current simple logic
    if fy_mid > ty_mid:
        start_point = (fx_mid, fy_top)
        end_point = (tx_mid, ty_down)
    else:
        start_point = (fx_mid, fy_down)
        end_point = (tx_mid, ty_top)
```

**Web App Enhanced:**
```python
# generators/pptx_generator.py
def _get_best_connection_points(self, from_coords, to_coords):
    """Optimized connection point selection to minimize crossings"""
    fx_left, fx_mid, fx_right = from_coords['x_left'], from_coords['x_mid'], from_coords['x_right']
    fy_top, fy_mid, fy_down = from_coords['y_top'], from_coords['y_mid'], from_coords['y_bottom']
    tx_left, tx_mid, tx_right = to_coords['x_left'], to_coords['x_mid'], to_coords['x_right']
    ty_top, ty_mid, ty_down = to_coords['y_top'], to_coords['y_mid'], to_coords['y_bottom']

    dx = tx_mid - fx_mid
    dy = ty_mid - fy_mid

    # Choose sides based on relative direction
    if abs(dx) > abs(dy) * 1.5:  # Horizontal dominant
        if dx > 0:
            return (fx_right, fy_mid), (tx_left, ty_mid)
        else:
            return (fx_left, fy_mid), (tx_right, ty_mid)
    else:  # Vertical dominant
        if dy > 0:
            return (fx_mid, fy_down), (tx_mid, ty_top)
        else:
            return (fx_mid, fy_top), (tx_mid, ty_down)
```

### 13.5 Tạo sơ đồ L2 (`ns_l2_diagram_create.py`)

**File:** `ns_l2_diagram_create.py` (~500 lines)

#### 13.5.1 Hàm chính

| Function | Purpose | Web App Mapping |
|----------|---------|-----------------|
| `create_l2_diagram_data()` | Generate L2 topology data | `L2DiagramService.generate()` |
| `get_l2_segments_for_device()` | Get VLANs for a device | `L2SegmentRepository.get_by_device()` |
| `calculate_l2_area_layout()` | Layout L2 groups | `LayoutService.calculate_l2_layout()` |

#### 13.5.2 Logic gom nhóm phân đoạn L2

```python
# Logic gốc từ ns_l2_diagram_create.py

def group_devices_by_l2_segment(devices, l2_segments):
    """
    Group devices that share the same L2 segment (VLAN)
    Devices in same VLAN are drawn in same L2 "bubble"
    """
    segment_groups = defaultdict(list)

    for device in devices:
        device_segments = get_device_l2_segments(device)
        for segment in device_segments:
            segment_groups[segment].append(device)

    return segment_groups
```

### 13.6 Tạo sơ đồ L3 (`ns_l3_diagram_create.py`)

**File:** `ns_l3_diagram_create.py` (~600 lines)

#### 13.6.1 Bộ nhớ đệm kích thước chữ

**Original Optimization:** Lines 43-60

```python
# ns_l3_diagram_create.py - Đã có bộ nhớ đệm cho chữ
_text_size_cache = {}

def get_text_wh_cached(text, font_size=6):
    """Cached text width/height calculation"""
    cache_key = (text, font_size)
    if cache_key not in _text_size_cache:
        # Calculate text dimensions using PIL
        font = ImageFont.truetype("arial.ttf", font_size)
        bbox = font.getbbox(text)
        _text_size_cache[cache_key] = (bbox[2] - bbox[0], bbox[3] - bbox[1])
    return _text_size_cache[cache_key]
```

**Web App Equivalent:**
```python
# services/layout_service.py
from functools import lru_cache
from PIL import ImageFont

class LayoutService:
    @lru_cache(maxsize=10000)
    def get_text_dimensions(self, text: str, font_size: int = 6) -> tuple[int, int]:
        """Cached text dimension calculation"""
        font = ImageFont.truetype("arial.ttf", font_size)
        bbox = font.getbbox(text)
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])
```

### 13.7 Đồng bộ lớp (`ns_sync_between_layers.py`)

**File:** `ns_sync_between_layers.py` (~400 lines)

#### 13.7.1 Quy tắc đồng bộ

```python
# Quy tắc đồng bộ lớp từ ns_sync_between_layers.py

"""
Sync Direction: L1 → L2 → L3

Rules:
1. L1 physical ports auto-create interface entries
2. L2 segment assignment requires interface to exist
3. L3 IP assignment requires interface to exist (can be physical or virtual)
4. Virtual ports (Vlan X, Loopback X) only exist in L2/L3, not L1
5. Port-channel is logical interface in L2/L3, member ports are L1
"""

def sync_l1_to_l2(master_data):
    """Create L2 interface entries from L1 physical connections"""
    for link in master_data['l1_links']:
        # Ensure interfaces exist in L2 tables
        ensure_interface_exists(link['from_device'], link['from_port'])
        ensure_interface_exists(link['to_device'], link['to_port'])

def sync_l2_to_l3(master_data):
    """Carry forward L2 interfaces to L3"""
    for device_name, l2_data in master_data['l2_devices'].items():
        for interface in l2_data['interfaces']:
            ensure_l3_interface_exists(device_name, interface)
```

**Web App Equivalent:**
```python
# services/sync_service.py
class SyncService:
    async def sync_layers(self, project_id: str, source_layer: str = "l1"):
        """
        Synchronize data between layers.
        L1 changes propagate to L2, L2 changes propagate to L3.
        """
        if source_layer == "l1":
            await self._sync_l1_to_l2(project_id)
            await self._sync_l2_to_l3(project_id)
        elif source_layer == "l2":
            await self._sync_l2_to_l3(project_id)

    async def _sync_l1_to_l2(self, project_id: str):
        """Ensure all L1 physical interfaces exist in L2 layer"""
        links = await self.link_repo.get_all(project_id)
        for link in links:
            await self.interface_repo.ensure_exists(
                project_id, link.from_device_id, link.from_port, layer="l2"
            )
            await self.interface_repo.ensure_exists(
                project_id, link.to_device_id, link.to_port, layer="l2"
            )
```

### 13.8 Logic nhập Excel (`scripts/import_from_excel.py`)

#### 13.8.1 Thứ tự xử lý sheet

```python
# Thứ tự nhập rất quan trọng - cần thỏa các phụ thuộc

IMPORT_ORDER = [
    'Areas',        # 1. Define areas first
    'Devices',      # 2. Devices reference areas
    'L1_Links',     # 3. Links reference devices
    'PortChannels', # 4. Port-channels reference physical ports
    'VirtualPorts', # 5. Virtual ports reference devices
    'L2_Segments',  # 6. L2 segments reference ports (physical or virtual)
    'IP_Addresses', # 7. IPs reference ports
]
```

**Web App Import Service:**
```python
# services/import_service.py
class ImportService:
    IMPORT_ORDER = [
        ('Areas', AreaImporter),
        ('Devices', DeviceImporter),
        ('L1_Links', LinkImporter),
        ('PortChannels', PortChannelImporter),
        ('VirtualPorts', VirtualPortImporter),
        ('L2_Segments', L2SegmentImporter),
        ('IP_Addresses', IPAddressImporter),
    ]

    async def import_excel(self, project_id: str, file_path: str) -> ImportResult:
        result = ImportResult()
        wb = openpyxl.load_workbook(file_path)

        async with self.db.begin():
            for sheet_name, importer_class in self.IMPORT_ORDER:
                if sheet_name in wb.sheetnames:
                    importer = importer_class(self.db)
                    sheet_result = await importer.import_sheet(
                        project_id, wb[sheet_name]
                    )
                    result.merge(sheet_result)

        return result
```

#### 13.8.2 Nhập liệu trực tiếp & template dữ liệu (JSON)

**Nguyên tắc:** Luồng chính là nhập liệu trực tiếp theo schema chuẩn; Excel/CSV chỉ là tùy chọn chuyển đổi dữ liệu cũ.

**Chi tiết schema/validation:** xem `docs/TEMPLATE_SCHEMA.md`.

### 13.9 Tham chiếu theme từ CLI gốc (không triển khai CLI)

#### 13.9.1 Áp dụng theme

```python
# ns_cli_wrapper.py - Hỗ trợ tham số theme

def cmd_export(args):
    theme = args.theme  # e.g., "contrast"

    export_args = ['export', f'{diagram_type}_diagram', '--mode', mode, '--master', master_file]
    if theme:
        export_args.extend(['--theme', theme])

    run_ns(export_args)
```

**Web App Theme System:**
```python
# models/export.py
class ExportRequest(BaseModel):
    project_id: str
    diagram_type: Literal["l1", "l2", "l3", "all"]
    mode: Literal["all_areas", "per_area"] = "all_areas"
    theme: Literal["default", "contrast", "dark", "light"] = "default"
    format: Literal["pptx", "pdf", "png"] = "pptx"

# services/theme_service.py
class ThemeService:
    THEMES = {
        "default": DefaultTheme(),
        "contrast": ContrastTheme(),  # Purpose-based link colors
        "dark": DarkTheme(),
        "light": LightTheme(),
    }

    def get_theme(self, name: str) -> Theme:
        return self.THEMES.get(name, self.THEMES["default"])
```

### 13.10 Bảng tham chiếu nhanh

| NS Function/File | Location | Web App Service | Web App File |
|------------------|----------|-----------------|--------------|
| `split_portname()` | `ns_def.py:200` | `ValidationService.validate_port_name()` | `services/validation.py` |
| `get_device_color()` | `ns_def.py:50` | `ColorService.get_device_color()` | `utils/colors.py` |
| `add_l1_link()` | `ns_cli.py:150` | `LinkService.create()` | `services/link.py` |
| `add_shape()` | `ns_ddx_figure.py:350` | `PPTXGenerator.add_device()` | `generators/pptx.py` |
| `add_line()` | `ns_ddx_figure.py:620` | `PPTXGenerator.add_link()` | `generators/pptx.py` |
| `get_shape_width()` | `ns_ddx_figure.py:1077` | `StyleCache.get_dimensions()` | `generators/pptx.py` |
| `sync_l1_to_l2()` | `ns_sync_between_layers.py:100` | `SyncService.sync_layers()` | `services/sync.py` |
| `create_l2_diagram_data()` | `ns_l2_diagram_create.py:50` | `L2DiagramService.generate()` | `services/diagram.py` |
| `get_text_wh_cached()` | `ns_l3_diagram_create.py:43` | `LayoutService.get_text_dimensions()` | `services/layout.py` |

---

## 14. Edge Cases & Xử lý ngoại lệ

### 14.1 Port Name Edge Cases

| Input | NS Gốc | Web App Expected | Ghi chú |
|-------|--------|------------------|---------|
| `Gi0/1` | INVALID | Error: thiếu space | Bắt buộc có space |
| `Gi 0/1` | Valid | Valid | Đúng format |
| `GigabitEthernet 0/0/1` | Valid | Valid | Full name OK |
| `Ethernet1/1` | INVALID | Error: thiếu space | Bắt buộc có space |
| `Eth 1/1` | Valid | Valid | Short name OK |
| `Port-channel 1` | Valid | Valid | Hyphen trong type OK |
| `Po 1` | Valid | Valid | Short name OK |
| `Loopback0` | INVALID | Error: thiếu space | Phải là `Loopback 0` |
| `Lo 0` | Valid | Valid | Short name OK |
| `Vlan10` | INVALID | Error: thiếu space | Phải là `Vlan 10` |
| `Vl 10` | Valid | Valid | Short name OK |

### 14.2 Device Name Edge Cases

| Input | NS Gốc | Web App Expected | Ghi chú |
|-------|--------|------------------|---------|
| `Core-SW-1` | Valid, color=Green | Valid, auto-color | Prefix match |
| `CoreSW1` | Valid, color=Green | Valid, auto-color | Prefix match |
| `My Router` | Valid, color=Blue | Valid, auto-color | Space trong tên OK |
| `FW_DMZ` | Valid, color=Red | Valid, auto-color | Underscore OK |
| `Switch.Core.1` | Valid, color=Gray | Valid, default color | Dot trong tên OK |
| Empty string | INVALID | Error | Name required |
| `A` | Valid | Valid | Single char OK |
| 256 chars | INVALID | Error | Max 100 chars |

### 14.3 Link Edge Cases

| Scenario | NS Gốc | Web App Expected |
|----------|--------|------------------|
| Same device self-loop | Allowed | Allowed (với warning) |
| Duplicate link A→B | Error | Error: L1_LINK_DUP |
| Reverse link B→A | Allowed | Allowed (khác link) |
| Port used twice | Error | Error: PORT_ALREADY_USED |
| Device not found | Error | Error: DEVICE_NOT_FOUND |

### 14.4 Area Layout Edge Cases

| Scenario | NS Gốc | Web App Expected |
|----------|--------|------------------|
| Grid overlap (same row/col) | Allowed | Warning, auto-adjust |
| Grid gap (1,1), (1,3) | Allowed | Allowed |
| Negative grid | INVALID | Error |
| Grid 0,0 | INVALID | Error (min 1,1) |
| Area with no devices | Allowed | Allowed (empty area) |
| Area name duplicate | Error | Error: AREA_NAME_DUP |

---

## 15. Mapping lỗi NS gốc → Web App Error Codes

### 15.1 Validation Errors

| NS Gốc Message Pattern | Web App Code | User Message |
|------------------------|--------------|--------------|
| `Area '{name}' not found` | `AREA_NOT_FOUND` | Area '{name}' không tồn tại |
| `Device '{name}' not found` | `DEVICE_NOT_FOUND` | Thiết bị '{name}' không tồn tại |
| `Duplicate device name` | `DEVICE_NAME_DUP` | Tên thiết bị đã tồn tại |
| `Invalid port format` | `PORT_FORMAT_INVALID` | Định dạng port không hợp lệ |
| `Port '{port}' already used` | `PORT_ALREADY_USED` | Port '{port}' đã được sử dụng |
| `Invalid VLAN ID` | `VLAN_INVALID` | VLAN ID phải từ 1-4094 |
| `Invalid IP address` | `IP_INVALID` | Địa chỉ IP không hợp lệ |

### 15.2 Export Errors

| NS Gốc Message Pattern | Web App Code | User Message |
|------------------------|--------------|--------------|
| `No devices to export` | `EXPORT_NO_DATA` | Project không có dữ liệu để xuất |
| `Template not found` | `EXPORT_TEMPLATE_ERROR` | Không tìm thấy template xuất |
| `PPTX generation failed` | `EXPORT_PPTX_ERROR` | Lỗi tạo file PPTX |
| `Excel generation failed` | `EXPORT_EXCEL_ERROR` | Lỗi tạo file Excel |

---

## 16. Kiểm tra tương thích (Compatibility Checklist)

### 16.1 Checklist trước khi release

- [ ] **Port name validation:** Test với tất cả edge cases ở mục 14.1
- [ ] **Device color auto-assign:** Verify màu theo prefix (mục 13.2.2)
- [ ] **Link color by purpose:** Verify màu theo purpose (mục 13.2.2)
- [ ] **PPTX export:** So sánh với golden files
- [ ] **Excel export:** So sánh structure và data với golden files
- [ ] **L1 diagram layout:** Kiểm tra vị trí shapes
- [ ] **L2 diagram grouping:** Kiểm tra nhóm theo VLAN
- [ ] **L3 diagram IP labels:** Kiểm tra hiển thị IP
- [ ] **Interface tags:** Kiểm tra vị trí và nội dung tags
- [ ] **Line connection points:** Kiểm tra điểm kết nối (mục 13.4.3)

### 16.2 Regression test scenarios

| Test ID | Mô tả | Input | Expected Output |
|---------|-------|-------|-----------------|
| REG-001 | Small network L1 | 10 devices, 10 links | Match golden PPTX |
| REG-002 | Medium network L1 | 100 devices, 150 links | Match golden PPTX |
| REG-003 | Multi-area L1 | 5 areas, 50 devices | Match golden PPTX |
| REG-004 | L2 with VLANs | 20 devices, 5 VLANs | Match golden PPTX |
| REG-005 | L3 with IPs | 30 interfaces, 30 IPs | Match golden PPTX |
| REG-006 | Master Excel | Full data | Match golden Excel |
| REG-007 | Device Excel | Devices only | Match golden Excel |
| REG-008 | Mixed purposes | WAN/DMZ/LAN links | Correct colors |
| REG-009 | Port-channels | 5 port-channels | Correct display |
| REG-010 | Virtual ports | Vlan/Loopback | Correct in L2/L3 |

---

## 17. Tài liệu liên quan

- `docs/TEST_STRATEGY.md` - Chi tiết về golden files và regression testing
- `docs/DIAGRAM_STYLE_SPEC.md` - Màu sắc và style mapping
- `docs/TEMPLATE_SCHEMA.md` - Schema validation
- `docs/API_SPEC.md` - API endpoints mapping
