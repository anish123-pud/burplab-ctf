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
from werkzeug.security import check_password_hash


class AdminAreaTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "burplab.db"
        recreate_db(self.database_path)

        def test_connection():
            return open_connection(self.database_path)

        self.patches = [
            patch.object(app_package, "migrate_db", lambda: None),
            patch.object(admin_module, "get_connection", test_connection),
            patch.object(api_module, "get_connection", test_connection),
            patch.object(auth_module, "get_connection", test_connection),
            patch.object(challenges_module, "get_connection", test_connection),
            patch.object(routes_module, "get_connection", test_connection),
        ]
        for active_patch in self.patches:
            active_patch.start()

        self.app = app_package.create_app()
        self.app.config.update(TESTING=True)

        with closing(open_connection(self.database_path)) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO challenge_progress (
                        user_id, challenge_id, attempts, highest_hint,
                        last_attempt_at
                    ) VALUES (1, 1, 3, 1, '2026-01-15 10:00:00')
                    """
                )
                connection.execute(
                    """
                    INSERT INTO challenge_completions (
                        user_id, challenge_id, completed_at, points_awarded,
                        hints_used, attempts
                    ) VALUES (1, 1, '2026-01-15 10:00:00', 90, 1, 3)
                    """
                )
                connection.execute(
                    """
                    INSERT INTO challenge_progress (
                        user_id, challenge_id, attempts, highest_hint,
                        last_attempt_at
                    ) VALUES (2, 2, 2, 2, '2026-01-15 11:00:00')
                    """
                )

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

    def test_seeded_admin_role_and_credentials(self):
        with closing(open_connection(self.database_path)) as connection:
            admin = connection.execute(
                """
                SELECT username, password_hash, role
                FROM users
                WHERE id = 4
                """
            ).fetchone()
        self.assertEqual(admin["username"], "admin01")
        self.assertEqual(admin["role"], "admin")
        self.assertTrue(
            check_password_hash(admin["password_hash"], "admin-lab-only")
        )

    def test_anonymous_student_and_instructor_cannot_access_admin(self):
        anonymous = self.app.test_client()
        self.assertEqual(anonymous.get("/admin").status_code, 404)
        self.assertEqual(anonymous.get("/admin/").status_code, 404)

        for user_id in (1, 2, 3):
            with self.subTest(user_id=user_id):
                client = self.client_for_user(user_id)
                self.assertEqual(client.get("/admin").status_code, 404)
                self.assertEqual(client.get("/admin/").status_code, 404)

                dashboard = client.get("/dashboard")
                self.assertEqual(dashboard.status_code, 200)
                self.assertNotIn(b'href="/admin/"', dashboard.data)

    def test_admin_navigation_and_dashboard_are_available(self):
        client = self.client_for_user(4)
        normal_dashboard = client.get("/dashboard")
        admin_dashboard = client.get("/admin/")

        self.assertIn(b'href="/admin/"', normal_dashboard.data)
        self.assertEqual(admin_dashboard.status_code, 200)
        self.assertIn(b"Admin Dashboard", admin_dashboard.data)
        self.assertIn(b"student01", admin_dashboard.data)
        self.assertIn(b"student02", admin_dashboard.data)
        self.assertNotIn(b"instructor01", admin_dashboard.data)
        self.assertNotIn(b"admin01@burplab.invalid", admin_dashboard.data)
        self.assertNotIn(b"password_hash", admin_dashboard.data)
        self.assertNotIn(b"BLCTF{", admin_dashboard.data)

    def test_dashboard_reports_progress_submissions_hints_and_scores(self):
        client = self.client_for_user(4)
        response = client.get("/admin/")
        page = response.data.decode()
        normalized_page = " ".join(page.split())

        self.assertIn("1 / 13", normalized_page)
        self.assertIn("0 / 13", normalized_page)
        self.assertIn("Submission Activity", page)
        self.assertIn("First Request", page)
        self.assertIn("Read the Response", page)
        self.assertIn("Completed", page)
        self.assertIn("Attempted", page)
        self.assertIn(">3<", page)
        self.assertIn(">2<", page)
        self.assertIn(">90<", page)

    def test_admin_dashboard_is_read_only(self):
        client = self.client_for_user(4)
        self.assertEqual(client.post("/admin/").status_code, 405)
        response = client.get("/admin/")
        self.assertNotIn(b"Delete", response.data)
        self.assertNotIn(b"Edit", response.data)
        self.assertIn(b'href="/admin/reset"', response.data)


if __name__ == "__main__":
    unittest.main()
