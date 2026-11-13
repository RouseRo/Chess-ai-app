import asyncio
import importlib.util
import io
import json
import os
import sqlite3
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

import httpx


spec = importlib.util.spec_from_file_location("admin_main", os.path.join(os.path.dirname(__file__), "..", "admin-service", "main.py"))
admin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(admin)

ROUTES = [
    ("GET", "/admin/stats"),
    ("GET", "/admin/models"),
    ("GET", "/admin/users"),
    ("GET", "/admin/users/player"),
    ("POST", "/admin/users/player/promote"),
    ("POST", "/admin/users/deputy/demote"),
    ("POST", "/admin/users/pending/verify"),
    ("DELETE", "/admin/users/player"),
]


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class AdminAuthTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        database = os.path.join(self.directory.name, "users.db")

        def connect():
            conn = sqlite3.connect(database)
            conn.row_factory = sqlite3.Row
            return conn

        self.connect = connect
        conn = connect()
        conn.execute("CREATE TABLE users (username TEXT, email TEXT, created_at TEXT, is_admin INTEGER, is_verified INTEGER, last_login TEXT, last_activity TEXT, current_activity TEXT)")
        conn.executemany("INSERT INTO users (username, email, created_at, is_admin, is_verified) VALUES (?, ?, 'now', ?, ?)", [
            ("boss", "boss@example.com", 1, 1), ("player", "player@example.com", 0, 1),
            ("pending", "pending@example.com", 0, 0), ("deputy", "deputy@example.com", 1, 1),
        ])
        conn.commit()
        conn.close()
        db_patch = patch.object(admin, "get_db_connection", connect)
        db_patch.start()
        self.addCleanup(db_patch.stop)
        # Tokens are "token-<username>"; the fake auth service echoes the username back.
        self.auth_patch = patch.object(admin.urllib.request, "urlopen", self.fake_auth)
        self.auth_patch.start()
        self.addCleanup(self.auth_patch.stop)

    def fake_auth(self, request, timeout=None):
        token = request.get_header("Authorization").removeprefix("Bearer ")
        if not token.startswith("token-"):
            return _Response(json.dumps({"success": False, "message": "Invalid or expired token."}).encode())
        return _Response(json.dumps({"success": True, "username": token.removeprefix("token-"), "is_admin": True}).encode())

    def call(self, method, path, token=None):
        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=admin.app), base_url="http://testserver") as client:
                headers = {"Authorization": f"Bearer {token}"} if token else {}
                return await client.request(method, path, headers=headers)
        return asyncio.run(send())

    def user(self, username):
        conn = self.connect()
        row = conn.execute("SELECT is_admin, is_verified FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        return tuple(row) if row else None

    def test_every_admin_route_rejects_requests_without_admin_sign_in(self):
        for method, path in ROUTES:
            with self.subTest(method=method, path=path):
                self.assertEqual(self.call(method, path).status_code, 401)
                self.assertEqual(self.call(method, path, "garbage").status_code, 401)
                self.assertEqual(self.call(method, path, "token-player").status_code, 403)
                self.assertEqual(self.call(method, path, "token-deleted").status_code, 403)
        self.assertEqual(self.user("player"), (0, 1))
        self.assertEqual(self.user("deputy"), (1, 1))
        self.assertEqual(self.user("pending"), (0, 0))

    def test_admin_can_use_every_route(self):
        for method, path in ROUTES:
            with self.subTest(method=method, path=path):
                self.assertEqual(self.call(method, path, "token-boss").status_code, 200)
        self.assertIsNone(self.user("player"))
        self.assertEqual(self.user("deputy"), (0, 1))
        self.assertEqual(self.user("pending"), (0, 1))

    # The fake auth service always claims is_admin, so this proves the users table decides.
    def test_demoted_admin_loses_access_despite_admin_claim_in_token(self):
        self.assertEqual(self.call("GET", "/admin/users", "token-boss").status_code, 200)
        conn = self.connect()
        conn.execute("UPDATE users SET is_admin = 0 WHERE username = 'boss'")
        conn.commit()
        conn.close()
        self.assertEqual(self.call("GET", "/admin/users", "token-boss").status_code, 403)

    def test_unreachable_auth_service_denies_access(self):
        with patch.object(admin.urllib.request, "urlopen", side_effect=urllib.error.URLError("down")):
            self.assertEqual(self.call("GET", "/admin/users", "token-boss").status_code, 503)
            self.assertEqual(self.call("DELETE", "/admin/users/player", "token-boss").status_code, 503)
        self.assertEqual(self.user("player"), (0, 1))

    def test_health_stays_public(self):
        self.assertEqual(self.call("GET", "/health").status_code, 200)


if __name__ == "__main__":
    unittest.main()
