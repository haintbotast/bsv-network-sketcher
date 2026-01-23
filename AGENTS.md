# Hướng dẫn AI (Bắt buộc)

Các hướng dẫn này áp dụng cho mọi công cụ AI lập trình (Codex, Claude Code, Cursor). Đọc file này trước khi thực hiện bất kỳ thay đổi nào.

## Thứ tự đọc
1) File này
2) WEB_APP_DEVELOPMENT_PLAN.md
3) Tài liệu khác do người dùng chỉ định

## Ngôn ngữ tài liệu (bắt buộc)
- Tất cả tài liệu/hướng dẫn trong repo phải viết bằng tiếng Việt có dấu.
- Nếu người dùng nhập không dấu, vẫn trả lời và cập nhật tài liệu bằng tiếng Việt có dấu.

## Ràng buộc dự án (ngăn xếp Option A)
- Backend: FastAPI async + SQLAlchemy 2.0 async.
- CSDL: SQLite + aiosqlite. UUID sinh ở tầng ứng dụng, lưu dạng TEXT. JSON lưu dạng TEXT.
- Job: worker nền dựa trên DB (poller) + ProcessPool cho tác vụ PPTX/Excel nặng.
- MVP không dùng Redis, Celery hoặc Docker.
- WebSocket: WebSocket gốc (không dùng Socket.IO).

## Quy ước Vue 3 + Konva.js
- Dùng `vue-konva` cho tích hợp chính; hạn chế thao tác DOM trực tiếp với Konva trừ khi bắt buộc.
- Tách mô hình dữ liệu (tọa độ logic) và mô hình hiển thị (tọa độ đã scale/zoom).
- Không tái tạo node Konva khi state đổi nhỏ; cập nhật thuộc tính và gọi `batchDraw()`.
- Tổ chức layer rõ ràng (tĩnh/động) để tối ưu hiệu năng; chỉ bật `draggable` khi cần.
- Áp dụng cắt giảm hiển thị/virtualization khi sơ đồ lớn (chỉ render phần đang thấy).
- Xử lý resize container để cập nhật kích thước `Stage` nhất quán.

## Nguồn tham chiếu
- WEB_APP_DEVELOPMENT_PLAN.md là nguồn chuẩn về kiến trúc và giai đoạn.
- Dự án tham chiếu repo gốc để đảm bảo logic tương đương:
  https://github.com/cisco-open/network-sketcher
  Dùng để đối chiếu logic nghiệp vụ và độ tương thích đầu ra.

## Kỷ luật thay đổi
- Chỉ thay đổi tối thiểu, có mục tiêu; tránh refactor không liên quan.
- Nếu yêu cầu mới xung đột với file này hoặc kế hoạch, hỏi người dùng và cập nhật cả hai.
- Khi người dùng cung cấp chỉ thị mới, cập nhật file này và các file hướng dẫn theo công cụ
  (CLAUDE.md, .cursor/rules/project.md) để đồng bộ.

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
