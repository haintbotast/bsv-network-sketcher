# Schema dữ liệu (schemas)

> **Mục tiêu:** Lưu schema chính thức để validate dữ liệu đầu vào.

---

## 1. Danh sách schema

- `schemas/template.json`: JSON Schema chính thức cho dữ liệu nhập liệu (template).

---

## 2. Cách validate

- Dùng script: `scripts/validate_template.py <path>`.
- Script sử dụng JSON Schema Draft 2020-12.

---

## 3. Quy ước version

- `schema_version` và `template_version` phải theo định dạng `X.Y`.
- Mọi thay đổi schema cần cập nhật tài liệu liên quan.
