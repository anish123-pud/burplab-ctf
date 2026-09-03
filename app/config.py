import os
import secrets
from datetime import timedelta

from dotenv import load_dotenv


load_dotenv()


class Config:
    # A process-local random fallback avoids a predictable development secret.
    # Set SECRET_KEY in .env to keep browser sessions across server restarts.
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = os.getenv("DEBUG", "0").lower() in {"1", "true", "yes", "on"}
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Exposing the intentionally vulnerable lab to a LAN requires explicit opt-in.
    HOST = "0.0.0.0" if os.getenv("LAB_ALLOW_LAN") == "1" else "127.0.0.1"
