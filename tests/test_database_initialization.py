import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app.database import get_connection
from app.database import initialize_db_if_needed


class DatabaseInitializationTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "burplab.db"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_initializes_when_database_file_is_absent(self):
        initialized = initialize_db_if_needed(self.database_path)

        self.assertTrue(initialized)
        with closing(get_connection(self.database_path)) as connection:
            users = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            challenges = connection.execute(
                "SELECT COUNT(*) FROM challenges"
            ).fetchone()[0]
        self.assertEqual(users, 4)
        self.assertEqual(challenges, 13)

    def test_initializes_when_sqlite_file_exists_without_tables(self):
        sqlite3.connect(self.database_path).close()

        initialized = initialize_db_if_needed(self.database_path)

        self.assertTrue(initialized)
        with closing(get_connection(self.database_path)) as connection:
            users_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'users'"
            ).fetchone()
        self.assertIsNotNone(users_table)

    def test_preserves_existing_data_when_users_table_exists(self):
        initialize_db_if_needed(self.database_path)
        with closing(get_connection(self.database_path)) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO users (username, password_hash, email, display_name)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        "persistent-user",
                        "test-password-hash",
                        "persistent-user@burplab.invalid",
                        "Persistent User",
                    ),
                )

        initialized = initialize_db_if_needed(self.database_path)

        self.assertFalse(initialized)
        with closing(get_connection(self.database_path)) as connection:
            persistent_user = connection.execute(
                "SELECT username FROM users WHERE username = ?",
                ("persistent-user",),
            ).fetchone()
            users = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        self.assertIsNotNone(persistent_user)
        self.assertEqual(users, 5)


if __name__ == "__main__":
    unittest.main()
