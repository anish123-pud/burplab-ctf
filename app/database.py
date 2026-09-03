import sqlite3
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_PATH = DATABASE_DIR / "burplab.db"
SCHEMA_PATH = DATABASE_DIR / "schema.sql"
SEED_PATH = DATABASE_DIR / "seed.sql"


def get_connection(database_path: str | Path = DATABASE_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with row access and foreign keys enabled."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def migrate_db(database_path: str | Path = DATABASE_PATH) -> None:
    """Apply idempotent schema updates required by existing databases."""
    path = Path(database_path)
    if not path.exists():
        return

    with closing(get_connection(path)) as connection:
        users_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone()
        with connection:
            if users_table is not None:
                user_columns = {
                    row["name"]
                    for row in connection.execute("PRAGMA table_info(users)")
                }
                if "display_name" not in user_columns:
                    connection.execute(
                        """
                        ALTER TABLE users
                        ADD COLUMN display_name TEXT NOT NULL DEFAULT ''
                        """
                    )
                    connection.execute(
                        "UPDATE users SET display_name = username WHERE display_name = ''"
                    )

            challenges_table = connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table' AND name = 'challenges'
                """
            ).fetchone()
            if challenges_table is None:
                return

            challenge_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(challenges)")
            }
            if "flag" not in challenge_columns:
                connection.execute(
                    "ALTER TABLE challenges ADD COLUMN flag TEXT NOT NULL DEFAULT ''"
                )
            for hint_column in ("hint_1", "hint_2", "hint_3"):
                if hint_column not in challenge_columns:
                    connection.execute(
                        f"ALTER TABLE challenges ADD COLUMN {hint_column} TEXT"
                    )
            if "active" not in challenge_columns:
                connection.execute(
                    """
                    ALTER TABLE challenges
                    ADD COLUMN active INTEGER NOT NULL DEFAULT 1
                    CHECK (active IN (0, 1))
                    """
                )
                if "is_active" in challenge_columns:
                    connection.execute(
                        "UPDATE challenges SET active = is_active"
                    )
            connection.execute(
                """
                UPDATE challenges
                SET flag = 'BLCTF{placeholder_' || id || '}'
                WHERE flag = ''
                """
            )

            completions_table = connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table' AND name = 'challenge_completions'
                """
            ).fetchone()
            if completions_table is not None:
                completion_columns = {
                    row["name"]
                    for row in connection.execute(
                        "PRAGMA table_info(challenge_completions)"
                    )
                }
                if "points_awarded" not in completion_columns:
                    connection.execute(
                        """
                        ALTER TABLE challenge_completions
                        ADD COLUMN points_awarded INTEGER NOT NULL DEFAULT 0
                        CHECK (points_awarded >= 0)
                        """
                    )
                    connection.execute(
                        """
                        UPDATE challenge_completions
                        SET points_awarded = COALESCE(
                            (
                                SELECT points
                                FROM challenges
                                WHERE challenges.id = challenge_id
                            ),
                            0
                        )
                        """
                    )
                if "hints_used" not in completion_columns:
                    connection.execute(
                        """
                        ALTER TABLE challenge_completions
                        ADD COLUMN hints_used INTEGER NOT NULL DEFAULT 0
                        CHECK (hints_used BETWEEN 0 AND 3)
                        """
                    )
                if "attempts" not in completion_columns:
                    connection.execute(
                        """
                        ALTER TABLE challenge_completions
                        ADD COLUMN attempts INTEGER NOT NULL DEFAULT 1
                        CHECK (attempts > 0)
                        """
                    )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS challenge_progress (
                    user_id INTEGER NOT NULL,
                    challenge_id INTEGER NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
                    highest_hint INTEGER NOT NULL DEFAULT 0
                        CHECK (highest_hint BETWEEN 0 AND 3),
                    last_attempt_at TEXT,
                    PRIMARY KEY (user_id, challenge_id),
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (challenge_id) REFERENCES challenges (id)
                        ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS lab_products (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    price NUMERIC NOT NULL CHECK (price >= 0),
                    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS lab_cookie_tokens (
                    user_id INTEGER PRIMARY KEY,
                    token_digest TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS lab_order_accounts (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS lab_orders (
                    id INTEGER PRIMARY KEY,
                    account_id INTEGER NOT NULL,
                    item_name TEXT NOT NULL,
                    total_amount NUMERIC NOT NULL CHECK (total_amount >= 0),
                    private_note TEXT NOT NULL,
                    FOREIGN KEY (account_id) REFERENCES lab_order_accounts (id)
                        ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS lab_chain_tokens (
                    user_id INTEGER PRIMARY KEY,
                    token_digest TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS lab_final_records (
                    id INTEGER PRIMARY KEY,
                    fictional_owner TEXT NOT NULL,
                    archived INTEGER NOT NULL DEFAULT 0
                        CHECK (archived IN (0, 1)),
                    public_note TEXT NOT NULL,
                    private_note TEXT NOT NULL
                )
                """
            )


def init_db(database_path: str | Path = DATABASE_PATH) -> None:
    """Create the database tables from database/schema.sql."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with get_connection(path) as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def seed_db(database_path: str | Path = DATABASE_PATH) -> None:
    """Populate an initialized database from database/seed.sql."""
    with get_connection(database_path) as connection:
        connection.executescript(SEED_PATH.read_text(encoding="utf-8"))


def has_users_table(database_path: str | Path = DATABASE_PATH) -> bool:
    """Return whether the database contains the schema's sentinel table."""
    path = Path(database_path)
    if not path.is_file():
        return False

    with closing(get_connection(path)) as connection:
        users_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone()
    return users_table is not None


def recreate_db(database_path: str | Path = DATABASE_PATH) -> Path:
    """Remove an existing database, then initialize and seed a fresh one."""
    path = Path(database_path)
    path.unlink(missing_ok=True)
    init_db(path)
    seed_db(path)
    return path


def initialize_db_if_needed(database_path: str | Path = DATABASE_PATH) -> bool:
    """Initialize and seed only when the users table is missing.

    The database file alone is not a reliable initialization marker because
    SQLite creates it when an application opens a connection. The users table
    is part of every valid BurpLab schema, so it is used as the sentinel.
    """
    path = Path(database_path)
    if has_users_table(path):
        return False

    recreate_db(path)
    return True
