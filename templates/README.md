# Mẫu dữ liệu (templates)

> **Mục tiêu:** Lưu các mẫu dữ liệu đầu vào để test nhanh và kiểm thử hồi quy.

---

## 1. Danh sách mẫu

- `templates/samples/minimal.json`: 1 area, 2 devices, 1 link (smoke test).
- `templates/samples/small.json`: ~10 devices, ~10 links (test cơ bản).
- `templates/samples/medium.json`: ~20 devices, ~27 links (test trung bình).
- `templates/samples/network_diagram_rebuild.json`: phục dựng sơ đồ từ `docs/Network diagram.pdf`.

---

## 2. Cách dùng

- Dùng để nhập liệu nhanh (import) hoặc chạy kiểm thử regression.
- Có thể dùng `scripts/validate_template.py` để kiểm tra hợp lệ theo schema.

---

## 3. Quy ước

- Mọi mẫu phải tuân theo `schemas/template.json`.
- Có thể khai báo `metadata.layout_mode = "standard"` để nhất quán style chung.
- Không đưa dữ liệu nhạy cảm vào mẫu.
