# Admin Config Schema (tối giản)

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-29  
> **Mục tiêu:** Chuẩn hóa cấu hình preset/layout/validation cho hệ thống, tránh hardcode.

---

## 1. Cấu trúc tổng thể

```json
{
  "config_version": "1.0",
  "layout": {
    "default_mode": "cisco",
    "allowed_modes": ["cisco", "iso", "custom"]
  },
  "layout_tuning": {
    "layer_gap": 1.4,
    "node_spacing": 0.7,
    "area_gap": 0.9,
    "area_padding": 0.3,
    "label_band": 0.45,
    "max_row_width_base": 12.0
  },
  "render_tuning": {
    "port_edge_inset": 6,
    "port_label_offset": 10,
    "bundle_gap": 14,
    "bundle_stub": 14,
    "area_clearance": 14,
    "area_anchor_offset": 12,
    "label_gap_x": 6,
    "label_gap_y": 4,
    "corridor_gap": 32
  },
  "style": {
    "themes": ["default", "contrast", "light", "dark"],
    "default_theme": "default",
    "presets": {
      "device_sizes": {"width": 1.2, "height": 0.5},
      "area_min_size": {"width": 3.0, "height": 1.5}
    }
  },
  "validation": {
    "port_name_requires_space": true,
    "vlan_range": [1, 4094],
    "ip_prefix_range": [1, 32],
    "layout_checks": {
      "area_padding": 0.15,
      "device_gap": 0.2,
      "label_gap": 0.05,
      "link_gap": 0.05,
      "overlap_epsilon": 0.01,
      "min_link_segment": 0.1
    }
  },
  "export": {
    "default_format": "pptx",
    "include_version_metadata": true
  }
}
```

---

## 2. Quy tắc cập nhật

- Mọi thay đổi config phải ghi audit log.
- Khi thay đổi `allowed_modes` hoặc `themes`, cần cập nhật UI chọn mode/theme.
- `config_version` tăng khi thay đổi schema.
- Khi thay đổi `validation.layout_checks`, cần cập nhật `docs/RULE_BASED_CHECKS.md` và test liên quan.

---

## 3. Tài liệu liên quan

- `docs/API_SPEC.md`
- `docs/DIAGRAM_STYLE_SPEC.md`
- `docs/TEMPLATE_SCHEMA.md`
- `docs/RULE_BASED_CHECKS.md`
