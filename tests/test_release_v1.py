import re
import tempfile
import unittest
from contextlib import closing
from http.cookies import SimpleCookie
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class V1ReleaseAuditTests(unittest.TestCase):
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

    def tearDown(self):
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temporary_directory.cleanup()

    def authenticated_client(self, user_id=1):
        client = self.app.test_client()
        token = auth_module.create_session(user_id)
        with client.session_transaction() as browser_session:
            browser_session["auth_token"] = token
            browser_session["csrf_token"] = "release-audit-csrf-token"
        return client

    def flags_by_id(self):
        with closing(open_connection(self.database_path)) as connection:
            rows = connection.execute(
                "SELECT id, flag FROM challenges WHERE active = 1 ORDER BY id"
            ).fetchall()
        return {row["id"]: row["flag"] for row in rows}

    def test_all_intended_challenge_workflows_and_submission(self):
        flags = self.flags_by_id()
        client = self.authenticated_client()
        discovered = {}

        discovered[1] = client.get("/lab/first-request").headers["X-Lab-Flag"]
        discovered[2] = client.get("/lab/read-response/data").get_json()[
            "internal_note"
        ]
        discovered[3] = client.get("/product?id=3").headers["X-Lab-Flag"]
        discovered[4] = client.get("/product?id=42").headers["X-Lab-Flag"]

        cookie_start = client.get("/lab/cookies/start")
        cookie_jar = SimpleCookie()
        cookie_jar.load(cookie_start.headers["Set-Cookie"])
        cookie_value = cookie_jar["blctf_lab_session"].value
        discovered[5] = client.get(
            f"/lab/cookies/check?session_value={cookie_value}"
        ).headers["X-Lab-Flag"]

        discovered[6] = client.get(
            "/lab/headers",
            headers={"X-Lab-Debug": "enabled"},
        ).headers["X-Lab-Flag"]

        login_client = self.app.test_client()
        login_client.get("/register")
        with login_client.session_transaction() as browser_session:
            registration_csrf = browser_session["csrf_token"]
        registration = login_client.post(
            "/register",
            data={
                "csrf_token": registration_csrf,
                "username": "release_student",
                "email": "release-student@burplab.invalid",
                "password": "release-audit-password",
            },
        )
        self.assertEqual(registration.status_code, 302)
        login_client.get("/login")
        with login_client.session_transaction() as browser_session:
            login_csrf = browser_session["csrf_token"]
        login = login_client.post(
            "/login",
            data={
                "csrf_token": login_csrf,
                "username": "release_student",
                "password": "release-audit-password",
            },
        )
        self.assertEqual(login.status_code, 302)
        discovered[7] = login.headers["X-Lab-Login-Note"]

        discovered[8] = client.get("/challenge-orders/7002").get_json()["order"][
            "private_note"
        ]
        discovered[9] = client.get("/api/internal/debug").get_json()[
            "debug_token"
        ]
        discovered[10] = client.post(
            "/api/lab/profile",
            json={
                "display_name": "Fictional Learner",
                "theme": "dark",
                "lab_access": True,
            },
        ).get_json()["lab_reward"]
        discovered[11] = client.get("/lab/archive/retired-status").get_json()[
            "archive_key"
        ]

        ordinary_chain = client.get("/lab/chain/start?record=1")
        self.assertNotIn("Set-Cookie", ordinary_chain.headers)
        chain_start = client.get("/lab/chain/start?record=12")
        self.assertIn("blctf_chain_token=", chain_start.headers["Set-Cookie"])
        discovered[12] = client.get("/lab/chain/finish").get_json()["flag"]

        initial_capstone = client.get("/api/lab/capstone/audit?record=1301")
        self.assertEqual(
            initial_capstone.headers["X-Lab-Optional-Query"],
            "include_archived=true",
        )
        self.assertEqual(
            client.get("/api/lab/capstone/audit?record=1302").status_code,
            404,
        )
        self.assertEqual(
            client.get(
                "/api/lab/capstone/audit"
                "?record=1301&include_archived=true"
            ).status_code,
            404,
        )
        discovered[13] = client.get(
            "/api/lab/capstone/audit?record=1302&include_archived=true"
        ).get_json()["record"]["private_note"]

        self.assertEqual(discovered, flags)

        submission_csrf = "release-audit-csrf-token"
        for challenge_id, flag in discovered.items():
            with self.subTest(challenge_id=challenge_id):
                response = client.post(
                    f"/challenge/{challenge_id}/submit",
                    json={
                        "csrf_token": submission_csrf,
                        "flag": flag,
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()["status"], "correct")
                submission_csrf = response.get_json()["csrf_token"]

        with closing(open_connection(self.database_path)) as connection:
            completion = connection.execute(
                """
                SELECT COUNT(*) AS completed, SUM(points_awarded) AS score
                FROM challenge_completions
                WHERE user_id = 1
                """
            ).fetchone()
        self.assertEqual(completion["completed"], 13)
        self.assertEqual(completion["score"], 3050)

    def test_release_metadata_teaching_material_and_client_source(self):
        with closing(open_connection(self.database_path)) as connection:
            challenges = connection.execute(
                """
                SELECT id, flag, hint_1, hint_2, hint_3, points
                FROM challenges
                WHERE active = 1
                ORDER BY id
                """
            ).fetchall()
            emails = [
                row["email"]
                for row in connection.execute("SELECT email FROM users")
            ]

        self.assertEqual(len(challenges), 13)
        self.assertEqual(sum(row["points"] for row in challenges), 3050)
        flags = [row["flag"] for row in challenges]
        self.assertEqual(len(flags), len(set(flags)))
        self.assertTrue(
            all(flag.startswith("BLCTF{") and flag.endswith("}") for flag in flags)
        )
        for challenge in challenges[:12]:
            self.assertTrue(
                all(
                    challenge[f"hint_{number}"]
                    and "placeholder" not in challenge[f"hint_{number}"].lower()
                    for number in range(1, 4)
                )
            )
        self.assertTrue(
            all(challenges[12][f"hint_{number}"] is None for number in range(1, 4))
        )
        self.assertTrue(all(email.endswith(".invalid") for email in emails))

        client_source = b"".join(
            path.read_bytes()
            for root in (PROJECT_ROOT / "templates", PROJECT_ROOT / "static")
            for path in root.rglob("*")
            if path.is_file()
        )
        for flag in flags:
            self.assertNotIn(flag.encode(), client_source)
        self.assertNotIn(b"admin-lab-only", client_source)

        routed_source = b"".join(
            path.read_bytes()
            for root in (PROJECT_ROOT / "app", PROJECT_ROOT / "templates")
            for path in root.rglob("*")
            if path.is_file() and path.suffix in {".py", ".html"}
        )
        self.assertNotIn(b"instructor/", routed_source)

        student_guide = (PROJECT_ROOT / "student/student-guide.md").read_text(
            encoding="utf-8"
        )
        for flag in flags:
            self.assertNotIn(flag, student_guide)
        self.assertNotIn("admin-lab-only", student_guide)

        answer_key = (PROJECT_ROOT / "instructor/answer-key.md").read_text(
            encoding="utf-8"
        )
        for challenge_id in range(1, 14):
            self.assertRegex(answer_key, rf"(?m)^## {challenge_id}\. ")
        for section in (
            "Objective",
            "Intended vulnerability",
            "Starting state",
            "Expected workflow",
            "Flag",
            "Common mistakes",
            "Teaching notes",
        ):
            self.assertGreaterEqual(answer_key.count(f"### {section}"), 13)

    def test_fresh_unauthenticated_sweep_of_every_route(self):
        flags = [flag.encode() for flag in self.flags_by_id().values()]
        with closing(open_connection(self.database_path)) as connection:
            admin = connection.execute(
                """
                SELECT username, email, display_name, password_hash
                FROM users
                WHERE role = 'admin'
                """
            ).fetchone()

        forbidden = flags + [
            admin["username"].encode(),
            admin["email"].encode(),
            admin["display_name"].encode(),
            admin["password_hash"].encode(),
            b"admin-lab-only",
            b"BurpLab CTF Instructor Answer Key",
            b"BurpLab CTF Challenge Map",
            b"BurpLab CTF Reset Guide",
            b"Seeded credentials are",
        ]

        replacements = {
            "challenge_id": "1",
            "hint_number": "1",
            "order_id": "7001",
            "product_id": "1",
            "filename": "css/app.css",
        }

        def concrete_path(rule):
            return re.sub(
                r"<(?:(?:int|path):)?([^>]+)>",
                lambda match: replacements[match.group(1)],
                rule,
            )

        swept = []
        for rule in sorted(self.app.url_map.iter_rules(), key=lambda item: item.rule):
            path = concrete_path(rule.rule)
            for method in sorted(rule.methods & {"GET", "POST", "PUT", "PATCH", "DELETE"}):
                with self.subTest(path=path, method=method):
                    client = self.app.test_client()
                    response = client.open(path, method=method)
                    material = response.get_data() + b"\n".join(
                        f"{key}: {value}".encode()
                        for key, value in response.headers.items()
                    )
                    for secret in forbidden:
                        self.assertNotIn(secret, material)
                    swept.append((method, path))
                    response.close()

        self.assertGreaterEqual(len(swept), 40)
        self.assertFalse(
            any(
                "instructor" in rule.rule.lower()
                or "instructor" in rule.endpoint.lower()
                for rule in self.app.url_map.iter_rules()
            )
        )

        for hidden_path in (
            "/instructor",
            "/instructor/",
            "/instructor/answer-key.md",
            "/instructor/challenge-map.md",
            "/instructor/reset-guide.md",
            "/static/../instructor/answer-key.md",
            "/static/%2e%2e/instructor/answer-key.md",
        ):
            with self.subTest(hidden_path=hidden_path):
                response = self.app.test_client().get(hidden_path)
                self.assertEqual(response.status_code, 404)
                for secret in forbidden:
                    self.assertNotIn(secret, response.get_data())
                response.close()


if __name__ == "__main__":
    unittest.main()
