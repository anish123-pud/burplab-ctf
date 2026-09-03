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


class HintFlowTests(unittest.TestCase):
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

    def csrf_token(self):
        with self.client.session_transaction() as browser_session:
            return browser_session["csrf_token"]

    def test_seed_has_three_useful_hints_except_no_hint_capstone(self):
        with open_connection(self.database_path) as connection:
            rows = connection.execute(
                "SELECT id, hint_1, hint_2, hint_3 FROM challenges ORDER BY id"
            ).fetchall()

        self.assertEqual([row["id"] for row in rows], list(range(1, 14)))
        for row in rows[:12]:
            for column in ("hint_1", "hint_2", "hint_3"):
                hint = row[column]
                self.assertIsInstance(hint, str)
                self.assertGreaterEqual(len(hint.strip()), 20)
                self.assertNotIn("placeholder", hint.lower())

        self.assertIsNone(rows[12]["hint_1"])
        self.assertIsNone(rows[12]["hint_2"])
        self.assertIsNone(rows[12]["hint_3"])

    def test_ui_and_server_enforce_progressive_reveal_order(self):
        initial_page = self.client.get("/challenge/1")
        self.assertIn(b"Reveal hint 1", initial_page.data)
        self.assertIn(b"Hint 2 locked", initial_page.data)
        self.assertIn(b"Hint 3 locked", initial_page.data)
        self.assertNotIn(
            b"Open the lab request while your browser is using Burp Proxy.",
            initial_page.data,
        )

        locked = self.client.post(
            "/challenge/1/hint/2",
            json={"csrf_token": self.csrf_token()},
        )
        self.assertEqual(locked.status_code, 409)
        self.assertNotIn("hint", locked.get_json())
        self.assertEqual(locked.get_json()["highest_hint"], 0)

        first = self.client.post(
            "/challenge/1/hint/1",
            json={"csrf_token": locked.get_json()["csrf_token"]},
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()["hint_number"], 1)
        self.assertTrue(first.get_json()["newly_revealed"])
        self.assertIn("Burp Proxy", first.get_json()["hint"])

        page_after_first = self.client.get("/challenge/1")
        self.assertIn(b"Hint 1:", page_after_first.data)
        self.assertIn(b"Reveal hint 2", page_after_first.data)
        self.assertIn(b"Hint 3 locked", page_after_first.data)

        repeat_first = self.client.post(
            "/challenge/1/hint/1",
            json={"csrf_token": self.csrf_token()},
        )
        self.assertEqual(repeat_first.status_code, 200)
        self.assertFalse(repeat_first.get_json()["newly_revealed"])
        self.assertEqual(repeat_first.get_json()["highest_hint"], 1)

    def test_revealed_hint_level_drives_score_penalty(self):
        self.client.get("/challenge/1")
        first = self.client.post(
            "/challenge/1/hint/1",
            json={"csrf_token": self.csrf_token()},
        )
        second = self.client.post(
            "/challenge/1/hint/2",
            json={"csrf_token": first.get_json()["csrf_token"]},
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.get_json()["highest_hint"], 2)

        submission = self.client.post(
            "/challenge/1/submit",
            json={
                "csrf_token": second.get_json()["csrf_token"],
                "flag": "BLCTF{first_request}",
            },
        )
        self.assertEqual(submission.status_code, 200)
        self.assertEqual(submission.get_json()["points_awarded"], 75)
        self.assertEqual(submission.get_json()["hints_used"], 2)

        with open_connection(self.database_path) as connection:
            completion = connection.execute(
                """
                SELECT points_awarded, hints_used
                FROM challenge_completions
                WHERE user_id = 1 AND challenge_id = 1
                """
            ).fetchone()
        self.assertEqual(completion["points_awarded"], 75)
        self.assertEqual(completion["hints_used"], 2)

    def test_final_challenge_remains_the_no_hint_exception(self):
        challenge_page = self.client.get("/challenge/13")
        self.assertNotIn(b"Hints", challenge_page.data)

        response = self.client.post(
            "/challenge/13/hint/1",
            json={"csrf_token": self.csrf_token()},
        )
        self.assertEqual(response.status_code, 404)
        with open_connection(self.database_path) as connection:
            progress = connection.execute(
                """
                SELECT highest_hint
                FROM challenge_progress
                WHERE user_id = 1 AND challenge_id = 13
                """
            ).fetchone()
        self.assertIsNone(progress)


if __name__ == "__main__":
    unittest.main()
