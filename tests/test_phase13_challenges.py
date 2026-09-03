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


class Phase13ChallengeTests(unittest.TestCase):
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

    def test_json_manipulation_is_confined_to_fictional_profile(self):
        normal = self.client.post(
            "/api/lab/profile",
            json={"display_name": "Fictional Learner", "theme": "light"},
        )
        self.assertEqual(normal.status_code, 200)
        self.assertNotIn("lab_reward", normal.get_json())

        unlocked = self.client.post(
            "/api/lab/profile",
            json={
                "display_name": "Fictional Learner",
                "theme": "light",
                "lab_access": True,
            },
        )
        self.assertEqual(
            unlocked.get_json()["lab_reward"],
            "BLCTF{unexpected_json_field}",
        )

        real_profile = self.client.post(
            "/api/profile",
            json={"lab_access": True},
        )
        self.assertEqual(real_profile.status_code, 400)
        with open_connection(self.database_path) as connection:
            role = connection.execute(
                "SELECT role FROM users WHERE id = 1"
            ).fetchone()["role"]
        self.assertEqual(role, "student")

    def test_hidden_endpoint_is_only_referenced_by_supporting_asset(self):
        challenge_page = self.client.get("/challenge/11")
        self.assertEqual(challenge_page.status_code, 200)
        self.assertNotIn(b"/lab/archive/retired-status", challenge_page.data)
        self.assertNotIn(b"BLCTF{", challenge_page.data)

        asset = self.client.get("/static/js/legacy-lab-reference.js")
        self.assertIn(b"/lab/archive/retired-status", asset.data)
        self.assertNotIn(b"BLCTF{", asset.data)
        asset.close()

        endpoint = self.client.get("/lab/archive/retired-status")
        self.assertEqual(
            endpoint.get_json()["archive_key"],
            "BLCTF{hidden_route_found}",
        )

    def test_multi_step_requires_parameter_then_user_bound_cookie(self):
        self.assertEqual(self.client.get("/lab/chain/finish").status_code, 403)

        ordinary = self.client.get("/lab/chain/start?record=1")
        self.assertEqual(ordinary.status_code, 200)
        self.assertNotIn("Set-Cookie", ordinary.headers)
        self.assertNotIn(b"BLCTF{", ordinary.data)

        handoff = self.client.get("/lab/chain/start?record=12")
        self.assertEqual(handoff.status_code, 200)
        self.assertIn("blctf_chain_token=", handoff.headers["Set-Cookie"])
        self.assertEqual(handoff.get_json()["next_path"], "/lab/chain/finish")
        self.assertNotIn(b"BLCTF{", handoff.data)

        chain_cookie = self.client.get_cookie(
            "blctf_chain_token",
            path="/lab/chain",
        )
        other_client = self.app.test_client()
        other_token = auth_module.create_session(2)
        with other_client.session_transaction() as browser_session:
            browser_session["auth_token"] = other_token
        other_client.set_cookie(
            "blctf_chain_token",
            chain_cookie.value,
            path="/lab/chain",
        )
        self.assertEqual(other_client.get("/lab/chain/finish").status_code, 403)

        finish = self.client.get("/lab/chain/finish")
        self.assertEqual(
            finish.get_json()["flag"],
            "BLCTF{chained_request_token}",
        )

    def test_real_order_routes_remain_scoped(self):
        html_orders = self.client.get("/orders")
        self.assertEqual(html_orders.status_code, 200)
        self.assertIn(b"Order #1", html_orders.data)
        self.assertNotIn(b"Order #2", html_orders.data)
        self.assertNotIn(b"7001", html_orders.data)
        self.assertNotIn(b"7002", html_orders.data)

        api_orders = self.client.get("/api/orders").get_json()["orders"]
        self.assertEqual([order["id"] for order in api_orders], [1])


if __name__ == "__main__":
    unittest.main()
