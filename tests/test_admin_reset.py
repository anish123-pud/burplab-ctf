import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import app as app_package
import app.admin as admin_module
import app.api as api_module
import app.auth as auth_module
import app.challenges as challenges_module
import app.routes as routes_module
from app.database import get_connection as open_connection
from app.database import recreate_db


class AdminResetTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "burplab.db"
        recreate_db(self.database_path)

        def test_connection():
            return open_connection(self.database_path)

        def reset_test_database():
            return recreate_db(self.database_path)

        self.patches = [
            patch.object(app_package, "migrate_db", lambda: None),
            patch.object(admin_module, "get_connection", test_connection),
            patch.object(admin_module, "recreate_db", reset_test_database),
            patch.object(api_module, "get_connection", test_connection),
            patch.object(auth_module, "get_connection", test_connection),
            patch.object(challenges_module, "get_connection", test_connection),
            patch.object(routes_module, "get_connection", test_connection),
        ]
        for active_patch in self.patches:
            active_patch.start()

        self.app = app_package.create_app()
        self.app.config.update(TESTING=True)

    def tearDown(self):
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temporary_directory.cleanup()

    def client_for_user(self, user_id):
        client = self.app.test_client()
        token = auth_module.create_session(user_id)
        with client.session_transaction() as browser_session:
            browser_session["auth_token"] = token
        return client

    def add_non_seed_data(self):
        with closing(open_connection(self.database_path)) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO products (name, description, price, stock)
                    VALUES ('Temporary Reset Product', 'Removed by reset.', 1, 1)
                    """
                )
                connection.execute(
                    """
                    INSERT INTO orders (user_id, status, total_amount)
                    VALUES (1, 'pending', 1)
                    """
                )
                connection.execute(
                    """
                    INSERT INTO challenge_progress (
                        user_id, challenge_id, attempts, highest_hint,
                        last_attempt_at
                    ) VALUES (1, 1, 2, 1, '2026-01-20 10:00:00')
                    """
                )
                connection.execute(
                    """
                    INSERT INTO challenge_completions (
                        user_id, challenge_id, points_awarded, hints_used,
                        attempts
                    ) VALUES (1, 1, 90, 1, 2)
                    """
                )

    def test_reset_confirmation_page_and_exact_phrase(self):
        client = self.client_for_user(4)
        self.add_non_seed_data()

        confirmation_page = client.get("/admin/reset")
        self.assertEqual(confirmation_page.status_code, 200)
        self.assertIn(b"Confirm Lab Reset", confirmation_page.data)
        self.assertIn(b"Type RESET to confirm", confirmation_page.data)
        self.assertIn(b'name="csrf_token"', confirmation_page.data)
        self.assertIn(b'name="confirmation"', confirmation_page.data)

        with client.session_transaction() as browser_session:
            csrf_token = browser_session["csrf_token"]
        rejected = client.post(
            "/admin/reset",
            data={"csrf_token": csrf_token, "confirmation": "reset"},
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertIn(b"Type RESET exactly", rejected.data)

        with closing(open_connection(self.database_path)) as connection:
            temporary_product = connection.execute(
                "SELECT id FROM products WHERE name = 'Temporary Reset Product'"
            ).fetchone()
        self.assertIsNotNone(temporary_product)

    def test_successful_reset_restores_seed_logs_and_invalidates_sessions(self):
        client = self.client_for_user(4)
        self.add_non_seed_data()
        client.get("/admin/reset")
        with client.session_transaction() as browser_session:
            csrf_token = browser_session["csrf_token"]

        with self.assertLogs(self.app.logger.name, level="INFO") as captured_logs:
            response = client.post(
                "/admin/reset",
                data={"csrf_token": csrf_token, "confirmation": "RESET"},
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/login"))
        reset_logs = [line for line in captured_logs.output if "event=admin_reset" in line]
        self.assertEqual(len(reset_logs), 1)
        self.assertIn("actor_user_id=4", reset_logs[0])
        self.assertIn("occurred_at=", reset_logs[0])
        for sensitive_text in ("password", "token", "flag", "admin-lab-only"):
            self.assertNotIn(sensitive_text, reset_logs[0].lower())

        with closing(open_connection(self.database_path)) as connection:
            counts = {
                "users": connection.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                "products": connection.execute(
                    "SELECT COUNT(*) FROM products"
                ).fetchone()[0],
                "orders": connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
                "completions": connection.execute(
                    "SELECT COUNT(*) FROM challenge_completions"
                ).fetchone()[0],
                "progress": connection.execute(
                    "SELECT COUNT(*) FROM challenge_progress"
                ).fetchone()[0],
                "sessions": connection.execute(
                    "SELECT COUNT(*) FROM sessions"
                ).fetchone()[0],
            }
            temporary_product = connection.execute(
                "SELECT id FROM products WHERE name = 'Temporary Reset Product'"
            ).fetchone()

        self.assertEqual(
            counts,
            {
                "users": 4,
                "products": 3,
                "orders": 2,
                "completions": 0,
                "progress": 0,
                "sessions": 1,
            },
        )
        self.assertIsNone(temporary_product)
        self.assertEqual(client.get("/admin/").status_code, 404)

    def test_reset_is_repeatable_and_schema_remains_valid(self):
        for _ in range(2):
            client = self.client_for_user(4)
            client.get("/admin/reset")
            with client.session_transaction() as browser_session:
                csrf_token = browser_session["csrf_token"]
            response = client.post(
                "/admin/reset",
                data={"csrf_token": csrf_token, "confirmation": "RESET"},
            )
            self.assertEqual(response.status_code, 302)

            with closing(open_connection(self.database_path)) as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
                foreign_key_errors = connection.execute(
                    "PRAGMA foreign_key_check"
                ).fetchall()
                challenge_count = connection.execute(
                    "SELECT COUNT(*) FROM challenges"
                ).fetchone()[0]
            self.assertEqual(integrity, "ok")
            self.assertEqual(foreign_key_errors, [])
            self.assertEqual(challenge_count, 13)

    def test_non_admins_cannot_view_or_execute_reset(self):
        for user_id in (1, 2, 3):
            with self.subTest(user_id=user_id):
                client = self.client_for_user(user_id)
                self.assertEqual(client.get("/admin/reset").status_code, 404)
                self.assertEqual(
                    client.post(
                        "/admin/reset",
                        data={"confirmation": "RESET"},
                    ).status_code,
                    404,
                )
                self.assertNotIn(b"/admin/reset", client.get("/dashboard").data)


if __name__ == "__main__":
    unittest.main()
