import hashlib
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.database import get_connection


SESSION_LIFETIME = timedelta(hours=8)
USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,32}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,189}$")
# Sessions are server-side so they can be revoked immediately. The browser receives
# only a random bearer token; storing its digest in SQLite limits damage from a DB leak.
DUMMY_PASSWORD_HASH = (
    "pbkdf2:sha256:600000$QyfKFu4l0bLW0uhw$"
    "5be9b6cd87547957b6babd3e18b2fb9758f86f13f092dfec62bb84ffed9bb1ef"
)


class RegistrationError(ValueError):
    """Raised when submitted registration details are invalid or unavailable."""


def _utc_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _session_token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def register_user(username: str, password: str, email: str) -> int:
    """Validate and create a student account, returning its database ID."""
    normalized_username = username.strip().lower()
    normalized_email = email.strip().lower()

    if not USERNAME_PATTERN.fullmatch(normalized_username):
        raise RegistrationError(
            "Username must be 3–32 characters using lowercase letters, numbers, or underscores."
        )
    if len(normalized_email) > 254 or not EMAIL_PATTERN.fullmatch(normalized_email):
        raise RegistrationError("Enter a valid email address.")
    if len(password) < 12:
        raise RegistrationError("Password must be at least 12 characters.")
    if len(password) > 128:
        raise RegistrationError("Password must be no more than 128 characters.")

    password_hash = generate_password_hash(password)

    try:
        with closing(get_connection()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users (username, password_hash, email, display_name, role)
                    VALUES (?, ?, ?, ?, 'student')
                    """,
                    (
                        normalized_username,
                        password_hash,
                        normalized_email,
                        normalized_username,
                    ),
                )
                return int(cursor.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise RegistrationError("That username or email is already registered.") from exc


def authenticate_user(username: str, password: str) -> sqlite3.Row | None:
    """Return a user for valid credentials, otherwise return None."""
    normalized_username = username.strip().lower()

    with closing(get_connection()) as connection:
        user = connection.execute(
            """
            SELECT id, username, password_hash, email, role, created_at
            FROM users
            WHERE username = ?
            """,
            (normalized_username,),
        ).fetchone()

    # Checking a valid dummy hash reduces username-enumeration timing differences.
    password_hash = user["password_hash"] if user is not None else DUMMY_PASSWORD_HASH
    if not check_password_hash(password_hash, password):
        return None
    return user


def create_session(user_id: int) -> str:
    """Create a server-side session and return its unguessable bearer token."""
    token = secrets.token_urlsafe(32)
    token_digest = _session_token_digest(token)
    now = datetime.now(timezone.utc)
    expires_at = now + SESSION_LIFETIME

    with closing(get_connection()) as connection:
        with connection:
            connection.execute(
                "DELETE FROM sessions WHERE expires_at <= ?",
                (_utc_timestamp(now),),
            )
            connection.execute(
                """
                INSERT INTO sessions (user_id, token, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    token_digest,
                    _utc_timestamp(now),
                    _utc_timestamp(expires_at),
                ),
            )

    return token


def destroy_session(token: str) -> None:
    """Invalidate one server-side session token."""
    token_digest = _session_token_digest(token)
    with closing(get_connection()) as connection:
        with connection:
            connection.execute("DELETE FROM sessions WHERE token = ?", (token_digest,))


def get_user_for_session(token: str) -> sqlite3.Row | None:
    """Return the user attached to a valid, unexpired session token."""
    token_digest = _session_token_digest(token)
    now = _utc_timestamp(datetime.now(timezone.utc))

    with closing(get_connection()) as connection:
        return connection.execute(
            """
            SELECT
                users.id,
                users.username,
                users.email,
                users.display_name,
                users.role,
                users.created_at
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ? AND sessions.expires_at > ?
            """,
            (token_digest, now),
        ).fetchone()
