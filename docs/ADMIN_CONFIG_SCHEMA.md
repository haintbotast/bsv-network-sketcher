# Admin Config Schema (tối giản)

> **Phiên bản:** 1.1  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-02-11  
> **Mục tiêu:** Chuẩn hóa cấu hình preset/layout/validation cho hệ thống, tránh hardcode.

---

## 1. Cấu trúc tổng thể

```json
{
  "config_version": "1.0",
  "layout": {
    "default_mode": "standard",
    "allowed_modes": ["standard"]
  },
  "layout_tuning": {
    "layer_gap": 1.25,
    "node_spacing": 1.1,
    "port_label_band": 0.0,
    "area_gap": 0.9,
    "area_padding": 0.3,
    "label_band": 0.35,
    "max_row_width_base": 12.0,
    "max_nodes_per_row": 8,
    "row_gap": 0.9,
    "row_stagger": 0.5,
    "adaptive_area_gap_factor": 0.06,
    "adaptive_area_gap_cap": 0.8,
    "inter_area_gap_per_link": 0.04,
    "inter_area_gap_cap": 0.35
  },
  "render_tuning": {
    "port_edge_inset": 6,
    "port_label_offset": 18,
    "bundle_gap": 34,
    "bundle_stub": 42,
    "area_clearance": 36,
    "area_anchor_offset": 26,
    "label_gap_x": 8,
    "label_gap_y": 6,
    "corridor_gap": 64,
    "inter_area_links_per_channel": 4,
    "inter_area_max_channels": 4,
    "inter_area_occupancy_weight": 1.0,
    "icon_scale": 1.15,
    "icon_stroke_width": 1.5,
    "icon_min_size": 18,
    "icon_max_size": 32,
    "icon_color_default": "#4f4a44",
    "icon_colors": {
      "router": "#1f6feb",
      "security": "#b91c1c",
      "cloud-network": "#0369a1",
      "cloud-security": "#be123c",
      "cloud-service": "#2563eb"
    }
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
- Khi thay đổi `themes`, cần cập nhật UI chọn theme (không có chọn layout mode).
- `config_version` tăng khi thay đổi schema.
- Khi thay đổi `validation.layout_checks`, cần cập nhật `docs/RULE_BASED_CHECKS.md` và test liên quan.
- Khi thay đổi `render_tuning.icon_*`, cần cập nhật `docs/DIAGRAM_STYLE_SPEC.md` và test liên quan đến icon mapping/readability.

---

## 3. Tài liệu liên quan

- `docs/API_SPEC.md`
- `docs/DIAGRAM_STYLE_SPEC.md`
- `docs/TEMPLATE_SCHEMA.md`
- `docs/RULE_BASED_CHECKS.md`
