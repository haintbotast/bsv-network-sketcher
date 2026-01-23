# Đặc tả Bảo mật (Security Spec)

> **Phiên bản:** 1.0
> **Tạo:** 2026-01-23
> **Cập nhật:** 2026-01-23
> **Mục tiêu:** Định nghĩa các yêu cầu và cơ chế bảo mật cho ứng dụng web.

---

## 1. Phạm vi

- Ứng dụng nội bộ, không public internet.
- ~5 người dùng đồng thời.
- Bảo vệ dữ liệu dự án và kiểm soát truy cập.

---

## 2. Authentication (Xác thực)

### 2.1 Cơ chế JWT

```
┌──────────┐    credentials    ┌──────────┐
│  Client  │ ───────────────▶ │  Server  │
└──────────┘                   └──────────┘
                                    │
                                    ▼
                            ┌──────────────┐
                            │ Verify user  │
                            │ + hash check │
                            └──────────────┘
                                    │
     access_token + refresh_token   │
◀────────────────────────────────────
```

### 2.2 Token Configuration

| Tham số | Giá trị | Ghi chú |
|---------|---------|---------|
| Access Token TTL | 1 giờ (3600s) | Ngắn để giảm rủi ro |
| Refresh Token TTL | 7 ngày | Cho phép duy trì phiên |
| Algorithm | HS256 | HMAC-SHA256 |
| Secret Key Length | ≥ 256 bits | Sinh ngẫu nhiên |

### 2.3 JWT Payload Structure

```json
{
  "sub": "usr_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "user@example.com",
  "display_name": "Nguyễn Văn A",
  "iat": 1737619200,
  "exp": 1737622800,
  "jti": "tok_unique-token-id"
}
```

### 2.4 Token Refresh Flow

```
1. Client gửi refresh_token → POST /api/v1/auth/refresh
2. Server kiểm tra:
   - Token chưa hết hạn
   - Token chưa bị revoke (blacklist)
   - User vẫn active
3. Trả về access_token mới + refresh_token mới (rotation)
4. Revoke refresh_token cũ
```

### 2.5 Token Blacklist

```python
# models/token_blacklist.py
class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id = Column(String(36), primary_key=True)
    jti = Column(String(36), unique=True, nullable=False)
    token_type = Column(String(20))  # "access" | "refresh"
    user_id = Column(String(36), ForeignKey("users.id"))
    revoked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # Để cleanup định kỳ
```

---

## 3. Password Security

### 3.1 Hashing Algorithm

- **Algorithm:** bcrypt
- **Cost Factor:** 12 (2^12 iterations)
- **Salt:** Tự động sinh bởi bcrypt

```python
# services/auth_service.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

### 3.2 Password Policy

| Yêu cầu | Giá trị |
|---------|---------|
| Độ dài tối thiểu | 8 ký tự |
| Độ dài tối đa | 128 ký tự |
| Chữ hoa | ≥ 1 |
| Chữ thường | ≥ 1 |
| Số | ≥ 1 |
| Ký tự đặc biệt | Không bắt buộc (khuyến khích) |

```python
# services/validation_service.py
import re

PASSWORD_PATTERN = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,128}$'
)

def validate_password(password: str) -> tuple[bool, str | None]:
    if len(password) < 8:
        return False, "Mật khẩu phải có ít nhất 8 ký tự"
    if len(password) > 128:
        return False, "Mật khẩu không được quá 128 ký tự"
    if not PASSWORD_PATTERN.match(password):
        return False, "Mật khẩu phải có ít nhất 1 chữ hoa, 1 chữ thường và 1 số"
    return True, None
```

### 3.3 Password Change Flow

1. Yêu cầu xác thực mật khẩu hiện tại
2. Validate mật khẩu mới theo policy
3. Không cho phép dùng lại 3 mật khẩu gần nhất
4. Revoke tất cả tokens hiện tại sau khi đổi mật khẩu

---

## 4. Authorization (Phân quyền)

### 4.1 Mô hình quyền

```
┌─────────────────────────────────────────────────────────┐
│                      PROJECT                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │
│  │  Owner  │  │  Editor │  │  Viewer │  │  None   │   │
│  │ (CRUD+) │  │ (CRUD)  │  │  (R)    │  │  (-)    │   │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Ma trận quyền

| Hành động | Owner | Editor | Viewer | None |
|-----------|-------|--------|--------|------|
| Xem project | ✓ | ✓ | ✓ | ✗ |
| Sửa project metadata | ✓ | ✓ | ✗ | ✗ |
| Xóa project | ✓ | ✗ | ✗ | ✗ |
| Thêm/sửa/xóa devices | ✓ | ✓ | ✗ | ✗ |
| Thêm/sửa/xóa links | ✓ | ✓ | ✗ | ✗ |
| Export diagrams | ✓ | ✓ | ✓ | ✗ |
| Mời thành viên | ✓ | ✗ | ✗ | ✗ |
| Thay đổi quyền thành viên | ✓ | ✗ | ✗ | ✗ |

### 4.3 Project Membership Model

```python
# models/project_member.py
class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    role = Column(String(20), nullable=False)  # "owner" | "editor" | "viewer"
    invited_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('project_id', 'user_id', name='uq_project_user'),
    )
```

### 4.4 Permission Check

```python
# services/permission_service.py
from functools import wraps

class PermissionService:
    async def check_project_access(
        self,
        user_id: str,
        project_id: str,
        required_role: str = "viewer"
    ) -> bool:
        """
        Kiểm tra quyền truy cập project.
        required_role: "viewer" | "editor" | "owner"
        """
        member = await self.member_repo.get_by_user_and_project(
            user_id, project_id
        )
        if not member:
            return False

        role_hierarchy = {"viewer": 1, "editor": 2, "owner": 3}
        return role_hierarchy.get(member.role, 0) >= role_hierarchy.get(required_role, 0)

# Decorator for route protection
def require_project_role(role: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id and project_id from request
            # Check permission
            # Raise 403 if not authorized
            pass
        return wrapper
    return decorator
```

---

## 5. Input Validation & Sanitization

### 5.1 Nguyên tắc

- **Validate tại boundary:** Kiểm tra tất cả input từ client.
- **Whitelist:** Chỉ chấp nhận các giá trị cho phép.
- **Escape output:** Escape HTML/JS khi render.
- **Parameterized queries:** Không bao giờ string concat SQL.

### 5.2 Validation Rules

```python
# schemas/project.py
from pydantic import BaseModel, Field, validator
import re

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)

    @validator('name')
    def validate_name(cls, v):
        # Chỉ cho phép ký tự an toàn
        if not re.match(r'^[\w\s\-\.]+$', v, re.UNICODE):
            raise ValueError('Tên project chứa ký tự không hợp lệ')
        return v.strip()

class DeviceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    area_name: str = Field(..., min_length=1)
    device_type: str = Field(default="Unknown")

    @validator('name')
    def validate_device_name(cls, v):
        if not re.match(r'^[A-Za-z0-9_\-\s]+$', v):
            raise ValueError('Tên device chỉ được chứa chữ, số, dấu gạch ngang và gạch dưới')
        return v.strip()
```

### 5.3 SQL Injection Prevention

```python
# repositories/device_repo.py
from sqlalchemy import select, and_

class DeviceRepository:
    async def get_by_name(self, project_id: str, name: str) -> Device | None:
        # ĐÚNG: Dùng parameterized query
        stmt = select(Device).where(
            and_(
                Device.project_id == project_id,
                Device.name == name
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

        # SAI: Không bao giờ làm thế này
        # stmt = f"SELECT * FROM devices WHERE name = '{name}'"
```

### 5.4 Path Traversal Prevention

```python
# services/file_service.py
import os
from pathlib import Path

UPLOAD_DIR = Path("/app/uploads")
EXPORT_DIR = Path("/app/exports")

def safe_file_path(base_dir: Path, filename: str) -> Path:
    """
    Đảm bảo đường dẫn file nằm trong thư mục cho phép.
    Ngăn chặn path traversal attacks.
    """
    # Normalize và resolve path
    safe_name = os.path.basename(filename)  # Loại bỏ path components
    full_path = (base_dir / safe_name).resolve()

    # Kiểm tra path nằm trong base_dir
    if not str(full_path).startswith(str(base_dir.resolve())):
        raise ValueError("Invalid file path")

    return full_path
```

---

## 6. File Upload Security

### 6.1 Giới hạn Upload

| Tham số | Giá trị | Ghi chú |
|---------|---------|---------|
| Max file size | 10 MB | Đủ cho Excel/CSV lớn |
| Allowed extensions | .xlsx, .xls, .csv, .json | Whitelist |
| Allowed MIME types | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel, text/csv, application/json | Kiểm tra cả extension và MIME |

### 6.2 Upload Validation

```python
# services/upload_service.py
import magic
from pathlib import Path

ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.csv', '.json'}
ALLOWED_MIMES = {
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'text/csv',
    'application/json',
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

class UploadService:
    def validate_upload(self, file_content: bytes, filename: str) -> tuple[bool, str | None]:
        # Check size
        if len(file_content) > MAX_FILE_SIZE:
            return False, f"File quá lớn. Tối đa {MAX_FILE_SIZE // 1024 // 1024} MB"

        # Check extension
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"Loại file không được phép. Chấp nhận: {', '.join(ALLOWED_EXTENSIONS)}"

        # Check MIME type (magic bytes)
        mime = magic.from_buffer(file_content, mime=True)
        if mime not in ALLOWED_MIMES:
            return False, f"Nội dung file không khớp với extension"

        return True, None
```

---

## 7. Rate Limiting

### 7.1 Giới hạn theo endpoint

| Endpoint | Limit | Window | Ghi chú |
|----------|-------|--------|---------|
| POST /auth/login | 5 | 1 phút | Ngăn brute force |
| POST /auth/register | 3 | 1 phút | Ngăn spam đăng ký |
| POST /*/export/* | 10 | 1 phút | Tránh quá tải export |
| Các API khác | 100 | 1 phút | Giới hạn chung |

### 7.2 Implementation

```python
# middleware/rate_limit.py
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

class RateLimiter:
    def __init__(self):
        self._requests = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """
        Returns (is_allowed, retry_after_seconds)
        """
        async with self._lock:
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=window_seconds)

            # Clean old requests
            self._requests[key] = [
                t for t in self._requests[key] if t > window_start
            ]

            if len(self._requests[key]) >= limit:
                oldest = min(self._requests[key])
                retry_after = (oldest + timedelta(seconds=window_seconds) - now).seconds
                return False, retry_after

            self._requests[key].append(now)
            return True, 0
```

---

## 8. CORS Configuration

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware

# Chỉ cho phép origin từ frontend
ALLOWED_ORIGINS = [
    "http://localhost:5173",      # Dev frontend
    "http://192.168.1.100:5173",  # Internal network
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,  # Cache preflight 10 phút
)
```

---

## 9. Security Headers

```python
# middleware/security_headers.py
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS Protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (adjust as needed)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' ws: wss:;"
        )

        return response
```

---

## 10. Logging & Audit

### 10.1 Security Events to Log

| Event | Log Level | Data |
|-------|-----------|------|
| Login success | INFO | user_id, ip, user_agent |
| Login failed | WARNING | email, ip, reason |
| Password change | INFO | user_id, ip |
| Token refresh | DEBUG | user_id |
| Permission denied | WARNING | user_id, resource, action |
| Rate limit exceeded | WARNING | ip, endpoint |
| Invalid input | WARNING | endpoint, validation_errors |
| File upload | INFO | user_id, filename, size |
| Config change | INFO | user_id, config_scope, diff |
| Version restore | INFO | user_id, project_id, version_id |

### 10.2 Audit Log Model

```python
# models/audit_log.py
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), index=True)
    ip_address = Column(String(45))  # IPv6 support
    user_agent = Column(String(500))
    resource_type = Column(String(50))  # "project", "device", etc.
    resource_id = Column(String(36))
    action = Column(String(20))  # "create", "update", "delete"
    details = Column(Text)  # JSON string for additional data
    status = Column(String(20))  # "success", "failed"
```

---

## 11. Checklist triển khai bảo mật

**MVP nội bộ (tối giản):** vẫn bắt buộc có chính sách mật khẩu, kiểm tra input, phân quyền, audit log; các mục còn lại triển khai trước khi mở rộng production.

- [ ] Cấu hình JWT secret key mạnh (≥ 256 bits)
- [ ] Thiết lập bcrypt cost factor = 12
- [ ] Implement password policy validation
- [ ] Implement token blacklist
- [ ] Thiết lập rate limiting
- [ ] Cấu hình CORS whitelist
- [ ] Thêm security headers middleware
- [ ] Implement input validation cho tất cả endpoints
- [ ] Implement permission checks
- [ ] Cấu hình file upload validation
- [ ] Enable audit logging
- [ ] Review và test các security controls

---

## 12. Tài liệu liên quan

- `docs/API_SPEC.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `PROJECT_TOPOLOGY.md`
