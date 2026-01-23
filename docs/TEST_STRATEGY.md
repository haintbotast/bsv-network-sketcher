# Chiến lược kiểm thử

> **Phiên bản:** 1.1
> **Tạo:** 2026-01-23
> **Cập nhật:** 2026-01-23
> **Mục tiêu:** Quy định chiến lược kiểm thử và golden files.

## 1. Kiểm thử backend

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

## 4. Golden files & regression (bắt buộc)

**Mục tiêu:** đảm bảo đầu ra PPTX/Excel tương đương Network Sketcher gốc.

**Thiết lập:**
- Tạo bộ input chuẩn (small/medium/large) và output chuẩn (golden).
- Script so sánh: hash + kiểm tra cấu trúc slide/shape + bảng Excel.
- Ngưỡng chấp nhận: **không chênh lệch** về số lượng shape, vị trí, màu, text.

**Bộ dữ liệu đề xuất:**
- **Small:** ~10 devices, 10–20 links.
- **Medium:** ~100 devices, 150–200 links.
- **Large:** ~1000 devices, 1500+ links (chỉ dùng cho regression định kỳ).

**Quy trình:**
1) Chạy export từ web app.
2) So sánh với golden files.
3) Bất kỳ chênh lệch nào đều phải cập nhật spec hoặc sửa logic.

---

## 5. Thiết lập Golden Files Baseline (chi tiết)

### 5.1 Cấu trúc thư mục golden files

```
tests/
├── golden/
│   ├── inputs/                    # Dữ liệu đầu vào chuẩn
│   │   ├── small/
│   │   │   ├── project.json       # Template JSON đầy đủ
│   │   │   ├── areas.csv          # (tùy chọn) CSV input
│   │   │   └── devices.csv
│   │   ├── medium/
│   │   │   └── project.json
│   │   └── large/
│   │       └── project.json
│   ├── outputs/                   # Đầu ra chuẩn từ NS gốc
│   │   ├── small/
│   │   │   ├── l1_diagram.pptx    # Golden PPTX từ NS gốc
│   │   │   ├── l2_diagram.pptx
│   │   │   ├── l3_diagram.pptx
│   │   │   ├── device_file.xlsx   # Golden Excel từ NS gốc
│   │   │   └── master_file.xlsx
│   │   ├── medium/
│   │   │   └── ...
│   │   └── large/
│   │       └── ...
│   └── snapshots/                 # Extracted data từ golden files
│       ├── small/
│       │   ├── l1_shapes.json     # Số lượng, loại, vị trí shapes
│       │   ├── l1_colors.json     # Bảng màu sử dụng
│       │   └── l1_text.json       # Nội dung text labels
│       └── ...
```

### 5.2 Quy trình tạo golden files từ NS gốc

**Bước 1: Chuẩn bị môi trường NS gốc**

```bash
# Clone và cài đặt Network Sketcher gốc
git clone https://github.com/cisco-open/network-sketcher.git
cd network-sketcher
pip install -r requirements.txt
```

**Bước 2: Tạo dữ liệu input chuẩn**

```python
# scripts/create_golden_input.py
"""
Tạo bộ dữ liệu input chuẩn cho golden files.
Lưu ý: Dữ liệu phải đại diện cho các use case thực tế.
"""

SMALL_DATASET = {
    "areas": [
        {"name": "Core", "grid_row": 1, "grid_col": 1},
        {"name": "DMZ", "grid_row": 1, "grid_col": 2},
        {"name": "LAN", "grid_row": 2, "grid_col": 1},
    ],
    "devices": [
        {"name": "Core-SW-1", "area_name": "Core", "device_type": "Switch"},
        {"name": "Core-SW-2", "area_name": "Core", "device_type": "Switch"},
        {"name": "FW-1", "area_name": "DMZ", "device_type": "Firewall"},
        {"name": "Router-1", "area_name": "Core", "device_type": "Router"},
        {"name": "Access-SW-1", "area_name": "LAN", "device_type": "Switch"},
        {"name": "Access-SW-2", "area_name": "LAN", "device_type": "Switch"},
        {"name": "Server-1", "area_name": "LAN", "device_type": "Server"},
        {"name": "Server-2", "area_name": "LAN", "device_type": "Server"},
        {"name": "ISP-Router", "area_name": "DMZ", "device_type": "Router"},
        {"name": "DB-Server", "area_name": "LAN", "device_type": "Server"},
    ],
    "l1_links": [
        {"from_device": "Core-SW-1", "from_port": "Gi 0/1", "to_device": "Core-SW-2", "to_port": "Gi 0/1", "purpose": "LAN"},
        {"from_device": "Core-SW-1", "from_port": "Gi 0/2", "to_device": "FW-1", "to_port": "Gi 0/1", "purpose": "DMZ"},
        {"from_device": "FW-1", "from_port": "Gi 0/2", "to_device": "ISP-Router", "to_port": "Gi 0/1", "purpose": "WAN"},
        {"from_device": "Core-SW-1", "from_port": "Gi 0/3", "to_device": "Access-SW-1", "to_port": "Gi 0/1", "purpose": "LAN"},
        {"from_device": "Core-SW-2", "from_port": "Gi 0/2", "to_device": "Access-SW-2", "to_port": "Gi 0/1", "purpose": "LAN"},
        {"from_device": "Access-SW-1", "from_port": "Gi 0/2", "to_device": "Server-1", "to_port": "Eth 0", "purpose": "LAN"},
        {"from_device": "Access-SW-1", "from_port": "Gi 0/3", "to_device": "Server-2", "to_port": "Eth 0", "purpose": "LAN"},
        {"from_device": "Access-SW-2", "from_port": "Gi 0/2", "to_device": "DB-Server", "to_port": "Eth 0", "purpose": "LAN"},
        {"from_device": "Router-1", "from_port": "Gi 0/1", "to_device": "Core-SW-1", "to_port": "Gi 0/4", "purpose": "LAN"},
        {"from_device": "Router-1", "from_port": "Gi 0/2", "to_device": "Core-SW-2", "to_port": "Gi 0/3", "purpose": "LAN"},
    ],
    "l2_segments": [
        {"name": "VLAN10-Servers", "vlan_id": 10},
        {"name": "VLAN20-Users", "vlan_id": 20},
        {"name": "VLAN30-MGMT", "vlan_id": 30},
    ],
    "l3_addresses": [
        {"device_name": "Router-1", "interface_name": "Loopback 0", "ip_address": "10.0.0.1", "prefix_length": 32},
        {"device_name": "Core-SW-1", "interface_name": "Vlan 10", "ip_address": "10.10.10.1", "prefix_length": 24},
        {"device_name": "Core-SW-2", "interface_name": "Vlan 10", "ip_address": "10.10.10.2", "prefix_length": 24},
        {"device_name": "Server-1", "interface_name": "Eth 0", "ip_address": "10.10.10.11", "prefix_length": 24},
        {"device_name": "Server-2", "interface_name": "Eth 0", "ip_address": "10.10.10.12", "prefix_length": 24},
    ]
}
```

**Bước 3: Chạy NS gốc để sinh golden output**

```bash
# Chạy NS gốc với input chuẩn
cd network-sketcher
python ns_cli.py export l1_diagram --input ../tests/golden/inputs/small/
python ns_cli.py export l2_diagram --input ../tests/golden/inputs/small/
python ns_cli.py export l3_diagram --input ../tests/golden/inputs/small/
python ns_cli.py export device_file --input ../tests/golden/inputs/small/
python ns_cli.py export master_file --input ../tests/golden/inputs/small/

# Copy output sang thư mục golden
cp output/*.pptx ../tests/golden/outputs/small/
cp output/*.xlsx ../tests/golden/outputs/small/
```

**Bước 4: Trích xuất metadata để so sánh**

```python
# scripts/extract_golden_metadata.py
"""
Trích xuất metadata từ golden PPTX/Excel để so sánh tự động.
"""
from pptx import Presentation
from openpyxl import load_workbook
import json

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

# Usage
pptx_meta = extract_pptx_metadata("tests/golden/outputs/small/l1_diagram.pptx")
with open("tests/golden/snapshots/small/l1_shapes.json", "w") as f:
    json.dump(pptx_meta, f, indent=2, ensure_ascii=False)
```

### 5.3 Script so sánh regression

```python
# tests/test_golden_regression.py
import pytest
import json
from pathlib import Path
from scripts.extract_golden_metadata import extract_pptx_metadata, extract_excel_metadata

GOLDEN_DIR = Path("tests/golden")
TOLERANCE_POSITION = 0.05  # 0.05 inch tolerance cho vị trí

class TestGoldenRegression:
    """Kiểm thử regression so với golden files"""

    @pytest.fixture
    def small_golden_l1(self):
        with open(GOLDEN_DIR / "snapshots/small/l1_shapes.json") as f:
            return json.load(f)

    def test_l1_diagram_shape_count(self, small_golden_l1, generated_l1_pptx):
        """Kiểm tra số lượng shapes khớp"""
        generated = extract_pptx_metadata(generated_l1_pptx)

        assert len(generated["shapes"]) == len(small_golden_l1["shapes"]), \
            f"Shape count mismatch: {len(generated['shapes'])} vs {len(small_golden_l1['shapes'])}"

    def test_l1_diagram_text_content(self, small_golden_l1, generated_l1_pptx):
        """Kiểm tra nội dung text khớp"""
        generated = extract_pptx_metadata(generated_l1_pptx)

        golden_texts = set(small_golden_l1["text_content"])
        generated_texts = set(generated["text_content"])

        missing = golden_texts - generated_texts
        extra = generated_texts - golden_texts

        assert not missing, f"Missing text labels: {missing}"
        assert not extra, f"Extra text labels: {extra}"

    def test_l1_diagram_positions(self, small_golden_l1, generated_l1_pptx):
        """Kiểm tra vị trí shapes trong ngưỡng cho phép"""
        generated = extract_pptx_metadata(generated_l1_pptx)

        # Match shapes by text content
        golden_by_text = {s.get("text"): s for s in small_golden_l1["shapes"] if s.get("text")}

        for gen_shape in generated["shapes"]:
            if gen_shape.get("text") and gen_shape["text"] in golden_by_text:
                golden_shape = golden_by_text[gen_shape["text"]]

                dx = abs(gen_shape["left"] - golden_shape["left"])
                dy = abs(gen_shape["top"] - golden_shape["top"])

                assert dx <= TOLERANCE_POSITION, \
                    f"X position mismatch for '{gen_shape['text']}': {dx}"
                assert dy <= TOLERANCE_POSITION, \
                    f"Y position mismatch for '{gen_shape['text']}': {dy}"

    def test_l1_diagram_colors(self, small_golden_l1, generated_l1_pptx):
        """Kiểm tra màu sắc shapes khớp"""
        generated = extract_pptx_metadata(generated_l1_pptx)

        golden_by_text = {s.get("text"): s for s in small_golden_l1["shapes"] if s.get("text")}

        for gen_shape in generated["shapes"]:
            if gen_shape.get("text") and gen_shape["text"] in golden_by_text:
                golden_shape = golden_by_text[gen_shape["text"]]

                if "fill_color" in golden_shape:
                    assert gen_shape.get("fill_color") == golden_shape["fill_color"], \
                        f"Color mismatch for '{gen_shape['text']}'"

    def test_excel_structure(self, generated_master_xlsx):
        """Kiểm tra cấu trúc Excel khớp"""
        golden_meta = extract_excel_metadata(GOLDEN_DIR / "outputs/small/master_file.xlsx")
        generated_meta = extract_excel_metadata(generated_master_xlsx)

        assert generated_meta["sheet_names"] == golden_meta["sheet_names"], \
            "Sheet names mismatch"

        for sheet_name in golden_meta["sheet_names"]:
            assert generated_meta["sheets"][sheet_name]["headers"] == \
                   golden_meta["sheets"][sheet_name]["headers"], \
                f"Headers mismatch in sheet '{sheet_name}'"
```

### 5.4 Checklist thiết lập golden files

- [ ] Clone Network Sketcher gốc và cài đặt dependencies
- [ ] Tạo input dataset Small (10 devices, 10 links)
- [ ] Tạo input dataset Medium (100 devices, 150 links)
- [ ] Tạo input dataset Large (1000 devices, 1500 links)
- [ ] Chạy NS gốc sinh golden PPTX cho Small
- [ ] Chạy NS gốc sinh golden Excel cho Small
- [ ] Trích xuất metadata từ golden files
- [ ] Viết test regression cơ bản
- [ ] Tích hợp vào CI/CD pipeline

### 5.5 Ngưỡng chấp nhận

| Tiêu chí | Ngưỡng | Ghi chú |
|---------|--------|---------|
| Số lượng shapes | Exact match | Không chấp nhận chênh lệch |
| Nội dung text | Exact match | Không chấp nhận chênh lệch |
| Vị trí (x, y) | ± 0.05 inch | Cho phép sai số nhỏ |
| Kích thước (w, h) | ± 0.02 inch | Cho phép sai số nhỏ |
| Màu sắc | Exact match | RGB phải khớp hoàn toàn |
| Excel headers | Exact match | Tên cột phải khớp |
| Excel row count | Exact match | Số dòng dữ liệu phải khớp |

---

## 6. Tài liệu liên quan

- `docs/DIAGRAM_STYLE_SPEC.md`
- `docs/NS_REFERENCE.md`
- `docs/TEMPLATE_SCHEMA.md`
