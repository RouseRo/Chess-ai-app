import asyncio
import importlib.util
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def auth_module(tmp_path, monkeypatch):
    auth_path = Path(__file__).resolve().parents[1] / "auth-service" / "main.py"
    spec = importlib.util.spec_from_file_location("chess_auth_profiles", auth_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    database_path = tmp_path / "users.db"
    connection = sqlite3.connect(database_path)
    connection.execute(
        """CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            is_verified BOOLEAN DEFAULT 0,
            verification_token TEXT,
            games_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    connection.execute(
        "INSERT INTO users (username, email, password_hash, is_verified) VALUES (?, ?, ?, ?)",
        ("testuser", "testuser@chess.local", "unused", True),
    )
    connection.commit()
    connection.close()
    monkeypatch.setattr(module, "DATABASE_PATH", str(database_path))
    monkeypatch.setattr(
        module,
        "_sqlite_connect",
        lambda path: sqlite3.connect(path, check_same_thread=False),
    )
    monkeypatch.setattr(
        module,
        "verify_jwt_token",
        lambda token: {"username": "testuser"} if token == "valid" else None,
    )
    module.init_db()
    return module


def test_profile_defaults_updates_and_community_roster(auth_module):
    profile_result = asyncio.run(auth_module.get_profile("Bearer valid"))
    assert profile_result["profile"] == {
        "username": "testuser",
        "display_name": "testuser",
        "avatar_id": "rook",
        "location": "",
        "chess_ability": "",
        "email_public": False,
    }

    update_result = asyncio.run(
        auth_module.update_profile(
            auth_module.ProfileUpdateRequest(
                display_name="Knight Fan",
                avatar_id="knight",
                location="Ottawa",
                chess_ability="advanced",
                email_public=True,
            ),
            "Bearer valid",
        )
    )
    assert update_result["success"] is True

    game_result = asyncio.run(
        auth_module.record_player_game_result(
            auth_module.GameResultRequest(result="win", opponent="Stockfish"),
            "Bearer valid",
        )
    )
    assert game_result["success"] is True
    awaitable_activity = asyncio.run(
        auth_module.update_activity(auth_module.ActivityRequest(activity="playing"), "Bearer valid")
    )
    assert awaitable_activity["activity"] == "playing"
    review_result = asyncio.run(
        auth_module.complete_review(
            auth_module.CompleteReviewRequest(game_key="opera-game"),
            "Bearer valid",
        )
    )
    assert review_result["success"] is True

    roster_result = asyncio.run(auth_module.get_online_users("Bearer valid"))
    test_user = next(user for user in roster_result["users"] if user["username"] == "testuser")
    assert test_user["display_name"] == "Knight Fan"
    assert test_user["avatar_id"] == "knight"

    public_result = asyncio.run(auth_module.get_public_profile("testuser", "Bearer valid"))
    assert public_result["profile"]["location"] == "Ottawa"
    assert public_result["profile"]["chess_ability"] == "advanced"
    assert public_result["profile"]["stats"] == {"total": 1, "wins": 1, "losses": 0, "draws": 0}
    assert public_result["profile"]["last_game"]["opponent"] == "Stockfish"
    assert public_result["profile"]["rewards"]["completed_count"] == 1
    assert public_result["profile"]["presence"]["activity"] == "playing"


def test_public_profile_respects_email_visibility(auth_module):
    connection = auth_module.get_db()
    connection.execute(
        "INSERT INTO users (username, email, password_hash, is_verified) VALUES (?, ?, ?, ?)",
        ("opponent", "opponent@chess.local", "unused", True),
    )
    connection.commit()
    connection.close()

    hidden = asyncio.run(auth_module.get_public_profile("opponent", "Bearer valid"))
    assert hidden["profile"]["email"] is None

    connection = auth_module.get_db()
    connection.execute("UPDATE users SET email_public = 1 WHERE username = 'opponent'")
    connection.commit()
    connection.close()

    shared = asyncio.run(auth_module.get_public_profile("opponent", "Bearer valid"))
    assert shared["profile"]["email"] == "opponent@chess.local"


def test_profile_rejects_invalid_name_and_avatar(auth_module):
    invalid_name = asyncio.run(
        auth_module.update_profile(
            auth_module.ProfileUpdateRequest(display_name=" ", avatar_id="rook"),
            "Bearer valid",
        )
    )
    invalid_avatar = asyncio.run(
        auth_module.update_profile(
            auth_module.ProfileUpdateRequest(display_name="Player", avatar_id="not-an-avatar"),
            "Bearer valid",
        )
    )
    assert invalid_name["success"] is False
    assert invalid_avatar["success"] is False