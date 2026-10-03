import asyncio
import importlib.util
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import httpx


spec = importlib.util.spec_from_file_location("auth_main", os.path.join(os.path.dirname(__file__), "..", "auth-service", "main.py"))
auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)
verify_token = auth.verify_jwt_token


class EmailInviteTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        database = os.path.join(self.directory.name, "users.db")
        connections = []

        def close_connections():
            for connection in connections:
                connection.close()

        self.addCleanup(close_connections)

        def connect():
            conn = sqlite3.connect(database)
            conn.row_factory = sqlite3.Row
            connections.append(conn)
            return conn

        self.connect = connect
        with connect() as conn:
            conn.execute("CREATE TABLE users (username TEXT, email TEXT, is_verified INTEGER, last_activity TEXT, current_activity TEXT, last_login TEXT, is_admin INTEGER DEFAULT 0)")
            conn.executemany("INSERT INTO users (username, email, is_verified, last_activity, current_activity, is_admin) VALUES (?, ?, 1, NULL, 'offline', 0)", [
                ("inviter", "inviter@example.com"), ("smtptest", "smtptest@example.com"),
                ("outsider", "outsider@example.com")
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
        self.assertIn("Accept invitation", preview["html_body"])
        self.assertIn(">Decline</a>", preview["html_body"])
        self.assertIn('href="#"', preview["html_body"])
        self.assertNotIn("decision=accept", preview["html_body"])
        result = self.invite()
        self.assertTrue(result["emailed"])
        self.assertEqual(self.mail.call_args.args[0], "smtptest@example.com")
        self.assertIn("/invite.html?token=", self.mail.call_args.args[2])
        self.assertIn("Accepted games are played by taking turns on a shared board.", self.mail.call_args.args[2])
        self.assertIn("You will receive an email when it is your turn.", self.mail.call_args.args[2])
        html_body = self.mail.call_args.args[3]
        self.assertIn('href="http://localhost:8080/invite.html?token=', html_body)
        self.assertIn("&amp;decision=accept", html_body)
        self.assertIn("&amp;decision=decline", html_body)
        self.assertIn("Accept invitation", html_body)
        self.assertIn(">Decline</a>", html_body)
        self.assertIn("confirm it on the invitation page", html_body)
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

    def test_acceptance_creates_one_persistent_game(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        response = auth.EmailInviteResponse(token=token, choice="white", first_move="e4")
        result = asyncio.run(auth.respond_to_email_invite(response))
        self.assertTrue(result["success"])
        self.assertFalse(asyncio.run(auth.respond_to_email_invite(response))["success"])
        with self.connect() as conn:
            game = conn.execute("SELECT * FROM email_games").fetchone()
            self.assertEqual(game["id"], result["game_id"])
            self.assertEqual(game["white_player"], "smtptest")
            self.assertEqual(game["current_player"], "inviter")
            self.assertEqual(game["version"], 1)
            board = auth.chess.Board()
            board.push_san("e4")
            self.assertEqual(game["fen"], board.fen())
            self.assertEqual(conn.execute("SELECT count(*) FROM email_games").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT status FROM email_game_invites").fetchone()[0], "accepted")

    def test_decline_is_recorded_without_game_even_if_email_fails(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        self.mail.side_effect = RuntimeError("SMTP unavailable")
        response = auth.EmailInviteResponse(token=token, decision="decline")
        result = asyncio.run(auth.respond_to_email_invite(response))
        self.assertTrue(result["success"])
        self.assertFalse(result["emailed"])
        self.assertIsNone(result["game_id"])
        self.assertFalse(asyncio.run(auth.respond_to_email_invite(response))["success"])
        with self.connect() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM email_games").fetchone()[0], 0)
            row = conn.execute("SELECT status, responded_at FROM email_game_invites").fetchone()
            self.assertEqual(row["status"], "declined")
            self.assertIsNotNone(row["responded_at"])

    def test_reading_invitation_does_not_consume_it(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        for _ in range(2):
            self.assertTrue(asyncio.run(auth.get_email_invite(token))["success"])
        with self.connect() as conn:
            self.assertEqual(conn.execute("SELECT status FROM email_game_invites").fetchone()[0], "pending")
            self.assertEqual(conn.execute("SELECT count(*) FROM email_games").fetchone()[0], 0)

    def test_game_access_checks_identity_and_membership(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        game_id = asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token)))["game_id"]
        for username in ("inviter", "smtptest"):
            with patch.object(auth, "verify_jwt_token", return_value={"username": username}):
                result = asyncio.run(auth.get_email_game(game_id, "Bearer test"))
                self.assertEqual(result["game"]["fen"], auth.chess.STARTING_FEN)
                self.assertEqual(result["game"]["current_player"], "inviter")
        for username in ("outsider", "deleted"):
            with patch.object(auth, "verify_jwt_token", return_value={"username": username}):
                with self.assertRaises(auth.HTTPException) as error:
                    asyncio.run(auth.get_email_game(game_id, "Bearer test"))
                self.assertEqual(error.exception.status_code, 404 if username == "outsider" else 401)
        for authorization in (None, "not-a-bearer"):
            with self.assertRaises(auth.HTTPException) as error:
                asyncio.run(auth.get_email_game(game_id, authorization))
            self.assertEqual(error.exception.status_code, 401)
        with patch.object(auth, "verify_jwt_token", return_value=None):
            with self.assertRaises(auth.HTTPException) as error:
                asyncio.run(auth.get_email_game(game_id, "Bearer expired"))
            self.assertEqual(error.exception.status_code, 401)

    def test_admin_listing_counts_declines_and_filters_games(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token, decision="decline")))
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token)))
        self.invite()
        with self.assertRaises(auth.HTTPException) as error:
            asyncio.run(auth.admin_email_games("Bearer test", None, 50, 0))
        self.assertEqual(error.exception.status_code, 403)
        with self.connect() as conn:
            conn.execute("UPDATE users SET is_admin = 1 WHERE username = 'inviter'")
        result = asyncio.run(auth.admin_email_games("Bearer test", None, 50, 0))
        self.assertEqual(result["invitation_stats"], {"pending": 1, "accepted": 1, "declined": 1, "expired": 0, "sent": 3})
        self.assertEqual(result["game_total"], 1)
        self.assertNotIn("token_hash", result["invitations"][0])
        self.assertGreaterEqual(result["games"][0]["waiting_seconds"], 0)
        filtered = asyncio.run(auth.admin_email_games("Bearer test", "declined", 1, 0))
        self.assertEqual(filtered["invitation_total"], 1)
        self.assertEqual(filtered["games"], [])
        self.assertEqual(filtered["invitations"][0]["status"], "declined")
        paged = asyncio.run(auth.admin_email_games("Bearer test", None, 1, 1))
        self.assertEqual(len(paged["invitations"]), 1)
        self.assertEqual(paged["invitation_total"], 3)
        with patch.object(auth, "verify_jwt_token", return_value={"username": "outsider"}):
            private = asyncio.run(auth.list_email_games("Bearer test", None, 50, 0))
        self.assertEqual(private["games"], [])
        self.assertEqual(private["invitation_stats"]["sent"], 0)

    def test_legacy_invitation_migration_and_expired_statistics(self):
        with self.connect() as conn:
            conn.execute("CREATE TABLE email_game_invites (id INTEGER PRIMARY KEY, sender TEXT, recipient TEXT, token_hash TEXT, created_at TEXT, expires_at TEXT, responded_at TEXT, recipient_color TEXT, first_move TEXT)")
            now = datetime.now(timezone.utc).isoformat()
            expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            conn.execute("INSERT INTO email_game_invites VALUES (1, 'inviter', 'smtptest', 'hash', ?, ?, ?, 'black', NULL)", (now, expired, now))
            conn.execute("INSERT INTO email_game_invites VALUES (2, 'inviter', 'smtptest', 'other', ?, ?, NULL, NULL, NULL)", (now, expired))
            auth._init_community_tables(conn)
            auth._init_community_tables(conn)
        result = asyncio.run(auth.list_email_games("Bearer test", None, 50, 0))
        self.assertEqual(result["invitation_stats"]["accepted"], 1)
        self.assertEqual(result["invitation_stats"]["expired"], 1)
        self.assertEqual(result["invitation_stats"]["pending"], 0)

    def test_legacy_completed_games_keep_unknown_outcome_after_migration(self):
        with self.connect() as conn:
            conn.execute("""CREATE TABLE email_game_invites (
                id INTEGER PRIMARY KEY, sender TEXT, recipient TEXT, token_hash TEXT,
                created_at TEXT, expires_at TEXT, responded_at TEXT, recipient_color TEXT,
                first_move TEXT, status TEXT DEFAULT 'accepted'
            )""")
            conn.execute("INSERT INTO email_game_invites VALUES (1, 'inviter', 'smtptest', 'hash', 'now', 'later', 'now', 'black', NULL, 'accepted')")
            conn.execute("""CREATE TABLE email_games (
                id INTEGER PRIMARY KEY, invitation_id INTEGER, white_player TEXT, black_player TEXT,
                status TEXT, fen TEXT, move_history TEXT, version INTEGER, current_player TEXT,
                created_at TEXT, turn_started_at TEXT, last_move_at TEXT, last_reminder_at TEXT
            )""")
            conn.execute(
                "INSERT INTO email_games VALUES (1, 1, 'inviter', 'smtptest', 'completed', ?, '[]', 0, 'inviter', 'now', 'now', NULL, NULL)",
                (auth.chess.STARTING_FEN,)
            )
            conn.execute("""CREATE TABLE email_outbox (
                id INTEGER PRIMARY KEY, recipient TEXT, subject TEXT, body TEXT,
                status TEXT, attempts INTEGER, next_attempt_at TEXT, claimed_until TEXT,
                last_error TEXT, created_at TEXT, sent_at TEXT
            )""")
            auth._init_community_tables(conn)
            game = conn.execute("SELECT result, winner, completion_reason, completed_at, draw_offer_by FROM email_games WHERE id = 1").fetchone()
            self.assertEqual(tuple(game), (None, None, None, None, None))
            outbox_columns = {row[1] for row in conn.execute("PRAGMA table_info(email_outbox)")}
            self.assertIn("game_id", outbox_columns)
            self.assertIn("notification_type", outbox_columns)

    def test_http_access_with_signed_tokens_and_pagination_validation(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]

        async def exercise_routes():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=auth.app), base_url="http://testserver") as client:
                response = await client.post("/community/email-invite/respond", json={"token": token, "choice": "black"})
                self.assertTrue(response.json()["success"])
                game_id = response.json()["game_id"]
                path = f"/community/email-games/{game_id}"
                self.assertEqual((await client.get(path)).status_code, 401)
                self.assertEqual((await client.get(path, headers={"Authorization": "Bearer invalid"})).status_code, 401)
                headers = {"Authorization": "Bearer " + auth.create_token("smtptest", False)}
                self.assertEqual((await client.get(path, headers=headers)).json()["game"]["black_player"], "smtptest")
                self.assertEqual((await client.get("/community/email-games?limit=0", headers=headers)).status_code, 422)
                self.assertEqual((await client.get("/community/email-games?offset=-1", headers=headers)).status_code, 422)
                self.assertEqual((await client.get("/community/email-games?status=unknown", headers=headers)).status_code, 400)
                forged_role = {"Authorization": "Bearer " + auth.create_token("outsider", True)}
                self.assertEqual((await client.get(path, headers=forged_role)).status_code, 404)
                self.assertEqual((await client.get("/community/admin/email-games", headers=forged_role)).status_code, 403)
                with self.connect() as conn:
                    conn.execute("UPDATE users SET is_admin = 1 WHERE username = 'inviter'")
                admin_headers = {"Authorization": "Bearer " + auth.create_token("inviter", True)}
                listing = await client.get("/community/admin/email-games?status=active", headers=admin_headers)
                self.assertEqual(listing.status_code, 200)
                self.assertEqual(listing.json()["game_total"], 1)

        with patch.object(auth, "verify_jwt_token", wraps=verify_token):
            asyncio.run(exercise_routes())

    def test_http_milestone_move_reminder_and_magic_link_routes(self):
        self.invite()
        invite_token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        game_id = asyncio.run(auth.respond_to_email_invite(
            auth.EmailInviteResponse(token=invite_token)
        ))["game_id"]

        async def exercise_routes():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=auth.app), base_url="http://testserver") as client:
                inviter_headers = {"Authorization": "Bearer " + auth.create_token("inviter", False)}
                opponent_headers = {"Authorization": "Bearer " + auth.create_token("smtptest", False)}
                move_url = f"/community/email-games/{game_id}/moves"
                moved = await client.post(move_url, headers=inviter_headers,
                                          json={"move": "e2e4", "expected_version": 0})
                self.assertEqual(moved.status_code, 200)
                self.assertEqual(moved.json()["game"]["version"], 1)
                stale = await client.post(move_url, headers=opponent_headers,
                                          json={"move": "e2e4", "expected_version": 0})
                self.assertEqual(stale.status_code, 409)

                reminder_url = f"/community/email-games/{game_id}/remind"
                reminder = await client.post(reminder_url, headers=inviter_headers)
                self.assertEqual(reminder.status_code, 200)
                throttled = await client.post(reminder_url, headers=inviter_headers)
                self.assertEqual(throttled.status_code, 429)

                request_link = await client.post("/auth/email-game-link", json={"email": "smtptest@example.com"})
                self.assertEqual(request_link.status_code, 200)
                with self.connect() as conn:
                    body = conn.execute(
                        "SELECT body FROM email_outbox WHERE subject = 'Your Chess AI sign-in link'"
                    ).fetchone()[0]
                magic_token = body.split("magic_token=", 1)[1].splitlines()[0]
                consumed = await client.post("/auth/email-game-link/consume", json={"token": magic_token})
                self.assertEqual(consumed.status_code, 200)
                magic_headers = {"Authorization": "Bearer " + consumed.json()["token"]}
                game = await client.get(f"/community/email-games/{game_id}", headers=magic_headers)
                self.assertEqual(game.status_code, 200)
                self.assertEqual(game.json()["game"]["current_player"], "smtptest")

        with patch.object(auth, "verify_jwt_token", wraps=verify_token):
            asyncio.run(exercise_routes())

    def test_acceptance_survives_notification_failure(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        self.mail.side_effect = RuntimeError("SMTP unavailable")
        result = asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token)))
        self.assertTrue(result["success"])
        self.assertFalse(result["emailed"])
        game = asyncio.run(auth.get_email_game(result["game_id"], "Bearer test"))["game"]
        self.assertEqual(game["current_player"], "inviter")
        self.assertEqual(game["move_history"], [])

    def test_legal_move_persists_and_advances_turn(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        game_id = asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token)))['game_id']

        result = asyncio.run(auth.submit_email_game_move(
            game_id, auth.EmailGameMoveRequest(move="e2e4", expected_version=0), "Bearer test"
        ))

        board = auth.chess.Board()
        board.push_san("e4")
        self.assertEqual(result["move"], {"uci": "e2e4", "san": "e4"})
        self.assertEqual(result["game"]["fen"], board.fen())
        self.assertEqual(result["game"]["move_history"], [{"uci": "e2e4", "san": "e4"}])
        self.assertEqual(result["game"]["current_player"], "smtptest")
        self.assertEqual(result["game"]["version"], 1)
        with self.connect() as conn:
            notice = conn.execute("SELECT recipient, subject, body, status FROM email_outbox").fetchone()
            self.assertEqual(notice["recipient"], "smtptest@example.com")
            self.assertIn("Your turn", notice["subject"])
            self.assertIn("played e4", notice["body"])
            self.assertEqual(notice["status"], "pending")

    def test_turn_email_retries_and_records_delivery(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        game_id = asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token)))['game_id']
        asyncio.run(auth.submit_email_game_move(
            game_id, auth.EmailGameMoveRequest(move="e4", expected_version=0), "Bearer test"
        ))
        self.mail.side_effect = [RuntimeError("SMTP unavailable"), None]

        self.assertTrue(auth._process_email_outbox_once())
        with self.connect() as conn:
            failed_attempt = conn.execute("SELECT status, attempts FROM email_outbox").fetchone()
            self.assertEqual(tuple(failed_attempt), ("pending", 1))
            conn.execute("UPDATE email_outbox SET next_attempt_at = ?", ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),))

        self.assertTrue(auth._process_email_outbox_once())
        with self.connect() as conn:
            delivered = conn.execute("SELECT status, attempts, sent_at FROM email_outbox").fetchone()
            self.assertEqual(delivered["status"], "sent")
            self.assertEqual(delivered["attempts"], 2)
            self.assertIsNotNone(delivered["sent_at"])

    def test_magic_link_is_generic_expiring_and_single_use(self):
        response = asyncio.run(auth.request_email_game_link(auth.EmailGameLinkRequest(email="smtptest@example.com")))
        self.assertTrue(response["success"])
        self.assertIn("If that verified account", response["message"])
        with self.connect() as conn:
            queued = conn.execute("SELECT recipient, body FROM email_outbox").fetchone()
            self.assertEqual(queued["recipient"], "smtptest@example.com")
            token = queued["body"].split("magic_token=", 1)[1].splitlines()[0]
            expiry = conn.execute("SELECT expires_at FROM email_game_magic_links").fetchone()[0]
            self.assertGreater(datetime.fromisoformat(expiry), datetime.now(timezone.utc))

        result = asyncio.run(auth.consume_email_game_link(auth.EmailGameLinkConsumeRequest(token=token)))
        self.assertEqual(result["username"], "smtptest")
        self.assertFalse(result["is_admin"])
        self.assertEqual(verify_token(result["token"])["username"], "smtptest")
        with self.assertRaises(auth.HTTPException) as error:
            asyncio.run(auth.consume_email_game_link(auth.EmailGameLinkConsumeRequest(token=token)))
        self.assertEqual(error.exception.status_code, 400)

    def test_magic_link_requests_do_not_enumerate_or_queue_admin(self):
        with self.connect() as conn:
            conn.execute("UPDATE users SET is_admin = 1 WHERE username = 'inviter'")
        unknown = asyncio.run(auth.request_email_game_link(auth.EmailGameLinkRequest(email="missing@example.com")))
        admin = asyncio.run(auth.request_email_game_link(auth.EmailGameLinkRequest(email="inviter@example.com")))
        self.assertEqual(unknown["message"], admin["message"])
        with self.connect() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM email_outbox").fetchone()[0], 0)

    def test_turn_reminder_requires_other_player_and_has_cooldown(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        game_id = asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token)))['game_id']
        with patch.object(auth, "verify_jwt_token", return_value={"username": "smtptest"}):
            result = asyncio.run(auth.remind_email_game_player(game_id, "Bearer test"))
            self.assertTrue(result["success"])
            with self.assertRaises(auth.HTTPException) as error:
                asyncio.run(auth.remind_email_game_player(game_id, "Bearer test"))
        self.assertEqual(error.exception.status_code, 429)
        with self.connect() as conn:
            notice = conn.execute("SELECT recipient, subject FROM email_outbox").fetchone()
            self.assertEqual(notice["recipient"], "inviter@example.com")
            self.assertIn("Reminder", notice["subject"])
            self.assertIsNotNone(conn.execute("SELECT last_reminder_at FROM email_games").fetchone()[0])

        with patch.object(auth, "verify_jwt_token", return_value={"username": "inviter"}):
            with self.assertRaises(auth.HTTPException) as error:
                asyncio.run(auth.remind_email_game_player(game_id, "Bearer test"))
        self.assertEqual(error.exception.status_code, 409)

    def test_move_rejects_illegal_out_of_turn_and_stale_requests(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        game_id = asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token)))['game_id']

        with self.assertRaises(auth.HTTPException) as error:
            asyncio.run(auth.submit_email_game_move(
                game_id, auth.EmailGameMoveRequest(move="e7e5", expected_version=0), "Bearer test"
            ))
        self.assertEqual(error.exception.status_code, 400)

        asyncio.run(auth.submit_email_game_move(
            game_id, auth.EmailGameMoveRequest(move="e4", expected_version=0), "Bearer test"
        ))
        with self.assertRaises(auth.HTTPException) as error:
            asyncio.run(auth.submit_email_game_move(
                game_id, auth.EmailGameMoveRequest(move="e5", expected_version=1), "Bearer test"
            ))
        self.assertEqual(error.exception.status_code, 403)

        with patch.object(auth, "verify_jwt_token", return_value={"username": "smtptest"}):
            with self.assertRaises(auth.HTTPException) as error:
                asyncio.run(auth.submit_email_game_move(
                    game_id, auth.EmailGameMoveRequest(move="e7e5", expected_version=0), "Bearer test"
                ))
        self.assertEqual(error.exception.status_code, 409)

    def test_checkmate_completes_email_game(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        game_id = asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token)))['game_id']
        sequence = [
            ("inviter", "f3"), ("smtptest", "e5"), ("inviter", "g4"), ("smtptest", "Qh4#")
        ]
        result = None
        for version, (username, move) in enumerate(sequence):
            with patch.object(auth, "verify_jwt_token", return_value={"username": username}):
                result = asyncio.run(auth.submit_email_game_move(
                    game_id, auth.EmailGameMoveRequest(move=move, expected_version=version), "Bearer test"
                ))
        self.assertEqual(result["game"]["status"], "completed")
        self.assertEqual(result["game"]["result"], "0-1")
        self.assertEqual(result["game"]["winner"], "smtptest")
        self.assertEqual(result["game"]["completion_reason"], "checkmate")
        self.assertIsNotNone(result["game"]["completed_at"])
        replay = asyncio.run(auth.replay_email_game(game_id, "Bearer test"))
        self.assertEqual(len(replay["positions"]), 5)
        self.assertEqual(replay["positions"][-1], result["game"]["fen"])
        pgn = asyncio.run(auth.export_email_game_pgn(game_id, "Bearer test"))
        self.assertEqual(pgn.media_type, "application/x-chess-pgn")
        self.assertIn('[Result "0-1"]', pgn.body.decode())
        self.assertIn("Qh4#", pgn.body.decode())
        with patch.object(auth, "verify_jwt_token", return_value={"username": "outsider"}):
            with self.assertRaises(auth.HTTPException) as error:
                asyncio.run(auth.replay_email_game(game_id, "Bearer test"))
        self.assertEqual(error.exception.status_code, 404)
        with self.connect() as conn:
            statuses = conn.execute("SELECT notification_type, status FROM email_outbox").fetchall()
            self.assertEqual(sum(row["status"] == "cancelled" for row in statuses), 3)
            self.assertEqual(sum(row["notification_type"] == "result" and row["status"] == "pending" for row in statuses), 2)
        with patch.object(auth, "verify_jwt_token", return_value={"username": "smtptest"}):
            with self.assertRaises(auth.HTTPException) as error:
                asyncio.run(auth.submit_email_game_move(
                    game_id, auth.EmailGameMoveRequest(move="e7e6", expected_version=4), "Bearer test"
                ))
        self.assertEqual(error.exception.status_code, 409)

    def test_draw_offer_requires_turn_and_acceptance_records_draw(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        game_id = asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token)))['game_id']

        with patch.object(auth, "verify_jwt_token", return_value={"username": "smtptest"}):
            with self.assertRaises(auth.HTTPException) as error:
                asyncio.run(auth.apply_email_game_action(
                    game_id, auth.EmailGameActionRequest(action="offer_draw", expected_version=0), "Bearer test"
                ))
        self.assertEqual(error.exception.status_code, 403)

        with patch.object(auth, "verify_jwt_token", return_value={"username": "inviter"}):
            offered = asyncio.run(auth.apply_email_game_action(
                game_id, auth.EmailGameActionRequest(action="offer_draw", expected_version=0), "Bearer test"
            ))
            self.assertEqual(offered["game"]["version"], 1)
            self.assertEqual(offered["game"]["draw_offer_by"], "inviter")
            with self.assertRaises(auth.HTTPException) as error:
                asyncio.run(auth.apply_email_game_action(
                    game_id, auth.EmailGameActionRequest(action="accept_draw", expected_version=1), "Bearer test"
                ))
        self.assertEqual(error.exception.status_code, 409)

        with patch.object(auth, "verify_jwt_token", return_value={"username": "smtptest"}):
            accepted = asyncio.run(auth.apply_email_game_action(
                game_id, auth.EmailGameActionRequest(action="accept_draw", expected_version=1), "Bearer test"
            ))
        self.assertEqual(accepted["game"]["status"], "completed")
        self.assertEqual(accepted["game"]["result"], "1/2-1/2")
        self.assertIsNone(accepted["game"]["winner"])
        self.assertEqual(accepted["game"]["completion_reason"], "agreed_draw")
        self.assertIsNone(accepted["game"]["draw_offer_by"])
        with self.connect() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM email_outbox WHERE notification_type = 'result'").fetchone()[0], 2)

    def test_declining_draw_clears_offer_and_notifies_offerer(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        game_id = asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token)))['game_id']
        with patch.object(auth, "verify_jwt_token", return_value={"username": "inviter"}):
            asyncio.run(auth.apply_email_game_action(
                game_id, auth.EmailGameActionRequest(action="offer_draw", expected_version=0), "Bearer test"
            ))
        with patch.object(auth, "verify_jwt_token", return_value={"username": "smtptest"}):
            result = asyncio.run(auth.apply_email_game_action(
                game_id, auth.EmailGameActionRequest(action="decline_draw", expected_version=1), "Bearer test"
            ))
        self.assertEqual(result["game"]["status"], "active")
        self.assertEqual(result["game"]["version"], 2)
        self.assertIsNone(result["game"]["draw_offer_by"])
        with self.connect() as conn:
            offer = conn.execute("SELECT status FROM email_outbox WHERE notification_type = 'draw_offer'").fetchone()
            reply = conn.execute("SELECT recipient, status FROM email_outbox WHERE notification_type = 'draw_response'").fetchone()
            self.assertEqual(offer["status"], "cancelled")
            self.assertEqual(tuple(reply), ("inviter@example.com", "pending"))

    def test_resignation_completes_game_and_cancels_pending_turn_email(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        game_id = asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token)))['game_id']
        asyncio.run(auth.submit_email_game_move(
            game_id, auth.EmailGameMoveRequest(move="e4", expected_version=0), "Bearer test"
        ))

        with patch.object(auth, "verify_jwt_token", return_value={"username": "smtptest"}):
            result = asyncio.run(auth.apply_email_game_action(
                game_id, auth.EmailGameActionRequest(action="resign", expected_version=1), "Bearer test"
            ))

        self.assertEqual(result["game"]["status"], "completed")
        self.assertEqual(result["game"]["result"], "1-0")
        self.assertEqual(result["game"]["winner"], "inviter")
        self.assertEqual(result["game"]["completion_reason"], "resignation")
        with self.connect() as conn:
            turn = conn.execute("SELECT status FROM email_outbox WHERE notification_type = 'turn'").fetchone()
            self.assertEqual(turn["status"], "cancelled")
            self.assertEqual(conn.execute("SELECT count(*) FROM email_outbox WHERE notification_type = 'result'").fetchone()[0], 2)

    def test_stalemate_move_records_draw_result(self):
        self.invite()
        token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        game_id = asyncio.run(auth.respond_to_email_invite(auth.EmailInviteResponse(token=token)))['game_id']
        before_stalemate = "k7/8/2K5/1Q6/8/8/8/8 w - - 0 1"
        with self.connect() as conn:
            conn.execute("UPDATE email_games SET fen = ?, current_player = 'inviter' WHERE id = ?",
                         (before_stalemate, game_id))

        result = asyncio.run(auth.submit_email_game_move(
            game_id, auth.EmailGameMoveRequest(move="b5b6", expected_version=0), "Bearer test"
        ))

        self.assertEqual(result["game"]["status"], "completed")
        self.assertEqual(result["game"]["result"], "1/2-1/2")
        self.assertIsNone(result["game"]["winner"])
        self.assertEqual(result["game"]["completion_reason"], "stalemate")

    def test_http_draw_actions_replay_and_pgn_export(self):
        self.invite()
        invite_token = self.mail.call_args.args[2].split("?token=", 1)[1].splitlines()[0]
        game_id = asyncio.run(auth.respond_to_email_invite(
            auth.EmailInviteResponse(token=invite_token)
        ))["game_id"]

        async def exercise_routes():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=auth.app), base_url="http://testserver") as client:
                white_headers = {"Authorization": "Bearer " + auth.create_token("inviter", False)}
                black_headers = {"Authorization": "Bearer " + auth.create_token("smtptest", False)}
                base = f"/community/email-games/{game_id}"
                moved = await client.post(base + "/moves", headers=white_headers,
                                          json={"move": "e4", "expected_version": 0})
                self.assertEqual(moved.status_code, 200)
                offer = await client.post(base + "/actions", headers=black_headers,
                                          json={"action": "offer_draw", "expected_version": 1})
                self.assertEqual(offer.status_code, 200)
                stale = await client.post(base + "/actions", headers=white_headers,
                                          json={"action": "accept_draw", "expected_version": 1})
                self.assertEqual(stale.status_code, 409)
                accepted = await client.post(base + "/actions", headers=white_headers,
                                             json={"action": "accept_draw", "expected_version": 2})
                self.assertEqual(accepted.status_code, 200)
                self.assertEqual(accepted.json()["game"]["result"], "1/2-1/2")
                replay = await client.get(base + "/replay", headers=white_headers)
                self.assertEqual(replay.status_code, 200)
                self.assertEqual(len(replay.json()["positions"]), 2)
                pgn = await client.get(base + "/pgn", headers=black_headers)
                self.assertEqual(pgn.status_code, 200)
                self.assertIn('[Result "1/2-1/2"]', pgn.text)
                self.assertIn("1. e4", pgn.text)

        with patch.object(auth, "verify_jwt_token", wraps=verify_token):
            asyncio.run(exercise_routes())


if __name__ == "__main__":
    unittest.main()