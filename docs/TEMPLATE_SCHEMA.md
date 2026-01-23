# Template Schema - Dữ liệu nhập liệu chuẩn

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-23  
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
    "created_at": "2026-01-23T00:00:00Z"
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

## 4. Ma trận kiểm tra hợp lệ (tối thiểu)

| Thực thể | Trường | Quy tắc | Mã lỗi |
|---------|--------|---------|-------|
| Area | name | Bắt buộc, duy nhất | `AREA_NAME_DUP` |
| Area | grid_row/grid_col | Số nguyên > 0 | `AREA_GRID_INVALID` |
| Device | name | Bắt buộc, duy nhất | `DEVICE_NAME_DUP` |
| Device | area_name | Phải tồn tại | `AREA_NOT_FOUND` |
| L1 Link | from_device/to_device | Phải tồn tại | `DEVICE_NOT_FOUND` |
| L1 Link | from_port/to_port | Định dạng có khoảng trắng | `PORT_FORMAT_INVALID` |
| L2 Segment | vlan_id | 1–4094 | `VLAN_INVALID` |
| L2 Assign | interface_name | Phải tồn tại | `INTERFACE_NOT_FOUND` |
| L3 Address | ip_address/prefix | IPv4 CIDR hợp lệ | `IP_INVALID` |

---

## 5. Format lỗi trả về (gợi ý)

```json
{
  "errors": [
    {"entity": "device", "row": 3, "field": "name", "code": "DEVICE_NAME_DUP", "message": "Trùng tên thiết bị"}
  ]
}
```

---

## 6. Tài liệu liên quan

- `docs/SRS.md`
- `docs/API_SPEC.md`
- `docs/DIAGRAM_STYLE_SPEC.md`
