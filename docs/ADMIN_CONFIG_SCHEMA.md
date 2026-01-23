# Admin Config Schema (tối giản)

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-23  
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
