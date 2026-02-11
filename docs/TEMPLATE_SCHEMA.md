# Template Schema - Dữ liệu nhập liệu chuẩn

> **Phiên bản:** 1.3
> **Tạo:** 2026-01-23
> **Cập nhật:** 2026-02-09
> **Mục tiêu:** Chuẩn hóa schema template JSON, thứ tự phụ thuộc và validation.

---

## 1. Cấu trúc tổng thể

```json
{
  "schema_version": "1.0",
  "template_version": "1.0",
  "metadata": {
    "name": "Default Template",
    "description": "Template chuẩn",
    "created_at": "2026-01-23T00:00:00Z",
    "layout_mode": "standard"
  },
  "areas": [],
  "devices": [],
  "l1_links": [],
  "port_channels": [],
  "virtual_ports": [],
  "l2_segments": [],
  "interface_l2_assignments": [],
  "l3_addresses": []
}
```

---

## 2. Định nghĩa tối thiểu theo thực thể

### 2.0 Metadata
- `name` (string, required)
- `description` (string)
- `created_at` (date-time)
- `author` (string)
- `layout_mode` (standard, optional; nếu có sẽ gợi ý style chung cho project)

### 2.1 Areas
- `name` (string, unique, required)
- `grid_row`, `grid_col` (int > 0)
- `position_x`, `position_y`, `width`, `height` (float, inch)
- `style` (object)

### 2.2 Devices
- `name` (string, unique, required)
- `device_type` (string, theo preset)
- `area_name` (string, required, phải tồn tại)
- `position_x`, `position_y`, `width`, `height` (float, inch)
- `color_rgb` ([int,int,int])

Preset `device_type` hiện tại: `Router`, `Switch`, `Firewall`, `Server`, `AP`, `PC`, `Storage`, `Cloud`, `Cloud-Network`, `Cloud-Security`, `Cloud-Service`, `Unknown`.

### 2.3 L1 Links
- `from_device`, `to_device` (string, required)
- `from_port`, `to_port` (string, required)
- `purpose` (string, preset)

### 2.4 Port Channels
- `device_name` (string, required)
- `name` (string, required)
- `channel_number` (int)
- `mode` (LACP | static)
- `members` ([string])

### 2.5 Virtual Ports
- `device_name` (string, required)
- `name` (string, required)
- `interface_type` (Vlan | Loopback | Port-Channel)

### 2.6 L2 Segments
- `name` (string, required)
- `vlan_id` (int 1–4094)

### 2.7 Interface L2 Assignments
- `device_name` (string, required)
- `interface_name` (string, required)
- `l2_segment` (string, required)
- `port_mode` (access | trunk)

### 2.8 L3 Addresses
- `device_name` (string, required)
- `interface_name` (string, required)
- `ip_address` (IPv4)
- `prefix_length` (1–32)

---

## 3. Thứ tự phụ thuộc (bắt buộc)

1) Areas → 2) Devices → 3) L1 Links → 4) PortChannels → 5) VirtualPorts → 6) L2 Segments → 7) L2 Assignments → 8) L3 Addresses

---

## 4. Ma trận kiểm tra hợp lệ (mở rộng tối thiểu)

| Thực thể | Trường | Quy tắc | Mã lỗi |
|---------|--------|---------|-------|
| Area | name | Bắt buộc, duy nhất | `AREA_NAME_DUP` |
| Area | grid_row/grid_col | Số nguyên > 0 | `AREA_GRID_INVALID` |
| Area | width/height | > 0 | `AREA_SIZE_INVALID` |
| Device | name | Bắt buộc, duy nhất | `DEVICE_NAME_DUP` |
| Device | area_name | Phải tồn tại | `AREA_NOT_FOUND` |
| Device | device_type | Thuộc preset | `DEVICE_TYPE_INVALID` |
| Device | width/height | > 0 | `DEVICE_SIZE_INVALID` |
| L1 Link | from_device/to_device | Phải tồn tại | `DEVICE_NOT_FOUND` |
| L1 Link | from_port/to_port | Định dạng có khoảng trắng | `PORT_FORMAT_INVALID` |
| L1 Link | from/to | Không trùng cặp | `L1_LINK_DUP` |
| Port Channel | members | Không rỗng, cổng hợp lệ | `PORT_CHANNEL_MEMBERS_INVALID` |
| Port Channel | members | Không trùng lặp | `PORT_CHANNEL_MEMBER_DUP` |
| Virtual Port | interface_type | Thuộc tập cho phép | `VIRTUAL_PORT_TYPE_INVALID` |
| Virtual Port | name | Không dùng trong L1 links | `VIRTUAL_PORT_L1_FORBIDDEN` |
| L2 Segment | vlan_id | 1–4094 | `VLAN_INVALID` |
| L2 Assign | interface_name | Phải tồn tại | `INTERFACE_NOT_FOUND` |
| L2 Assign | port_mode | access/trunk | `PORT_MODE_INVALID` |
| L2 Assign | interface/l2 | Không vi phạm liên lớp | `L2_ASSIGNMENT_INVALID` |
| L3 Address | ip_address/prefix | IPv4 CIDR hợp lệ | `IP_INVALID` |
| L3 Address | interface_name | Phải tồn tại | `INTERFACE_NOT_FOUND` |
| L3 Address | interface | Không vi phạm liên lớp | `L3_ASSIGNMENT_INVALID` |

**Ghi chú:** Các kiểm tra hình học/bố cục (không chồng lấn, khoảng cách tối thiểu, nhãn không đè) tham chiếu `docs/RULE_BASED_CHECKS.md`.

---

## 5. Quy tắc chuẩn hóa dữ liệu

- Trim khoảng trắng đầu/cuối cho mọi chuỗi.
- Gộp nhiều khoảng trắng liên tiếp thành 1 khoảng trắng.
- Chuẩn hóa **port name** yêu cầu có khoảng trắng giữa loại và số (vd: `Gi 0/1`).
- `purpose`, `port_mode` chuẩn hóa uppercase trước khi map.
- So sánh trùng tên dựa trên chuỗi đã chuẩn hóa (trim + gộp khoảng trắng).

---

## 6. Ràng buộc liên lớp (bắt buộc)

- **L1 → L2:** chỉ cho phép gán L2 trên interface đã tồn tại (physical/virtual/port-channel).
- **L2 → L3:** IP chỉ gán trên interface đã tồn tại; không tự tạo interface mới ở L3.
- **Virtual ports:** chỉ tồn tại ở L2/L3; không xuất hiện trong L1 links.
- **Port-channel:** member ports phải tồn tại và thuộc cùng thiết bị; không cho member trùng lặp.

---

## 7. Giá trị mặc định

- `position_x`, `position_y`: mặc định theo layout tự động nếu thiếu.
- `width`, `height`: dùng preset trong `docs/DIAGRAM_STYLE_SPEC.md`.
- `device_type`: nếu thiếu, gán `Unknown`.
- `purpose`: nếu thiếu, gán `DEFAULT`.
- `port_mode`: mặc định `access` nếu không chỉ định.

---

## 8. Format lỗi trả về (gợi ý)

```json
{
  "errors": [
    {"entity": "device", "row": 3, "field": "name", "code": "DEVICE_NAME_DUP", "message": "Trùng tên thiết bị"}
  ]
}
```

---

---

## 9. JSON Schema chính thức (cho auto-validation)

### 9.1 Root Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://bsv.local/schemas/template.json",
  "title": "Network Sketcher Template",
  "description": "Schema chuẩn cho template dữ liệu nhập liệu",
  "type": "object",
  "required": ["schema_version", "template_version", "metadata"],
  "properties": {
    "schema_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+$",
      "description": "Phiên bản schema (vd: 1.0)"
    },
    "template_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+$",
      "description": "Phiên bản template"
    },
    "metadata": { "$ref": "#/$defs/metadata" },
    "areas": {
      "type": "array",
      "items": { "$ref": "#/$defs/area" },
      "default": []
    },
    "devices": {
      "type": "array",
      "items": { "$ref": "#/$defs/device" },
      "default": []
    },
    "l1_links": {
      "type": "array",
      "items": { "$ref": "#/$defs/l1_link" },
      "default": []
    },
    "port_channels": {
      "type": "array",
      "items": { "$ref": "#/$defs/port_channel" },
      "default": []
    },
    "virtual_ports": {
      "type": "array",
      "items": { "$ref": "#/$defs/virtual_port" },
      "default": []
    },
    "l2_segments": {
      "type": "array",
      "items": { "$ref": "#/$defs/l2_segment" },
      "default": []
    },
    "interface_l2_assignments": {
      "type": "array",
      "items": { "$ref": "#/$defs/interface_l2_assignment" },
      "default": []
    },
    "l3_addresses": {
      "type": "array",
      "items": { "$ref": "#/$defs/l3_address" },
      "default": []
    }
  },
  "$defs": {
    "metadata": {
      "type": "object",
      "required": ["name"],
      "properties": {
        "name": {
          "type": "string",
          "minLength": 1,
          "maxLength": 255
        },
        "description": {
          "type": "string",
          "maxLength": 1000
        },
        "created_at": {
          "type": "string",
          "format": "date-time"
        },
        "author": {
          "type": "string",
          "maxLength": 100
        },
        "layout_mode": {
          "type": "string",
          "enum": ["standard"],
          "description": "Gợi ý style chung cho project"
        }
      }
    },
    "area": {
      "type": "object",
      "required": ["name", "grid_row", "grid_col"],
      "properties": {
        "name": {
          "type": "string",
          "minLength": 1,
          "maxLength": 100,
          "pattern": "^[A-Za-z0-9_\\-\\s]+$"
        },
        "grid_row": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100
        },
        "grid_col": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100
        },
        "position_x": {
          "type": "number",
          "minimum": 0,
          "description": "Tọa độ X (inch)"
        },
        "position_y": {
          "type": "number",
          "minimum": 0,
          "description": "Tọa độ Y (inch)"
        },
        "width": {
          "type": "number",
          "minimum": 0.5,
          "maximum": 50,
          "default": 3.0
        },
        "height": {
          "type": "number",
          "minimum": 0.5,
          "maximum": 50,
          "default": 1.5
        },
        "style": {
          "$ref": "#/$defs/area_style"
        }
      }
    },
    "area_style": {
      "type": "object",
      "properties": {
        "fill_color_rgb": {
          "$ref": "#/$defs/rgb_color"
        },
        "stroke_color_rgb": {
          "$ref": "#/$defs/rgb_color"
        },
        "stroke_width": {
          "type": "number",
          "minimum": 0.5,
          "maximum": 5,
          "default": 1
        }
      }
    },
    "device": {
      "type": "object",
      "required": ["name", "area_name"],
      "properties": {
        "name": {
          "type": "string",
          "minLength": 1,
          "maxLength": 100,
          "pattern": "^[A-Za-z0-9_\\-\\s]+$"
        },
        "area_name": {
          "type": "string",
          "minLength": 1
        },
        "device_type": {
          "type": "string",
          "enum": ["Router", "Switch", "Firewall", "Server", "AP", "PC", "Storage", "Cloud", "Cloud-Network", "Cloud-Security", "Cloud-Service", "Unknown"],
          "default": "Unknown"
        },
        "position_x": {
          "type": "number",
          "minimum": 0
        },
        "position_y": {
          "type": "number",
          "minimum": 0
        },
        "width": {
          "type": "number",
          "minimum": 0.5,
          "maximum": 10,
          "default": 1.2
        },
        "height": {
          "type": "number",
          "minimum": 0.2,
          "maximum": 5,
          "default": 0.5
        },
        "color_rgb": {
          "$ref": "#/$defs/rgb_color"
        }
      }
    },
    "l1_link": {
      "type": "object",
      "required": ["from_device", "from_port", "to_device", "to_port"],
      "properties": {
        "from_device": {
          "type": "string",
          "minLength": 1
        },
        "from_port": {
          "type": "string",
          "minLength": 1,
          "pattern": "^[A-Za-z\\-]+\\s+.+$",
          "description": "Phải có khoảng trắng giữa loại và số (vd: Gi 0/1)"
        },
        "to_device": {
          "type": "string",
          "minLength": 1
        },
        "to_port": {
          "type": "string",
          "minLength": 1,
          "pattern": "^[A-Za-z\\-]+\\s+.+$"
        },
        "purpose": {
          "type": "string",
          "enum": ["WAN", "INTERNET", "DMZ", "LAN", "MGMT", "HA", "STORAGE", "BACKUP", "VPN", "DEFAULT"],
          "default": "DEFAULT"
        },
        "line_style": {
          "type": "string",
          "enum": ["solid", "dashed", "dotted"],
          "default": "solid"
        }
      }
    },
    "port_channel": {
      "type": "object",
      "required": ["device_name", "name", "members"],
      "properties": {
        "device_name": {
          "type": "string",
          "minLength": 1
        },
        "name": {
          "type": "string",
          "minLength": 1,
          "pattern": "^Port-[Cc]hannel\\s*\\d+$"
        },
        "channel_number": {
          "type": "integer",
          "minimum": 1,
          "maximum": 256
        },
        "mode": {
          "type": "string",
          "enum": ["LACP", "static"],
          "default": "LACP"
        },
        "members": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[A-Za-z\\-]+\\s+.+$"
          },
          "minItems": 1,
          "maxItems": 16
        }
      }
    },
    "virtual_port": {
      "type": "object",
      "required": ["device_name", "name", "interface_type"],
      "properties": {
        "device_name": {
          "type": "string",
          "minLength": 1
        },
        "name": {
          "type": "string",
          "minLength": 1,
          "pattern": "^(Vlan|Loopback|Port-[Cc]hannel)\\s*\\d+$"
        },
        "interface_type": {
          "type": "string",
          "enum": ["Vlan", "Loopback", "Port-Channel"]
        }
      }
    },
    "l2_segment": {
      "type": "object",
      "required": ["name", "vlan_id"],
      "properties": {
        "name": {
          "type": "string",
          "minLength": 1,
          "maxLength": 100
        },
        "vlan_id": {
          "type": "integer",
          "minimum": 1,
          "maximum": 4094
        },
        "description": {
          "type": "string",
          "maxLength": 255
        }
      }
    },
    "interface_l2_assignment": {
      "type": "object",
      "required": ["device_name", "interface_name", "l2_segment", "port_mode"],
      "properties": {
        "device_name": {
          "type": "string",
          "minLength": 1
        },
        "interface_name": {
          "type": "string",
          "minLength": 1
        },
        "l2_segment": {
          "type": "string",
          "minLength": 1
        },
        "port_mode": {
          "type": "string",
          "enum": ["access", "trunk"]
        },
        "native_vlan": {
          "type": "integer",
          "minimum": 1,
          "maximum": 4094,
          "description": "Chỉ áp dụng cho trunk"
        },
        "allowed_vlans": {
          "type": "array",
          "items": {
            "type": "integer",
            "minimum": 1,
            "maximum": 4094
          },
          "description": "Chỉ áp dụng cho trunk"
        }
      }
    },
    "l3_address": {
      "type": "object",
      "required": ["device_name", "interface_name", "ip_address", "prefix_length"],
      "properties": {
        "device_name": {
          "type": "string",
          "minLength": 1
        },
        "interface_name": {
          "type": "string",
          "minLength": 1
        },
        "ip_address": {
          "type": "string",
          "pattern": "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
          "description": "IPv4 address"
        },
        "prefix_length": {
          "type": "integer",
          "minimum": 1,
          "maximum": 32
        },
        "is_secondary": {
          "type": "boolean",
          "default": false
        },
        "description": {
          "type": "string",
          "maxLength": 255
        }
      }
    },
    "rgb_color": {
      "type": "array",
      "items": {
        "type": "integer",
        "minimum": 0,
        "maximum": 255
      },
      "minItems": 3,
      "maxItems": 3,
      "description": "[R, G, B]"
    }
  }
}
```

### 8.2 Ví dụ template hợp lệ

```json
{
  "schema_version": "1.0",
  "template_version": "1.0",
  "metadata": {
    "name": "Small Office Network",
    "description": "Template cho mạng văn phòng nhỏ",
    "created_at": "2026-01-23T10:00:00Z",
    "author": "admin"
  },
  "areas": [
    {
      "name": "Core",
      "grid_row": 1,
      "grid_col": 1,
      "width": 4.0,
      "height": 2.0
    },
    {
      "name": "Access",
      "grid_row": 2,
      "grid_col": 1,
      "width": 4.0,
      "height": 2.0
    }
  ],
  "devices": [
    {
      "name": "Core-SW-1",
      "area_name": "Core",
      "device_type": "Switch",
      "width": 1.2,
      "height": 0.5
    },
    {
      "name": "Access-SW-1",
      "area_name": "Access",
      "device_type": "Switch"
    },
    {
      "name": "Server-1",
      "area_name": "Access",
      "device_type": "Server"
    }
  ],
  "l1_links": [
    {
      "from_device": "Core-SW-1",
      "from_port": "Gi 0/1",
      "to_device": "Access-SW-1",
      "to_port": "Gi 0/1",
      "purpose": "LAN"
    },
    {
      "from_device": "Access-SW-1",
      "from_port": "Gi 0/2",
      "to_device": "Server-1",
      "to_port": "Eth 0",
      "purpose": "LAN"
    }
  ],
  "l2_segments": [
    {
      "name": "VLAN10-Servers",
      "vlan_id": 10,
      "description": "Server VLAN"
    }
  ],
  "interface_l2_assignments": [
    {
      "device_name": "Access-SW-1",
      "interface_name": "Gi 0/2",
      "l2_segment": "VLAN10-Servers",
      "port_mode": "access"
    }
  ],
  "l3_addresses": [
    {
      "device_name": "Core-SW-1",
      "interface_name": "Vlan 10",
      "ip_address": "10.10.10.1",
      "prefix_length": 24
    },
    {
      "device_name": "Server-1",
      "interface_name": "Eth 0",
      "ip_address": "10.10.10.11",
      "prefix_length": 24
    }
  ]
}
```

### 8.3 Sử dụng JSON Schema trong code

```python
# services/validation_service.py
import json
from jsonschema import Draft202012Validator, ValidationError
from pathlib import Path

class TemplateValidator:
    def __init__(self):
        schema_path = Path(__file__).parent.parent / "schemas" / "template.json"
        with open(schema_path) as f:
            self.schema = json.load(f)
        self.validator = Draft202012Validator(self.schema)

    def validate(self, template_data: dict) -> list[dict]:
        """
        Validate template data against JSON Schema.
        Returns list of validation errors.
        """
        errors = []
        for error in self.validator.iter_errors(template_data):
            errors.append({
                "path": "/".join(str(p) for p in error.absolute_path),
                "message": error.message,
                "schema_path": "/".join(str(p) for p in error.schema_path)
            })
        return errors

    def is_valid(self, template_data: dict) -> bool:
        """Quick check if template is valid"""
        return self.validator.is_valid(template_data)
```

### 8.4 Trường mới theo grid Excel + device ports (2026-02-09)

- `areas[].grid_range`:
  - Kiểu: `string`
  - Định dạng: `A1` hoặc `A1:B8`
  - Ý nghĩa: vùng tọa độ chuẩn theo lưới Excel; backend tự đồng bộ với `grid_row/grid_col/position_x/position_y/width/height`.
- `devices[].grid_range`:
  - Kiểu: `string`
  - Định dạng: `B10:F12`
  - Ý nghĩa: vị trí/kích thước chuẩn của thiết bị trên lưới logic.
- `device_ports[]` (khuyến nghị thêm vào template):
  - `device_name`: tên thiết bị sở hữu port.
  - `name`: tên port (vd: `Gi 0/1`, `Gi0/1`, `P1`).
  - `side`: `top|bottom|left|right`.
  - `offset_ratio`: `0..1` hoặc `null`.

Ví dụ:
```json
{
  "device_ports": [
    { "device_name": "Core-SW-1", "name": "Gi 0/1", "side": "top", "offset_ratio": null },
    { "device_name": "Core-SW-1", "name": "Gi 0/24", "side": "bottom", "offset_ratio": null }
  ]
}
```

---

## 9. Tài liệu liên quan

- `docs/SRS.md`
- `docs/API_SPEC.md`
- `docs/DIAGRAM_STYLE_SPEC.md`
- `docs/TEST_STRATEGY.md`
- `docs/RULE_BASED_CHECKS.md`
