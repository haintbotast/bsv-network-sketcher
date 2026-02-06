---
name: test
description: Chạy backend unit tests. Dùng khi cần kiểm tra regression sau khi sửa code.
argument-hint: "[test_file hoặc test class]"
---

Chạy backend unit tests với đúng venv và working directory.

## Cấu hình

- **Venv**: `/opt/bsv-ns-deploy/backend/venv/bin/python3`
- **CWD**: phải `cd` vào `backend/` trước khi chạy (để `app` module resolve đúng)
- **Framework**: `unittest` (không có pytest trong venv)

## Cách chạy

### Có argument — chạy file/class cụ thể
```bash
cd /home/haint/Projects/bsv/bsv-network-sketcher/backend && \
  /opt/bsv-ns-deploy/backend/venv/bin/python3 -m unittest $ARGUMENTS -v
```

Ví dụ:
- `/test tests/test_topology_normalizer.py` → chạy 1 file
- `/test tests.test_device_sizing.TestEstimateBandWidthPx` → chạy 1 class

### Không argument — discover toàn bộ tests/
```bash
cd /home/haint/Projects/bsv/bsv-network-sketcher/backend && \
  /opt/bsv-ns-deploy/backend/venv/bin/python3 -m unittest discover -s tests -v
```

## Báo cáo

- Tổng số tests: passed / failed / errors
- Nếu có failure: trích dẫn traceback và gợi ý sửa

## Test files hiện có

- `tests/test_topology_normalizer.py` — classify_area_kind, device_compatible_with_area_kind
- `tests/test_device_sizing.py` — port band sizing, estimate_device_rendered_size
- `tests/test_layout_simple_layer.py` — simple_layer_layout algorithm
- `tests/test_layout_port_label_band.py` — port label band sizing
- `tests/test_port_anchor_override.py` — port anchor override logic
- `tests/test_link_validation.py` — link validation rules
- `tests/test_layout_l1_grid_macro.py` — grid macro layout
