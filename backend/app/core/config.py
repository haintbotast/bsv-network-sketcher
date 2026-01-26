import os
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/network_sketcher.db")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
EXPORTS_DIR = os.getenv("EXPORTS_DIR", "./exports")
ALLOW_SELF_REGISTER = os.getenv("ALLOW_SELF_REGISTER", "false").lower() == "true"

_frontend_urls = os.getenv("FRONTEND_URLS", "").split(",")
FRONTEND_URLS = [url.strip() for url in _frontend_urls if url.strip()]
if not FRONTEND_URLS:
    fallback = os.getenv("FRONTEND_URL", "")
    if fallback:
        FRONTEND_URLS = [fallback.strip()]
    else:
        FRONTEND_URLS = ["http://localhost:5173", "http://127.0.0.1:5173"]
