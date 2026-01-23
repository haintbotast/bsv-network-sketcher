# Phụ lục (tối giản)

> **Phiên bản:** 1.0  
> **Tạo:** 2026-01-23  
> **Cập nhật:** 2026-01-23  
> **Mục tiêu:** Lưu các thông tin phụ trợ tách khỏi plan tổng.

---

## A. Cấu trúc thư mục (tham chiếu)

```
network-sketcher-web/
|-- backend/
|-- frontend/
|-- scripts/
|-- docs/
`-- README.md
```

---

## B. Ví dụ phản hồi API

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Enterprise Network",
  "description": "Main corporate network topology",
  "theme": "default",
  "areas_count": 0,
  "devices_count": 0,
  "links_count": 0,
  "created_at": "2026-01-23T10:30:00Z",
  "updated_at": "2026-01-23T10:30:00Z"
}
```

---

## C. Thuật ngữ

| Term | Definition |
|------|------------|
| Area | Khu vực chứa thiết bị (Core, DMZ, User) |
| Device | Thiết bị mạng (router/switch/server/firewall) |
| Interface | Cổng vật lý/ảo trên thiết bị |
| L1 Link | Kết nối vật lý |
| L2 Segment | VLAN/Broadcast domain |
| L3 Address | IP trên interface |
| Port-Channel | Gộp nhiều cổng |
| Waypoint | Điểm bẻ hướng đường link |

---

## D. Tài liệu liên quan

- `WEB_APP_DEVELOPMENT_PLAN.md`
- `docs/NS_REFERENCE.md`
