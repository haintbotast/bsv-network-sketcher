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

## 4. Regression testing

**Mục tiêu:** đảm bảo đầu ra PPTX/Excel đúng logic theo spec riêng của dự án.

> **Lưu ý:** Dự án không yêu cầu tương thích 1:1 với Network Sketcher gốc. Thay vào đó, tự định nghĩa expected output dựa trên `docs/DIAGRAM_STYLE_SPEC.md`.

**Thiết lập:**
- Tạo bộ input chuẩn (small/medium/large) trong `templates/samples/`.
- Khi có PPTX generator, tạo expected output samples làm baseline.
- Script so sánh: kiểm tra cấu trúc slide/shape + bảng Excel.

**Bộ dữ liệu:**
- **Small:** ~10 devices, 10–20 links → `templates/samples/small.json`
- **Medium:** ~100 devices, 150–200 links (tạo sau)
- **Large:** ~1000 devices, 1500+ links (chỉ dùng cho regression định kỳ)

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
- `schemas/template.json` - JSON Schema chính thức
- `templates/samples/` - Mẫu dữ liệu test
