# Hướng dẫn AI (Bắt buộc)

Đọc file này trước khi thực hiện bất kỳ thay đổi nào. Các quy tắc này dùng chung với AGENTS.md và phải luôn đồng bộ.

## Thứ tự đọc
1) File này
2) AGENTS.md
3) PROJECT_TOPOLOGY.md
4) WEB_APP_DEVELOPMENT_PLAN.md
5) Tài liệu khác do người dùng chỉ định

## Ngôn ngữ tài liệu (bắt buộc)
- Tất cả tài liệu/hướng dẫn trong repo phải viết bằng tiếng Việt có dấu.
- Nếu người dùng nhập không dấu, vẫn trả lời và cập nhật tài liệu bằng tiếng Việt có dấu.

## Ràng buộc dự án (ngăn xếp Option A)
- Backend: FastAPI async + SQLAlchemy 2.0 async.
- CSDL: SQLite + aiosqlite. UUID sinh ở tầng ứng dụng, lưu dạng TEXT. JSON lưu dạng TEXT.
- Job: worker nền dựa trên DB (poller) + ProcessPool cho tác vụ PPTX/Excel nặng.
- MVP không dùng Redis, Celery hoặc Docker.
- WebSocket: WebSocket gốc (không dùng Socket.IO).
- Không triển khai CLI/CLI wrapper trong dự án web; CLI chỉ là nguồn tham chiếu logic từ repo gốc.

## Quy ước Vue 3 + Konva.js
- Dùng `vue-konva` cho tích hợp chính; hạn chế thao tác DOM trực tiếp với Konva trừ khi bắt buộc.
- Tách mô hình dữ liệu (tọa độ logic) và mô hình hiển thị (tọa độ đã scale/zoom).
- Không tái tạo node Konva khi state đổi nhỏ; cập nhật thuộc tính và gọi `batchDraw()`.
- Tổ chức layer rõ ràng (tĩnh/động) để tối ưu hiệu năng; chỉ bật `draggable` khi cần.
- Áp dụng cắt giảm hiển thị/virtualization khi sơ đồ lớn (chỉ render phần đang thấy).
- Xử lý resize container để cập nhật kích thước `Stage` nhất quán.

## Nguồn tham chiếu
- PROJECT_TOPOLOGY.md là nguồn chuẩn về topology hệ thống.
- WEB_APP_DEVELOPMENT_PLAN.md là nguồn chuẩn về kiến trúc và giai đoạn.
- `docs/BRD.md`, `docs/PRD.md`, `docs/SRS.md` là nguồn chuẩn về yêu cầu nghiệp vụ/sản phẩm/kỹ thuật.
- `docs/DIAGRAM_STYLE_SPEC.md` là nguồn chuẩn về style sơ đồ và mapping UI/Konva/PPTX.
- `docs/API_SPEC.md` là nguồn chuẩn về đặc tả API.
- `docs/TEMPLATE_SCHEMA.md` là nguồn chuẩn về schema template và validation.
- `docs/TEST_STRATEGY.md` là nguồn chuẩn về chiến lược kiểm thử.
- `docs/RELEASE_CHECKLIST.md` là nguồn chuẩn về tiêu chí chấp nhận và checklist phát hành.
- `docs/RULE_BASED_CHECKS.md` là nguồn chuẩn về rule-based checks.
- `docs/NS_REFERENCE.md` là nguồn chuẩn về tham chiếu logic NS gốc.
- `docs/DEPLOYMENT_GUIDE.md` là nguồn chuẩn về triển khai tối giản.
- `docs/APPENDIX.md` là nguồn chuẩn về phụ lục tham chiếu.
- `docs/ADMIN_CONFIG_SCHEMA.md` là nguồn chuẩn về cấu hình admin.
- `docs/ADMIN_UI_FLOW.md` là nguồn chuẩn về luồng UI quản trị.
- Dự án tham chiếu repo gốc để đảm bảo logic tương đương:
  https://github.com/cisco-open/network-sketcher
  Dùng để đối chiếu logic nghiệp vụ và độ tương thích đầu ra.

## Ràng buộc layout theo AI Context NS (bắt buộc)
- Nguồn gốc tham chiếu: `docs/[AI_Context]no_data.txt` (tiếng Anh); tóm tắt chuẩn tiếng Việt trong `docs/NS_REFERENCE.md`.
- Bố cục phân tầng **top‑to‑bottom**: Core/Distribution ở trên, Access ở giữa, Endpoints ở dưới; cha ở trên con.
- Dùng `_AIR_` để canh cột và giữ thẳng hàng.
- Auto‑layout theo **2 tầng**: macro (Area) + micro (thiết bị trong Area); không xếp xuyên Area.
- Overview chỉ L1 (hoặc flow); L2/L3 chỉ ở view riêng.
- Liên kết khác Area phải qua **Waypoint area** (đuôi `_wp_`).

## Kỷ luật thay đổi
- Chỉ thay đổi tối thiểu, có mục tiêu; tránh refactor không liên quan.
- Nếu yêu cầu mới xung đột với file này hoặc kế hoạch, hỏi người dùng và cập nhật cả hai.
- Khi người dùng cung cấp chỉ thị mới, cập nhật file này và các file hướng dẫn theo công cụ
  (AGENTS.md, .cursor/rules/project.md) để đồng bộ.
- Sau mỗi lần hoàn thành yêu cầu, **tự động commit/push** nếu không bị chặn; nếu không thể thì báo rõ lý do.
- Mọi thay đổi về topology/triển khai/luồng dữ liệu phải cập nhật PROJECT_TOPOLOGY.md.
- Mọi thay đổi về yêu cầu nghiệp vụ/sản phẩm/kỹ thuật phải cập nhật BRD/PRD/SRS tương ứng.
- Mọi thay đổi về hình khối/màu/nét/chữ phải cập nhật DIAGRAM_STYLE_SPEC.md.
- Mọi thay đổi về API hoặc schema template phải cập nhật API_SPEC/TEMPLATE_SCHEMA.
- Mọi thay đổi về kiểm thử phải cập nhật TEST_STRATEGY.md.
- Mọi thay đổi về rule-based checks phải cập nhật RULE_BASED_CHECKS.md.
- Mọi thay đổi về tiêu chí phát hành phải cập nhật RELEASE_CHECKLIST.md.
- Mọi thay đổi tham chiếu NS gốc phải cập nhật NS_REFERENCE.md.
- Mọi thay đổi về triển khai phải cập nhật DEPLOYMENT_GUIDE.md.
- Mọi thay đổi về cấu hình admin phải cập nhật ADMIN_CONFIG_SCHEMA.md/ADMIN_UI_FLOW.md.

## Biên soạn hướng dẫn (thực hành tốt)
- Giữ hướng dẫn ngắn gọn, tập trung, có kiểm soát phiên bản; coi file này là README cho tác tử.
- Đặt hướng dẫn vận hành cho tác tử ở đây (lệnh build/test, quy tắc style, ghi chú an ninh/triển khai) và giữ README cho người.
- Với Codex, dùng AGENTS.md (hoặc AGENTS.override.md) ở thư mục con để thu hẹp quy tắc; ưu tiên từ gốc đến sâu.
- Giữ chuỗi hướng dẫn Codex dưới project_doc_max_bytes (mặc định 32 KiB); tách theo thư mục nếu cần.
- Với Cursor, dùng .cursor/rules với globs và quy tắc lồng theo đường dẫn; quy tắc được chèn đầu ngữ cảnh nên phải thật ngắn.

## Kỳ vọng đầu ra
- Giữ phụ thuộc tối thiểu; giải thích khi thêm phụ thuộc mới.
- Cập nhật tài liệu khi thay đổi hành vi, API, lược đồ hoặc quy trình.
- Thêm/điều chỉnh kiểm thử khi thay đổi hành vi.
- Bảo toàn ngữ cảnh người dùng: trả lời và đầu ra ngắn gọn tối đa, tập trung.
- Không giải thích dài dòng trừ khi người dùng yêu cầu.
