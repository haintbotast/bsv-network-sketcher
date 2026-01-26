"""Pydantic schemas cho BSV Network Sketcher."""

from app.schemas.auth import (
    Token,
    TokenData,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.schemas.area import (
    AreaCreate,
    AreaResponse,
    AreaUpdate,
    AreaStyle,
)
from app.schemas.device import (
    DeviceCreate,
    DeviceResponse,
    DeviceUpdate,
    DeviceBulkCreate,
    DeviceBulkResponse,
)
from app.schemas.link import (
    L1LinkCreate,
    L1LinkResponse,
    L1LinkUpdate,
    L1LinkBulkCreate,
    L1LinkBulkResponse,
)
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    BulkResultItem,
)
