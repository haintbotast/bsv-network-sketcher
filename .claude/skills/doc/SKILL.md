---
name: doc
description: Tra cứu tài liệu dự án theo chủ đề. Dùng khi cần tham khảo API spec, kiến trúc, style, template schema, deploy guide...
argument-hint: "[chủ đề hoặc câu hỏi]"
context: fork
agent: Explore
---

Tra cứu tài liệu dự án BSV Network Sketcher theo chủ đề.

## Mapping chủ đề → file tài liệu

| Chủ đề | File | Mô tả |
|--------|------|-------|
| api | `docs/API_SPEC.md` | Đặc tả REST API và WebSocket |
| style | `docs/DIAGRAM_STYLE_SPEC.md` | Style sơ đồ, mapping UI/Konva/PPTX |
| template | `docs/TEMPLATE_SCHEMA.md` | Schema template và validation |
| deploy | `docs/DEPLOYMENT_GUIDE.md` | Hướng dẫn triển khai |
| test | `docs/TEST_STRATEGY.md` | Chiến lược kiểm thử |
| security | `docs/SECURITY_SPEC.md` | Bảo mật và audit |
| admin | `docs/ADMIN_CONFIG_SCHEMA.md` + `docs/ADMIN_UI_FLOW.md` | Cấu hình và UI admin |
| rules | `docs/RULE_BASED_CHECKS.md` | Rule-based checks |
| ns | `docs/NS_REFERENCE.md` | Tham chiếu logic NS gốc |
| arch | `PROJECT_TOPOLOGY.md` | Kiến trúc hệ thống |
| plan | `WEB_APP_DEVELOPMENT_PLAN.md` | Kế hoạch phát triển |
| brd | `docs/BRD.md` | Yêu cầu nghiệp vụ |
| prd | `docs/PRD.md` | Yêu cầu sản phẩm |
| srs | `docs/SRS.md` | Yêu cầu kỹ thuật |
| release | `docs/RELEASE_CHECKLIST.md` | Tiêu chí phát hành |
| index | `docs/DOCS_INDEX.md` | Mục lục tài liệu |

## Cách thực hiện

1. Xác định chủ đề từ `$ARGUMENTS`
2. Đọc file tài liệu tương ứng
3. Nếu argument là câu hỏi cụ thể (VD: "endpoint tạo device"), tìm và trích dẫn phần liên quan
4. Nếu argument là tên chủ đề đơn (VD: "api"), tóm tắt nội dung chính
5. Nếu không rõ chủ đề, đọc `docs/DOCS_INDEX.md` và gợi ý

## Ví dụ sử dụng

- `/doc api` → tóm tắt API endpoints
- `/doc template validation` → trích dẫn phần validation trong TEMPLATE_SCHEMA
- `/doc deploy rsync` → hướng dẫn rsync từ DEPLOYMENT_GUIDE
- `/doc style konva` → mapping Konva constants
