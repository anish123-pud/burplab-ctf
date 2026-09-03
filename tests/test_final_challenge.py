import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_package
import app.api as api_module
import app.auth as auth_module
import app.challenges as challenges_module
import app.routes as routes_module
from app.database import get_connection as open_connection
from app.database import recreate_db


class FinalChallengeTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "burplab.db"
        recreate_db(self.database_path)

        def test_connection():
            return open_connection(self.database_path)

        self.patches = [
            patch.object(app_package, "migrate_db", lambda: None),
            patch.object(api_module, "get_connection", test_connection),
            patch.object(auth_module, "get_connection", test_connection),
            patch.object(challenges_module, "get_connection", test_connection),
            patch.object(routes_module, "get_connection", test_connection),
        ]
        for active_patch in self.patches:
            active_patch.start()

        self.app = app_package.create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

        token = auth_module.create_session(1)
        with self.client.session_transaction() as browser_session:
            browser_session["auth_token"] = token

    def tearDown(self):
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temporary_directory.cleanup()

    def test_student_metadata_reveals_no_category_or_hints(self):
        expected_description = (
            "A flag has been hidden somewhere in this application. "
            "You have a normal student account and Burp Suite. Find it."
        )
        with open_connection(self.database_path) as connection:
            challenge = connection.execute(
                """
                SELECT description, category, hint_1, hint_2, hint_3
                FROM challenges
                WHERE id = 13
                """
            ).fetchone()
        self.assertEqual(challenge["description"], expected_description)
        self.assertEqual(challenge["category"], "mystery")
        self.assertIsNone(challenge["hint_1"])
        self.assertIsNone(challenge["hint_2"])
        self.assertIsNone(challenge["hint_3"])

        challenge_list = self.client.get("/challenges")
        challenge_page = self.client.get("/challenge/13")
        self.assertEqual(challenge_page.status_code, 200)
        self.assertIn(expected_description.encode(), challenge_page.data)
        self.assertNotIn(b"Mystery", challenge_list.data)
        self.assertNotIn(b"Mystery", challenge_page.data)
        self.assertNotIn(b"Application", challenge_page.data)
        self.assertNotIn(b"Hints", challenge_page.data)
        self.assertNotIn(b"Reveal hint", challenge_page.data)
        self.assertNotIn(b"BLCTF{", challenge_page.data)

        with self.client.session_transaction() as browser_session:
            csrf_token = browser_session["csrf_token"]
        hint_attempt = self.client.post(
            "/challenge/13",
            data={"csrf_token": csrf_token},
        )
        self.assertEqual(hint_attempt.status_code, 405)
        with open_connection(self.database_path) as connection:
            progress = connection.execute(
                """
                SELECT highest_hint
                FROM challenge_progress
                WHERE user_id = 1 AND challenge_id = 13
                """
            ).fetchone()
        self.assertIsNone(progress)

    def test_capstone_requires_discovery_parameter_and_record_chain(self):
        challenge_page = self.client.get("/challenge/13")
        self.assertIn(b"/static/js/capstone-audit.js", challenge_page.data)
        self.assertNotIn(b"include_archived", challenge_page.data)

        asset = self.client.get("/static/js/capstone-audit.js")
        self.assertIn(b"/api/lab/capstone/audit?record=1301", asset.data)
        self.assertNotIn(b"include_archived", asset.data)
        self.assertNotIn(b"BLCTF{", asset.data)
        asset.close()

        initial = self.client.get("/api/lab/capstone/audit?record=1301")
        self.assertEqual(initial.status_code, 200)
        self.assertEqual(
            initial.headers["X-Lab-Optional-Query"],
            "include_archived=true",
        )
        self.assertEqual(initial.get_json()["record"]["owner"], "alice")
        self.assertNotIn(b"BLCTF{", initial.data)

        id_only = self.client.get("/api/lab/capstone/audit?record=1302")
        parameter_only = self.client.get(
            "/api/lab/capstone/audit?record=1301&include_archived=true"
        )
        self.assertEqual(id_only.status_code, 404)
        self.assertEqual(parameter_only.status_code, 404)

        combined = self.client.get(
            "/api/lab/capstone/audit?record=1302&include_archived=true"
        )
        self.assertEqual(combined.status_code, 200)
        self.assertEqual(combined.get_json()["record"]["owner"], "bob")
        self.assertEqual(
            combined.get_json()["record"]["private_note"],
            "BLCTF{capstone_audit_bypass}",
        )

    def test_capstone_is_authenticated_and_real_routes_remain_isolated(self):
        anonymous_client = self.app.test_client()
        unauthorized = anonymous_client.get(
            "/api/lab/capstone/audit?record=1301"
        )
        self.assertEqual(unauthorized.status_code, 401)

        real_profile = self.client.post(
            "/api/profile",
            json={"include_archived": True},
        )
        self.assertEqual(real_profile.status_code, 400)

        html_orders = self.client.get("/orders")
        api_orders = self.client.get("/api/orders").get_json()["orders"]
        self.assertIn(b"Order #1", html_orders.data)
        self.assertNotIn(b"Order #2", html_orders.data)
        self.assertNotIn(b"1301", html_orders.data)
        self.assertNotIn(b"1302", html_orders.data)
        self.assertEqual([order["id"] for order in api_orders], [1])

    def test_correct_submission_scores_once_without_hint_penalty(self):
        self.client.get("/challenge/13")
        with self.client.session_transaction() as browser_session:
            csrf_token = browser_session["csrf_token"]
        first_submission = self.client.post(
            "/challenge/13/submit",
            data={
                "csrf_token": csrf_token,
                "flag": "BLCTF{capstone_audit_bypass}",
            },
        )
        self.assertEqual(first_submission.status_code, 302)

        self.client.get("/challenge/13")
        with self.client.session_transaction() as browser_session:
            csrf_token = browser_session["csrf_token"]
        second_submission = self.client.post(
            "/challenge/13/submit",
            data={
                "csrf_token": csrf_token,
                "flag": "BLCTF{capstone_audit_bypass}",
            },
        )
        self.assertEqual(second_submission.status_code, 302)

        with open_connection(self.database_path) as connection:
            completion = connection.execute(
                """
                SELECT COUNT(*) AS completion_count, points_awarded, hints_used
                FROM challenge_completions
                WHERE user_id = 1 AND challenge_id = 13
                """
            ).fetchone()
        self.assertEqual(completion["completion_count"], 1)
        self.assertEqual(completion["points_awarded"], 500)
        self.assertEqual(completion["hints_used"], 0)


if __name__ == "__main__":
    unittest.main()
