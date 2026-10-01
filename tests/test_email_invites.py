import asyncio
import importlib.util
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("auth_main", os.path.join(os.path.dirname(__file__), "..", "auth-service", "main.py"))
auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)


class EmailInviteTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        database = os.path.join(self.directory.name, "users.db")

        def connect():
            conn = sqlite3.connect(database)
            conn.row_factory = sqlite3.Row
            return conn

        self.connect = connect
        with connect() as conn:
            conn.execute("CREATE TABLE users (username TEXT, email TEXT, is_verified INTEGER, last_activity TEXT, current_activity TEXT)")
            conn.executemany("INSERT INTO users VALUES (?, ?, 1, NULL, 'offline')", [
                ("inviter", "inviter@example.com"), ("smtptest", "smtptest@example.com")
            ])
        db_patch = patch.object(auth, "get_db", connect)
        token_patch = patch.object(auth, "verify_jwt_token", return_value={"username": "inviter"})
        self.mail_patch = patch.object(auth, "_send_invite_email")
        self.mail = self.mail_patch.start()
        db_patch.start()
        token_patch.start()
        self.addCleanup(db_patch.stop)
        self.addCleanup(token_patch.stop)
        self.addCleanup(self.mail_patch.stop)

    def invite(self):
        return asyncio.run(auth.send_game_invite(auth.GameInviteRequest(recipient="smtptest"), "Bearer test"))

    def test_offline_invitation_is_emailed_and_persisted(self):
        preview = asyncio.run(auth.preview_game_invite("smtptest", "Bearer test"))
        self.assertTrue(preview["success"])
        self.assertIn("[Personal response link included when sent]", preview["body"])
        result = self.invite()
        self.assertTrue(result["emailed"])
        self.assertEqual(self.mail.call_args.args[0], "smtptest@example.com")
        self.assertIn("/invite.html?token=", self.mail.call_args.args[2])
        link = self.mail.call_args.args[2].split("Respond here within 30 days: ", 1)[1].strip()
        self.assertEqual(self.mail.call_args.args[2], preview["body"].replace("[Personal response link included when sent]", link))
        with self.connect() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM email_game_invites").fetchone()[0], 1)

    def test_failed_delivery_does_not_store_invitation(self):
        self.mail.side_effect = RuntimeError("SMTP unavailable")
        self.assertFalse(self.invite()["success"])
        with self.connect() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM email_game_invites").fetchone()[0], 0)

    def test_online_player_still_gets_in_app_invite(self):
        with self.connect() as conn:
            conn.execute("UPDATE users SET current_activity = 'online', last_activity = ? WHERE username = 'smtptest'",
                         (datetime.now(timezone.utc).isoformat(),))
        result = self.invite()
        self.assertTrue(result["success"])
        self.assertNotIn("emailed", result)
        self.mail.assert_not_called()

    def test_white_opening_response_and_replay(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        self.assertTrue(asyncio.run(auth.get_email_invite(token))["success"])
        response = auth.EmailInviteResponse(token=token, choice="white", first_move="e2e4")
        self.assertTrue(asyncio.run(auth.respond_to_email_invite(response))["success"])
        self.assertIn("My first move is e4", self.mail.call_args.args[2])
        self.assertFalse(asyncio.run(auth.respond_to_email_invite(response))["success"])
        with self.connect() as conn:
            row = conn.execute("SELECT recipient_color, first_move FROM email_game_invites").fetchone()
            self.assertEqual(tuple(row), ("white", "e4"))

    def test_black_and_invalid_opening(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        invalid = auth.EmailInviteResponse(token=token, choice="white", first_move="e5")
        self.assertFalse(asyncio.run(auth.respond_to_email_invite(invalid))["success"])
        self.assertTrue(asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token, choice="black")))["success"])
        self.assertIn("You play White", self.mail.call_args.args[2])

    def test_random_opening(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        with patch.object(auth.random, "choice", return_value=list(auth.chess.Board().legal_moves)[0]):
            result = asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token, choice="random")))
        self.assertTrue(result["success"])
        self.assertEqual(result["color"], "white")
        self.assertIsNotNone(result["first_move"])
        self.assertIn("Let the first move be chosen at random", self.mail.call_args.args[2])

    def test_expired_invitation_is_not_accepted(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        with self.connect() as conn:
            conn.execute("UPDATE email_game_invites SET expires_at = ?",
                         ((datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),))
        self.assertFalse(asyncio.run(auth.get_email_invite(token))["success"])
        self.assertFalse(asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token, choice="black")))["success"])
        self.mail.assert_called_once()


if __name__ == "__main__":
    unittest.main()