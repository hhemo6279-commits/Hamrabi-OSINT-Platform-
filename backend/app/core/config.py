import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = BASE_DIR / "generated_reports"
REPORT_DIR.mkdir(exist_ok=True)
LEARNING_DIR = BASE_DIR

DATABASE_PATH = BASE_DIR / "hamrabi.db"

# --- security / env-driven config -------------------------------------------
# Override these with environment variables in production (see .env.example).
SECRET_KEY = os.getenv("HAMRABI_SECRET_KEY", "hamrabi-dev-secret-change-me")
ALGORITHM = os.getenv("HAMRABI_JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("HAMRABI_TOKEN_TTL_MIN", 60 * 12))

# Comma-separated list of allowed CORS origins; "*" only for local development.
CORS_ORIGINS = [o.strip() for o in os.getenv("HAMRABI_CORS_ORIGINS", "*").split(",")]

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}

REQUEST_TIMEOUT = 10

MAX_INVESTIGATIONS_PER_USER = 200