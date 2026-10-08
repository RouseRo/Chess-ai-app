"""
Authentication Service for Chess AI App.
Uses SQLite database for user storage.
"""

from fastapi import FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncio
import sqlite3
import os
import secrets
import hashlib
import random
import re
import bcrypt
import chess
import chess.pgn
import jwt
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape as html_escape
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from threading import Lock

app = FastAPI(title="Chess Auth Service", version="1.0.0")
_email_worker_task: Optional[asyncio.Task] = None

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "chess-app-secret-key-change-in-production")
JWT_EXPIRATION_HOURS = int(os.environ.get("JWT_EXPIRATION_HOURS", "24"))
DATABASE_PATH = os.environ.get("DATABASE_PATH", "/app/data/users.db")
DEV_MODE = os.environ.get("CHESS_DEV_MODE", "").lower() == "true"
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", SMTP_USER)
SMTP_USE_STARTTLS = os.environ.get("SMTP_USE_STARTTLS", "true").lower() == "true"
SMTP_USE_AUTH = os.environ.get("SMTP_USE_AUTH", "true").lower() == "true"
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8080")

def send_verification_email(to_email: str, username: str, token: str) -> None:
    """Send email verification link via SMTP. Logs on failure without raising."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        print(f"[EMAIL] SMTP not configured — verification token for {username}: {token}")
        return
    verify_url = f"{APP_BASE_URL}/?verify_token={token}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your Chess AI account"
    msg["From"] = SMTP_FROM_EMAIL or SMTP_USER
    msg["To"] = to_email
    html = (
        f"<p>Hi {username},</p>"
        f"<p>Click the link below to verify your email address:</p>"
        f"<p><a href='{verify_url}'>Verify my account</a></p>"
        f"<p>If you did not register, you can ignore this email.</p>"
    )
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            if SMTP_USE_STARTTLS:
                server.starttls()
            if SMTP_USE_AUTH:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
    except Exception as e:
        print(f"[EMAIL] Failed to send verification email to {to_email}: {e}")


# Admin login rate limiting (3 failed attempts → 15-min lockout)
_ADMIN_MAX_ATTEMPTS = 3
_ADMIN_LOCKOUT_MINUTES = 15
_admin_failed: dict = defaultdict(list)
_admin_lock = Lock()


def _admin_check_rate(key: str) -> tuple:
    """Returns (is_locked, remaining_seconds)."""
    with _admin_lock:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=_ADMIN_LOCKOUT_MINUTES)
        _admin_failed[key] = [t for t in _admin_failed[key] if t > cutoff]
        if len(_admin_failed[key]) >= _ADMIN_MAX_ATTEMPTS:
            unlock_at = _admin_failed[key][0] + timedelta(minutes=_ADMIN_LOCKOUT_MINUTES)
            return True, max(0, int((unlock_at - now).total_seconds()))
        return False, 0


def _admin_record_failure(key: str):
    with _admin_lock:
        _admin_failed[key].append(datetime.now(timezone.utc))


def _admin_clear(key: str):
    with _admin_lock:
        _admin_failed.pop(key, None)


# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class TokenRequest(BaseModel):
    token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    username: str


# Database functions
def _sqlite_connect(path: str) -> sqlite3.Connection:
    """Open a SQLite connection using unix-dotfile VFS for Azure Files SMB compatibility."""
    uri = f"file:{path}?vfs=unix-dotfile"
    return sqlite3.connect(uri, uri=True, timeout=30, check_same_thread=False)


def get_db():
    """Get database connection."""
    conn = _sqlite_connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    conn = _sqlite_connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            is_verified BOOLEAN DEFAULT 0,
            verification_token TEXT,
            games_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            last_activity TIMESTAMP,
            current_activity TEXT DEFAULT 'offline'
        )
    ''')

    # Migration: add new columns to existing databases
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    for col, definition in [
        ('last_login', 'TIMESTAMP'),
        ('last_activity', 'TIMESTAMP'),
        ('current_activity', "TEXT DEFAULT 'offline'"),
    ]:
        if col not in existing_columns:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")

    # Classic game reviews tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classic_game_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            game_key TEXT NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username, game_key)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            category TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        )
    ''')

    # Create default admin if not exists
    cursor.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        password_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, is_admin, is_verified)
            VALUES (?, ?, ?, ?, ?)
        ''', ("admin", "admin@chess.local", password_hash, True, True))
        print("[AUTH] Created default admin user")

    # Create default test user if not exists
    cursor.execute("SELECT id FROM users WHERE username = ?", ("testuser",))
    if not cursor.fetchone():
        password_hash = bcrypt.hashpw(b"Chess123", bcrypt.gensalt()).decode()
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, is_admin, is_verified)
            VALUES (?, ?, ?, ?, ?)
        ''', ("testuser", "testuser@chess.local", password_hash, False, True))
        print("[AUTH] Created default test user")
    
    conn.commit()
    conn.close()


def create_token(username: str, is_admin: bool, email: str = "") -> str:
    """Create a JWT token."""
    payload = {
        "username": username,
        "is_admin": is_admin,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_jwt_token(token: str) -> Optional[dict]:
    """Verify a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ── Admin auth app (port 8003 — Docker-internal only, not published to host) ──
admin_app = FastAPI(title="Chess Admin Auth", version="1.0.0")
admin_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/admin-auth/login")
@admin_app.post("/admin-auth/login")
async def admin_login(request: LoginRequest):
    """Admin-only login. Rate limited: 3 failed attempts triggers a 15-min lockout."""
    username_key = request.username.strip().lower()

    locked, remaining = _admin_check_rate(username_key)
    if locked:
        mins, secs = divmod(remaining, 60)
        return {"success": False, "message": f"Too many failed attempts. Try again in {mins}m {secs}s."}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, email, password_hash, is_admin, is_verified
        FROM users
        WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)
    ''', (request.username, request.username))
    user = cursor.fetchone()
    conn.close()

    if not user or not bool(user["is_admin"]):
        _admin_record_failure(username_key)
        return {"success": False, "message": "Invalid credentials."}

    try:
        if not bcrypt.checkpw(request.password.encode(), user["password_hash"].encode()):
            _admin_record_failure(username_key)
            return {"success": False, "message": "Invalid credentials."}
    except Exception:
        _admin_record_failure(username_key)
        return {"success": False, "message": "Invalid credentials."}

    if not user["is_verified"]:
        return {"success": False, "message": "Account not verified."}

    _admin_clear(username_key)
    token = create_token(user["username"], True, user["email"])

    conn2 = get_db()
    cur2 = conn2.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cur2.execute(
        "UPDATE users SET last_login = ?, last_activity = ?, current_activity = 'online' WHERE username = ?",
        (now, now, user["username"])
    )
    conn2.commit()
    conn2.close()

    return {
        "success": True,
        "message": f"Welcome back, {user['username']}!",
        "token": token,
        "username": user["username"],
        "is_admin": True
    }


# Startup
@app.on_event("startup")
async def startup():
    global _email_worker_task
    print(f"[AUTH] Database path: {DATABASE_PATH}")
    init_db()
    print(f"[AUTH] Service started")
    
    # List users
    conn = get_db()
    _init_community_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT username, is_admin, is_verified FROM users")
    users = cursor.fetchall()
    print(f"[AUTH] Users in database: {[dict(u) for u in users]}")
    conn.close()
    _email_worker_task = asyncio.create_task(_email_outbox_worker())


@app.on_event("shutdown")
async def shutdown_email_worker():
    if _email_worker_task:
        _email_worker_task.cancel()
        try:
            await _email_worker_task
        except asyncio.CancelledError:
            pass


# Endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "auth", "storage": "sqlite"}


@app.post("/auth/login")
async def login(request: LoginRequest):
    """Authenticate user with username or email."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Find user by username or email (case-insensitive)
    cursor.execute('''
        SELECT id, username, email, password_hash, is_admin, is_verified 
        FROM users 
        WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)
    ''', (request.username, request.username))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return {"success": False, "message": "Invalid username or password."}

    # Admin accounts must use the dedicated secure endpoint (port 8003, Docker-internal only)
    if bool(user["is_admin"]):
        return {"success": False, "message": "Please use the admin login.", "use_admin_login": True}

    # Verify password
    try:
        if not bcrypt.checkpw(request.password.encode(), user["password_hash"].encode()):
            return {"success": False, "message": "Invalid username or password."}
    except Exception:
        return {"success": False, "message": "Invalid username or password."}
    
    # Check if verified
    if not user["is_verified"]:
        return {
            "success": False,
            "message": "Account not verified. Please check your email for the verification link."
        }
    
    # Create token
    token = create_token(user["username"], bool(user["is_admin"]), user["email"])

    # Track login activity
    conn2 = get_db()
    cur2 = conn2.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cur2.execute(
        "UPDATE users SET last_login = ?, last_activity = ?, current_activity = 'online' WHERE username = ?",
        (now, now, user["username"])
    )
    conn2.commit()
    conn2.close()

    return {
        "success": True,
        "message": f"Welcome back, {user['username']}!",
        "token": token,
        "username": user["username"],
        "is_admin": bool(user["is_admin"])
    }


@app.post("/auth/register")
async def register(request: RegisterRequest):
    """Register a new user."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if username exists
    cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (request.username,))
    if cursor.fetchone():
        conn.close()
        return {"success": False, "message": "Username already exists."}
    
    # Check if email exists
    cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (request.email,))
    if cursor.fetchone():
        conn.close()
        return {"success": False, "message": "Email already registered."}
    
    # Hash password and create verification token
    password_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()
    verification_token = secrets.token_hex(32)
    
    try:
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, is_verified, verification_token)
            VALUES (?, ?, ?, ?, ?)
        ''', (request.username.lower(), request.email, password_hash, DEV_MODE, verification_token))
        conn.commit()
        conn.close()
        
        if DEV_MODE:
            return {
                "success": True,
                "message": "Registration successful! (Dev mode: auto-verified)",
                "verification_token": verification_token
            }

        send_verification_email(request.email, request.username, verification_token)
        return {
            "success": True,
            "message": "Registration successful! Please check your email for a verification link."
        }
        
    except sqlite3.IntegrityError as e:
        conn.close()
        return {"success": False, "message": f"Registration failed: {str(e)}"}


@app.post("/auth/verify")
async def verify(authorization: str = Header(None)):
    """Verify a JWT token provided as a Bearer token in the Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[len("Bearer "):]
    payload = verify_jwt_token(token)

    if payload:
        return {
            "success": True,
            "username": payload.get("username"),
            "is_admin": payload.get("is_admin", False),
            "email": payload.get("email", "")
        }

    return {"success": False, "message": "Invalid or expired token."}


@app.post("/auth/verify-email")
async def verify_email(request: VerifyEmailRequest):
    """Verify user's email with verification token."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, username FROM users 
        WHERE verification_token = ? AND is_verified = 0
    ''', (request.token,))
    
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return {"success": False, "message": "Invalid verification token."}
    
    cursor.execute('''
        UPDATE users SET is_verified = 1, verification_token = NULL WHERE id = ?
    ''', (user["id"],))
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "message": f"Email verified successfully! You can now login, {user['username']}."
    }


@app.post("/auth/resend-verification")
async def resend_verification(request: ResendVerificationRequest):
    """Resend the email verification link for an unverified user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email, is_verified FROM users WHERE LOWER(username) = LOWER(?)",
        (request.username,)
    )
    user = cursor.fetchone()

    if not user:
        conn.close()
        return {"success": False, "message": "User not found."}

    if user["is_verified"]:
        conn.close()
        return {"success": False, "message": "User email is already verified."}

    token = secrets.token_hex(32)
    cursor.execute("UPDATE users SET verification_token = ? WHERE id = ?", (token, user["id"]))
    conn.commit()
    conn.close()

    send_verification_email(user["email"], user["username"], token)
    return {"success": True, "message": f"Verification email resent to {user['email']}."}


@app.post("/auth/logout")
async def logout(request: TokenRequest):
    """Logout user."""
    payload = verify_jwt_token(request.token)
    if payload:
        username = payload.get("username")
        conn = get_db()
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "UPDATE users SET last_activity = ?, current_activity = 'offline' WHERE username = ?",
            (now, username)
        )
        conn.commit()
        conn.close()
    return {"success": True, "message": "Logged out successfully."}


class ActivityRequest(BaseModel):
    activity: str  # 'online', 'playing', 'idle'


@app.post("/auth/activity")
async def update_activity(
    request: ActivityRequest,
    authorization: Optional[str] = Header(None)
):
    """Update the current user's activity status."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}

    token = authorization.replace("Bearer ", "")
    payload = verify_jwt_token(token)
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}

    username = payload.get("username")
    allowed = ('online', 'playing', 'idle', 'offline')
    activity = request.activity if request.activity in allowed else 'online'

    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        "UPDATE users SET last_activity = ?, current_activity = ? WHERE username = ?",
        (now, activity, username)
    )
    conn.commit()
    conn.close()
    return {"success": True, "activity": activity}


@app.post("/auth/change-password")
async def change_password(
    request: ChangePasswordRequest,
    authorization: Optional[str] = Header(None)
):
    """Change user's password."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}
    
    token = authorization.replace("Bearer ", "")
    payload = verify_jwt_token(token)
    
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}
    
    username = payload.get("username")
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return {"success": False, "message": "User not found."}
    
    # Verify old password
    if not bcrypt.checkpw(request.old_password.encode(), user["password_hash"].encode()):
        conn.close()
        return {"success": False, "message": "Current password is incorrect."}
    
    # Update password
    new_hash = bcrypt.hashpw(request.new_password.encode(), bcrypt.gensalt()).decode()
    cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hash, username))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Password changed successfully."}


@app.post("/auth/refresh")
async def refresh_token(request: TokenRequest):
    """Refresh a JWT token."""
    payload = verify_jwt_token(request.token)
    
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}
    
    new_token = create_token(
        payload.get("username"),
        payload.get("is_admin", False),
        payload.get("email", "")
    )
    
    return {"success": True, "token": new_token, "message": "Token refreshed successfully."}


# ========== Community Endpoints ==========

import json as _json_module

def _init_community_tables(conn: sqlite3.Connection):
    """Ensure community_messages table exists."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS community_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            message_type TEXT DEFAULT 'chat',
            target_users TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS email_game_invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            responded_at TEXT,
            recipient_color TEXT,
            first_move TEXT
        )
    ''')
    columns = {row[1] for row in conn.execute("PRAGMA table_info(email_game_invites)")}
    if "recipient_email" not in columns:
        conn.execute("ALTER TABLE email_game_invites ADD COLUMN recipient_email TEXT")
        columns.add("recipient_email")
    if "status" not in columns:
        conn.execute("ALTER TABLE email_game_invites ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
        conn.execute("UPDATE email_game_invites SET status = 'accepted' WHERE responded_at IS NOT NULL")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS email_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invitation_id INTEGER NOT NULL UNIQUE REFERENCES email_game_invites(id),
            white_player TEXT NOT NULL,
            black_player TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            fen TEXT NOT NULL,
            move_history TEXT NOT NULL DEFAULT '[]',
            version INTEGER NOT NULL DEFAULT 0,
            current_player TEXT NOT NULL,
            created_at TEXT NOT NULL,
            turn_started_at TEXT NOT NULL,
            last_move_at TEXT,
            last_reminder_at TEXT,
            result TEXT,
            winner TEXT,
            completion_reason TEXT,
            completed_at TEXT,
            draw_offer_by TEXT
        )
    ''')
    game_columns = {row[1] for row in conn.execute("PRAGMA table_info(email_games)")}
    for column in (
        "result TEXT",
        "winner TEXT",
        "completion_reason TEXT",
        "completed_at TEXT",
        "draw_offer_by TEXT",
    ):
        name = column.split()[0]
        if name not in game_columns:
            conn.execute(f"ALTER TABLE email_games ADD COLUMN {column}")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS email_outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            next_attempt_at TEXT NOT NULL,
            claimed_until TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL,
            sent_at TEXT,
            game_id INTEGER,
            notification_type TEXT
        )
    ''')
    outbox_columns = {row[1] for row in conn.execute("PRAGMA table_info(email_outbox)")}
    for column in ("game_id INTEGER", "notification_type TEXT"):
        name = column.split()[0]
        if name not in outbox_columns:
            conn.execute(f"ALTER TABLE email_outbox ADD COLUMN {column}")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_email_outbox_due ON email_outbox(status, next_attempt_at)")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS email_game_magic_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used_at TEXT
        )
    ''')
    conn.execute("CREATE INDEX IF NOT EXISTS idx_email_magic_username ON email_game_magic_links(username, created_at)")
    conn.commit()


def _is_online(last_activity_str: Optional[str], current_activity: Optional[str]) -> bool:
    """Return True if user has been active within the last 5 minutes."""
    if current_activity == 'offline':
        return False
    if not last_activity_str:
        return False
    try:
        last = datetime.fromisoformat(last_activity_str.replace('Z', '+00:00'))
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - last) < timedelta(minutes=5)
    except Exception:
        return False


class CommunityMessageRequest(BaseModel):
    content: str


class AnnouncementRequest(BaseModel):
    content: str
    target_users: Optional[list] = None  # None = broadcast to all


@app.get("/community/online-users")
async def get_online_users(authorization: Optional[str] = Header(None)):
    """Return verified users with their current presence."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}
    payload = verify_jwt_token(authorization.replace("Bearer ", ""))
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, current_activity, last_activity FROM users WHERE is_verified = 1"
    )
    rows = cursor.fetchall()
    conn.close()

    users = []
    for row in rows:
        online = _is_online(row["last_activity"], row["current_activity"])
        users.append({
            "username": row["username"],
            "activity": (row["current_activity"] or "online") if online else "offline"
        })
    return {"success": True, "users": users}


@app.get("/community/messages")
async def get_community_messages(
    limit: int = 50,
    authorization: Optional[str] = Header(None)
):
    """Return recent community chat messages and announcements visible to this user."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}
    payload = verify_jwt_token(authorization.replace("Bearer ", ""))
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}

    username = payload.get("username")
    conn = get_db()
    _init_community_tables(conn)
    cursor = conn.cursor()

    # Fetch recent messages (chat + announcements targeting this user or all)
    cursor.execute(
        '''SELECT id, sender, content, message_type, target_users, created_at
           FROM community_messages
           ORDER BY created_at DESC
           LIMIT ?''',
        (max(1, min(limit, 200)),)
    )
    rows = cursor.fetchall()
    conn.close()

    messages = []
    for row in rows:
        target = row["target_users"]
        # Include if: it's a chat message, or it's an announcement for all (target is NULL),
        # or it targets this specific user.
        if row["message_type"] == "chat":
            include = True
        elif target is None:
            include = True
        else:
            try:
                targets = _json_module.loads(target)
                include = username in targets
            except Exception:
                include = False
        if include:
            messages.append({
                "id": row["id"],
                "sender": row["sender"],
                "content": row["content"],
                "message_type": row["message_type"],
                "target_users": _json_module.loads(row["target_users"]) if row["target_users"] else None,
                "created_at": row["created_at"]
            })

    # Return in chronological order (oldest first)
    messages.reverse()
    return {"success": True, "messages": messages}


@app.post("/community/messages")
async def post_community_message(
    request: CommunityMessageRequest,
    authorization: Optional[str] = Header(None)
):
    """Post a chat message to the community."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}
    payload = verify_jwt_token(authorization.replace("Bearer ", ""))
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}

    content = request.content.strip()
    if not content:
        return {"success": False, "message": "Message cannot be empty."}
    if len(content) > 500:
        return {"success": False, "message": "Message too long (max 500 characters)."}

    username = payload.get("username")
    conn = get_db()
    _init_community_tables(conn)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        "INSERT INTO community_messages (sender, content, message_type, created_at) VALUES (?, ?, 'chat', ?)",
        (username, content, now)
    )
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return {"success": True, "id": msg_id}


@app.post("/community/announcements")
async def post_announcement(
    request: AnnouncementRequest,
    authorization: Optional[str] = Header(None)
):
    """Post an admin announcement (admin only). target_users=None means all users."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}
    payload = verify_jwt_token(authorization.replace("Bearer ", ""))
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}
    if not payload.get("is_admin"):
        return {"success": False, "message": "Admin privileges required."}

    content = request.content.strip()
    if not content:
        return {"success": False, "message": "Announcement cannot be empty."}
    if len(content) > 1000:
        return {"success": False, "message": "Announcement too long (max 1000 characters)."}

    username = payload.get("username")
    target_json = _json_module.dumps(request.target_users) if request.target_users else None
    conn = get_db()
    _init_community_tables(conn)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        "INSERT INTO community_messages (sender, content, message_type, target_users, created_at) VALUES (?, ?, 'announcement', ?, ?)",
        (username, content, target_json, now)
    )
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return {"success": True, "id": msg_id}


class DirectMessageRequest(BaseModel):
    recipient: str
    content: str


class GameInviteRequest(BaseModel):
    recipient: str


class EmailInviteResponse(BaseModel):
    token: str
    choice: str = "black"
    first_move: str = ""
    decision: str = "accept"
    username: Optional[str] = None
    password: Optional[str] = None


class EmailGameMoveRequest(BaseModel):
    move: str
    expected_version: int


class EmailGameActionRequest(BaseModel):
    action: str
    expected_version: int


class EmailGameLinkRequest(BaseModel):
    email: str


class EmailGameLinkConsumeRequest(BaseModel):
    token: str


def _send_invite_email(address: str, subject: str, body: str,
                       html_body: Optional[str] = None) -> None:
    if not all((SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL)):
        raise RuntimeError("Email is not configured.")
    message = MIMEMultipart("alternative")
    message["From"] = SMTP_FROM_EMAIL
    message["To"] = address
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))
    if html_body:
        message.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        if SMTP_USE_STARTTLS:
            server.starttls()
        if SMTP_USE_AUTH:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM_EMAIL, address, message.as_string())


def _queue_email(conn: sqlite3.Connection, address: str, subject: str, body: str, now: str,
                 game_id: Optional[int] = None, notification_type: Optional[str] = None) -> None:
    conn.execute(
        "INSERT INTO email_outbox (recipient, subject, body, next_attempt_at, created_at, game_id, notification_type) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (address, subject, body, now, now, game_id, notification_type)
    )


def _notification_email_html(body: str, notification_type: Optional[str]) -> Optional[str]:
    message, separator, link_line = body.rstrip().rpartition("\n\n")
    link = link_line.rsplit(": ", 1)[-1].strip()
    if not separator or not link.startswith(("http://", "https://")):
        return None
    action_labels = {
        "turn": "Go to game",
        "reminder": "Go to game",
        "draw_offer": "Review draw offer",
        "draw_response": "View game",
        "result": "Review game",
    }
    action_label = "Sign in to your games" if "magic_token=" in link else action_labels.get(
        notification_type, "Open game"
    )
    safe_message = html_escape(message).replace("\n", "<br>")
    safe_link = html_escape(link, quote=True)
    return (
        '<div style="font-family:Arial,sans-serif;color:#242424;font-size:16px">'
        f'<p>{safe_message}</p>'
        '<table role="presentation" cellspacing="0" cellpadding="0"><tr><td '
        'bgcolor="#176b45" style="border-radius:4px">'
        f'<a href="{safe_link}" style="display:inline-block;padding:12px 20px;'
        f'color:#ffffff;text-decoration:none;font-weight:bold">{html_escape(action_label)}</a>'
        '</td></tr></table>'
        f'<p style="font-size:13px;color:#555">Or use this link: '
        f'<a href="{safe_link}">{html_escape(link)}</a></p>'
        '</div>'
    )


def _cancel_pending_game_notifications(conn: sqlite3.Connection, game_id: int, now: str) -> None:
    conn.execute(
        "UPDATE email_outbox SET status = 'cancelled', body = '', claimed_until = NULL, "
        "last_error = 'Game state changed before notification was sent' "
        "WHERE game_id = ? AND notification_type IN ('turn', 'reminder', 'draw_offer') AND status = 'pending'",
        (game_id,)
    )


def _queue_game_result_notifications(conn: sqlite3.Connection, game_id: int, white_player: str,
                                     black_player: str, result: str, winner: Optional[str],
                                     reason: str, now: str) -> None:
    _cancel_pending_game_notifications(conn, game_id, now)
    outcome = f"{result} ({winner} wins)" if winner else "1/2-1/2 (draw)"
    link = f"{APP_BASE_URL.rstrip('/')}/email-game.html?game_id={game_id}"
    for username in (white_player, black_player):
        recipient = conn.execute("SELECT email FROM users WHERE username = ?", (username,)).fetchone()
        if recipient:
            _queue_email(
                conn, recipient["email"], "Your email chess game is complete",
                f"The game ended by {reason.replace('_', ' ')}. Result: {outcome}.\n\nReview the game: {link}\n",
                now, game_id, "result"
            )


def _email_game_turn_color(game: sqlite3.Row) -> str:
    return "White" if game["current_player"] == game["white_player"] else "Black"


def _process_email_outbox_once() -> bool:
    now = datetime.now(timezone.utc)
    now_text = now.isoformat()
    conn = get_db()
    try:
        _init_community_tables(conn)
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT * FROM email_outbox WHERE "
            "(status = 'pending' AND next_attempt_at <= ?) OR "
            "(status = 'processing' AND claimed_until <= ?) ORDER BY id LIMIT 1",
            (now_text, now_text)
        ).fetchone()
        if not row:
            conn.rollback()
            return False
        attempts = row["attempts"] + 1
        conn.execute(
            "UPDATE email_outbox SET status = 'processing', attempts = ?, claimed_until = ? WHERE id = ?",
            (attempts, (now + timedelta(minutes=2)).isoformat(), row["id"])
        )
        conn.commit()
        message = dict(row)
        message["attempts"] = attempts
    finally:
        conn.close()

    if message.get("game_id") and message.get("notification_type") in ("turn", "reminder", "draw_offer"):
        conn = get_db()
        try:
            game = conn.execute("SELECT status FROM email_games WHERE id = ?", (message["game_id"],)).fetchone()
            if not game or game["status"] != "active":
                conn.execute(
                    "UPDATE email_outbox SET status = 'cancelled', body = '', claimed_until = NULL, "
                    "last_error = 'Game is no longer active' WHERE id = ? AND status = 'processing'",
                    (message["id"],)
                )
                conn.commit()
                return True
        finally:
            conn.close()

    try:
        html_body = _notification_email_html(
            message["body"], message.get("notification_type")
        )
        _send_invite_email(message["recipient"], message["subject"], message["body"], html_body)
    except Exception as exc:
        final_attempt = message["attempts"] >= 5
        retry_at = (now + timedelta(seconds=min(60 * (2 ** (message["attempts"] - 1)), 3600))).isoformat()
        conn = get_db()
        try:
            conn.execute(
                "UPDATE email_outbox SET status = ?, body = CASE WHEN ? = 'failed' THEN '' ELSE body END, "
                "next_attempt_at = ?, claimed_until = NULL, last_error = ? WHERE id = ?",
                ("failed" if final_attempt else "pending", "failed" if final_attempt else "pending",
                 retry_at, str(exc)[:500], message["id"])
            )
            conn.commit()
        finally:
            conn.close()
        print(f"[EMAIL] Delivery attempt {message['attempts']} failed for outbox item {message['id']}: {exc}")
        return True

    conn = get_db()
    try:
        conn.execute(
            "UPDATE email_outbox SET status = 'sent', body = '', sent_at = ?, claimed_until = NULL, last_error = NULL WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), message["id"])
        )
        conn.commit()
    finally:
        conn.close()
    return True


async def _email_outbox_worker() -> None:
    loop = asyncio.get_running_loop()
    while True:
        try:
            while await loop.run_in_executor(None, _process_email_outbox_once):
                pass
        except Exception as exc:
            print(f"[EMAIL] Outbox worker failed: {exc}")
        await asyncio.sleep(5)


def _game_invite_email(sender: str, link: str) -> str:
    return (f"{sender} invites you to play a friendly game of chess.\n\n"
            "Open the invitation to accept or decline. If you accept, choose your color and opening move.\n\n"
            "Accepted games are played by taking turns on a shared board. You will receive an email when it is your turn.\n\n"
            f"Respond here within 30 days: {link}\n")


def _game_invite_email_html(sender: str, link: str, preview: bool = False) -> str:
    sender_name = html_escape(sender)
    if preview:
        accept_url = decline_url = "#"
    else:
        accept_url = html_escape(f"{link}&decision=accept", quote=True)
        decline_url = html_escape(f"{link}&decision=decline", quote=True)
    return f"""<!doctype html>
<html lang="en">
<body style="margin:0;padding:24px;background:#f2f5f2;color:#25382e;font-family:Georgia,serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #c7d3c9;">
        <tr><td style="padding:28px;">
            <h1 style="margin:0 0 16px;font-size:24px;">Chess invitation</h1>
            <p style="line-height:1.5;">{sender_name} invites you to play a friendly game of chess.</p>
            <p style="line-height:1.5;">Accept to choose your color and opening move. Games are played on a shared board, and you will receive an email when it is your turn.</p>
            <table role="presentation" cellspacing="0" cellpadding="0" style="margin:24px 0;">
                <tr>
                    <td bgcolor="#2e7d32" style="padding:12px 18px;">
                        <a href="{accept_url}" style="color:#ffffff;text-decoration:none;font-weight:bold;">Accept invitation</a>
                    </td>
                    <td width="12"></td>
                    <td bgcolor="#ffffff" style="padding:11px 17px;border:1px solid #829486;">
                        <a href="{decline_url}" style="color:#25382e;text-decoration:none;font-weight:bold;">Decline</a>
                    </td>
                </tr>
            </table>
            <p style="font-size:13px;line-height:1.5;color:#59675e;">Invitation expires in 30 days. Opening either link will not record a decision; you will confirm it on the invitation page.</p>
        </td></tr>
    </table>
</body>
</html>"""


def _game_invite_response_email_html(recipient: str, status: str, reply: str,
                                    game_link: Optional[str]) -> str:
    recipient_name = html_escape(recipient)
    heading = "Invitation accepted" if status == "accepted" else "Invitation declined"
    safe_reply = html_escape(reply).replace("\n", "<br>")
    action = ""
    if game_link:
        safe_link = html_escape(game_link, quote=True)
        action = (
            '<table role="presentation" cellspacing="0" cellpadding="0" style="margin:24px 0;">'
            '<tr><td bgcolor="#2e7d32" style="padding:12px 18px;">'
            f'<a href="{safe_link}" style="color:#ffffff;text-decoration:none;font-weight:bold;">View the board</a>'
            '</td></tr></table>'
            f'<p style="font-size:13px;line-height:1.5;color:#59675e;">Sign-in is required. Or use this link: '
            f'<a href="{safe_link}">{html_escape(game_link)}</a></p>'
        )
    return f"""<!doctype html>
<html lang="en">
<body style="margin:0;padding:24px;background:#f2f5f2;color:#25382e;font-family:Georgia,serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #c7d3c9;">
        <tr><td style="padding:28px;">
            <h1 style="margin:0 0 16px;font-size:24px;">{heading}</h1>
            <p style="line-height:1.5;">{recipient_name} {status} your friendly chess invitation.</p>
            <p style="line-height:1.5;">{safe_reply}</p>
            {action}
        </td></tr>
    </table>
</body>
</html>"""


def _opening_move(move: str) -> str:
    board = chess.Board()
    try:
        parsed = board.parse_san(move)
    except ValueError:
        try:
            parsed = chess.Move.from_uci(move.lower())
            if parsed not in board.legal_moves:
                raise ValueError("Illegal opening move")
        except (ValueError, chess.InvalidMoveError):
            raise ValueError("Enter a legal first move for White, such as e4 or d4.")
    return board.san(parsed)


@app.post("/community/dm")
async def send_direct_message(
    request: DirectMessageRequest,
    authorization: Optional[str] = Header(None)
):
    """Send a direct message to a specific user."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}
    payload = verify_jwt_token(authorization.replace("Bearer ", ""))
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}

    sender = payload.get("username")
    recipient = request.recipient.strip()
    content = request.content.strip()

    if not content:
        return {"success": False, "message": "Message cannot be empty."}
    if len(content) > 500:
        return {"success": False, "message": "Message too long (max 500 characters)."}
    if sender.lower() == recipient.lower():
        return {"success": False, "message": "Cannot send a message to yourself."}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE LOWER(username) = LOWER(?)", (recipient,))
    recipient_row = cursor.fetchone()
    if not recipient_row:
        conn.close()
        return {"success": False, "message": "Recipient not found."}

    actual_recipient = recipient_row["username"]
    _init_community_tables(conn)
    now = datetime.now(timezone.utc).isoformat()
    target_json = _json_module.dumps([sender, actual_recipient])
    cursor.execute(
        "INSERT INTO community_messages (sender, content, message_type, target_users, created_at) VALUES (?, ?, 'dm', ?, ?)",
        (sender, content, target_json, now)
    )
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return {"success": True, "id": msg_id}


@app.get("/community/game-invite/preview")
async def preview_game_invite(recipient: str, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}
    payload = verify_jwt_token(authorization.replace("Bearer ", ""))
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}
    conn = get_db()
    row = conn.execute(
        "SELECT username, is_verified, last_activity, current_activity FROM users WHERE LOWER(username) = LOWER(?)",
        (recipient.strip(),)
    ).fetchone()
    sender = payload["username"]
    if row:
        conn.close()
        if not row["is_verified"] or row["username"].lower() == sender.lower():
            return {"success": False, "message": "Recipient is not available for email invitations."}
        if _is_online(row["last_activity"], row["current_activity"]):
            return {"success": False, "message": "This player is online. Refresh the player list to invite them in-app."}
        actual_recipient = row["username"]
    else:
        recipient_email = _normalize_invite_email(recipient)
        if not recipient_email:
            conn.close()
            return {"success": False, "message": "Enter a valid email address or community username."}
        sender_row = conn.execute("SELECT email FROM users WHERE LOWER(username) = LOWER(?)", (sender,)).fetchone()
        conn.close()
        if sender_row and sender_row["email"].lower() == recipient_email:
            return {"success": False, "message": "Cannot invite yourself."}
        actual_recipient = recipient_email
    if not actual_recipient:
        return {"success": False, "message": "Recipient is not available for email invitations."}
    return {"success": True, "recipient": actual_recipient,
            "subject": f"Chess invitation from {sender}",
            "body": _game_invite_email(sender, "[Personal response link included when sent]"),
            "html_body": _game_invite_email_html(sender, "#", preview=True)}


def _normalize_invite_email(value: str) -> Optional[str]:
    address = value.strip().lower()
    if len(address) > 254 or address.count("@") != 1:
        return None
    local, domain = address.split("@")
    if (not local or len(local) > 64 or ".." in local or local.startswith(".") or local.endswith(".")
            or not re.fullmatch(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+", local)):
        return None
    labels = domain.split(".")
    label_pattern = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    if (len(labels) < 2 or len(domain) > 253 or len(labels[-1]) < 2
            or any(not re.fullmatch(label_pattern, label) for label in labels)):
        return None
    return address


@app.post("/community/game-invite")
async def send_game_invite(
    request: GameInviteRequest,
    authorization: Optional[str] = Header(None)
):
    """Send a game invitation to a specific user."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}
    payload = verify_jwt_token(authorization.replace("Bearer ", ""))
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}

    sender = payload.get("username")
    recipient = request.recipient.strip()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, email, is_verified, last_activity, current_activity FROM users WHERE LOWER(username) = LOWER(?)", (recipient,))
    recipient_row = cursor.fetchone()
    _init_community_tables(conn)
    now = datetime.now(timezone.utc).isoformat()
    if not recipient_row:
        recipient_email = _normalize_invite_email(recipient)
        if not recipient_email:
            conn.close()
            return {"success": False, "message": "Enter a valid email address or community username."}
        sender_row = conn.execute("SELECT email FROM users WHERE LOWER(username) = LOWER(?)", (sender,)).fetchone()
        if sender_row and sender_row["email"].lower() == recipient_email:
            conn.close()
            return {"success": False, "message": "Cannot invite yourself."}
        existing = conn.execute(
            "SELECT id FROM email_game_invites WHERE recipient_email = ? AND status = 'pending' AND expires_at > ?",
            (recipient_email, now)
        ).fetchone()
        if existing:
            conn.close()
            return {"success": False, "message": "An invitation is already pending for this email address."}
        actual_recipient = recipient_email
        recipient_address = recipient_email
        is_external = True
    else:
        actual_recipient = recipient_row["username"]
        if sender.lower() == actual_recipient.lower():
            conn.close()
            return {"success": False, "message": "Cannot invite yourself."}
        if not recipient_row["is_verified"]:
            conn.close()
            return {"success": False, "message": "Recipient must verify their email first."}
        if _is_online(recipient_row["last_activity"], recipient_row["current_activity"]):
            target_json = _json_module.dumps([sender, actual_recipient])
            content = f"{sender} has invited you to play a game of chess!"
            cursor.execute(
                "INSERT INTO community_messages (sender, content, message_type, target_users, created_at) VALUES (?, ?, 'game_invite', ?, ?)",
                (sender, content, target_json, now)
            )
            conn.commit()
            msg_id = cursor.lastrowid
            conn.close()
            return {"success": True, "id": msg_id, "recipient": actual_recipient}
        recipient_address = recipient_row["email"]
        recipient_email = None
        is_external = False

    if is_external or recipient_row:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        link = f"{APP_BASE_URL.rstrip('/')}/invite.html?token={token}"
        cursor.execute(
            "INSERT INTO email_game_invites (sender, recipient, recipient_email, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
            (sender, actual_recipient, recipient_email, token_hash, now, expires_at)
        )
        invite_id = cursor.lastrowid
        try:
            _send_invite_email(
                recipient_address, f"Chess invitation from {sender}",
                _game_invite_email(sender, link),
                _game_invite_email_html(sender, link)
            )
        except (RuntimeError, smtplib.SMTPException, OSError):
            conn.rollback()
            conn.close()
            return {"success": False, "message": "Invitation email could not be sent. Check email configuration."}
        conn.commit()
        conn.close()
        return {"success": True, "id": invite_id, "recipient": actual_recipient, "emailed": True}


def _find_email_invite(conn: sqlite3.Connection, token: str):
    if not token or len(token) > 256:
        return None
    return conn.execute(
        "SELECT * FROM email_game_invites WHERE token_hash = ?",
        (hashlib.sha256(token.encode()).hexdigest(),)
    ).fetchone()


@app.get("/community/email-invite")
async def get_email_invite(token: str):
    conn = get_db()
    _init_community_tables(conn)
    invite = _find_email_invite(conn, token)
    conn.close()
    if not invite or invite["responded_at"] or datetime.fromisoformat(invite["expires_at"]) < datetime.now(timezone.utc):
        return {"success": False, "message": "This invitation is invalid, expired, or already answered."}
    needs_registration = False
    recipient_email = invite["recipient_email"]
    if recipient_email:
        conn = get_db()
        existing_user = conn.execute(
            "SELECT username FROM users WHERE LOWER(email) = LOWER(?)", (recipient_email,)
        ).fetchone()
        conn.close()
        needs_registration = existing_user is None
    return {"success": True, "sender": invite["sender"], "recipient": invite["recipient"],
            "recipient_email": recipient_email, "needs_registration": needs_registration}


@app.post("/community/email-invite/respond")
async def respond_to_email_invite(request: EmailInviteResponse):
    if request.decision not in ("accept", "decline"):
        return {"success": False, "message": "Choose Accept or Decline."}
    if request.decision == "accept" and request.choice not in ("white", "black", "random"):
        return {"success": False, "message": "Choose White, Black, or random."}
    if len(request.first_move) > 12:
        return {"success": False, "message": "First move is too long."}
    if request.decision == "decline":
        color, first_move, reply = None, None, "I declined your game invitation."
    elif request.choice == "white":
        try:
            first_move = _opening_move(request.first_move.strip())
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        color = "white"
        reply = f"I play White. My first move is {first_move}."
    elif request.choice == "black":
        if request.first_move.strip():
            return {"success": False, "message": "Only White can supply the first move."}
        color, first_move, reply = "black", None, "You play White."
    else:
        if request.first_move.strip():
            return {"success": False, "message": "A random opening cannot also specify a move."}
        color = "white"
        board = chess.Board()
        first_move = board.san(random.choice(list(board.legal_moves)))
        reply = f"Let the first move be chosen at random. I play White and my first move is {first_move}."

    conn = get_db()
    _init_community_tables(conn)
    conn.execute("BEGIN IMMEDIATE")
    invite = _find_email_invite(conn, request.token)
    if not invite or invite["responded_at"] or datetime.fromisoformat(invite["expires_at"]) < datetime.now(timezone.utc):
        conn.rollback()
        conn.close()
        return {"success": False, "message": "This invitation is invalid, expired, or already answered."}
    inviter = conn.execute("SELECT email FROM users WHERE username = ?", (invite["sender"],)).fetchone()
    if not inviter:
        conn.rollback()
        conn.close()
        return {"success": False, "message": "Inviting player no longer exists."}
    recipient_username = invite["recipient"]
    if request.decision == "accept" and invite["recipient_email"]:
        existing_user = conn.execute(
            "SELECT username FROM users WHERE LOWER(email) = LOWER(?)", (invite["recipient_email"],)
        ).fetchone()
        if existing_user:
            recipient_username = existing_user["username"]
            conn.execute(
                "UPDATE users SET is_verified = 1, verification_token = NULL WHERE username = ?",
                (recipient_username,)
            )
        else:
            username = (request.username or "").strip()
            password = request.password or ""
            if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", username):
                conn.rollback()
                conn.close()
                return {"success": False, "message": "Username must be 3-20 characters using letters, numbers, or underscores."}
            if len(password.encode("utf-8")) < 8 or len(password.encode("utf-8")) > 72:
                conn.rollback()
                conn.close()
                return {"success": False, "message": "Password must be between 8 and 72 bytes."}
            duplicate = conn.execute(
                "SELECT 1 FROM users WHERE LOWER(username) = LOWER(?)", (username,)
            ).fetchone()
            if duplicate:
                conn.rollback()
                conn.close()
                return {"success": False, "message": "That username is already taken. Choose another username."}
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()
            recipient_username = username.lower()
            conn.execute(
                "INSERT INTO users (username, email, password_hash, is_verified, verification_token) VALUES (?, ?, ?, 1, NULL)",
                (recipient_username, invite["recipient_email"], password_hash)
            )
        conn.execute(
            "UPDATE email_game_invites SET recipient = ? WHERE id = ?",
            (recipient_username, invite["id"])
        )
    now = datetime.now(timezone.utc).isoformat()
    status = "declined" if request.decision == "decline" else "accepted"
    conn.execute("UPDATE email_game_invites SET responded_at = ?, recipient_color = ?, first_move = ?, status = ? WHERE id = ?",
                 (now, color, first_move, status, invite["id"]))
    game_id = None
    if status == "accepted":
        white_player = recipient_username if color == "white" else invite["sender"]
        black_player = invite["sender"] if color == "white" else recipient_username
        board = chess.Board()
        history = []
        if first_move:
            opening = board.parse_san(first_move)
            history.append({"uci": opening.uci(), "san": first_move})
            board.push(opening)
        cursor = conn.execute(
            "INSERT INTO email_games (invitation_id, white_player, black_player, fen, move_history, version, "
            "current_player, created_at, turn_started_at, last_move_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (invite["id"], white_player, black_player, board.fen(), _json_module.dumps(history), len(history),
             white_player if board.turn == chess.WHITE else black_player, now, now, now if history else None)
        )
        game_id = cursor.lastrowid
    if not invite["recipient_email"] or status == "accepted":
        conn.execute(
            "INSERT INTO community_messages (sender, content, message_type, target_users, created_at) VALUES (?, ?, 'dm', ?, ?)",
            (recipient_username, f"Invitation {status}. {reply}",
             _json_module.dumps([invite["sender"], recipient_username]), now)
        )
    conn.commit()
    conn.close()
    game_link = f"{APP_BASE_URL.rstrip('/')}/email-game.html?game_id={game_id}" if game_id else None
    recipient_label = recipient_username if status == "accepted" else invite["recipient"]
    body = f"{recipient_label} {status} your friendly chess invitation.\n\n{reply}\n"
    if game_link:
        body += f"\nView the board (sign-in required): {game_link}\n"
    emailed = True
    try:
        _send_invite_email(
            inviter["email"], f"Chess invitation response from {invite['recipient']}", body,
            _game_invite_response_email_html(recipient_label, status, reply, game_link)
        )
    except (RuntimeError, smtplib.SMTPException, OSError):
        emailed = False
    return {"success": True, "message": "Your decision has been recorded.", "status": status,
            "color": color, "first_move": first_move, "game_id": game_id, "emailed": emailed,
            "username": recipient_username if status == "accepted" else None}


def _email_game_user(authorization: Optional[str]) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign-in required.")
    payload = verify_jwt_token(authorization[7:])
    if not payload or not payload.get("username"):
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    conn = get_db()
    try:
        user = conn.execute("SELECT username, is_admin FROM users WHERE username = ?", (payload["username"],)).fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="Account no longer exists.")
        return dict(user)
    finally:
        conn.close()


def _email_game_record(row: sqlite3.Row) -> dict:
    game = dict(row)
    game["move_history"] = _json_module.loads(game["move_history"])
    game["waiting_seconds"] = max(0, int((datetime.now(timezone.utc) - datetime.fromisoformat(game["turn_started_at"])).total_seconds())) if game["status"] == "active" else 0
    return game


def _email_game_capture_history(move_history: list[dict]) -> list[dict]:
    board = chess.Board()
    captured_by_white = []
    captured_by_black = []
    captures = [{"white": [], "black": []}]
    for item in move_history:
        try:
            move = chess.Move.from_uci(item["uci"])
        except (KeyError, ValueError, chess.InvalidMoveError) as exc:
            raise HTTPException(status_code=409, detail="Stored move history cannot be replayed.") from exc
        if move not in board.legal_moves:
            raise HTTPException(status_code=409, detail="Stored move history cannot be replayed.")
        captured_piece = board.piece_at(move.to_square)
        if board.is_en_passant(move):
            captured_square = move.to_square - 8 if board.turn == chess.WHITE else move.to_square + 8
            captured_piece = board.piece_at(captured_square)
        if captured_piece:
            captures_by_player = captured_by_white if board.turn == chess.WHITE else captured_by_black
            captures_by_player.append(captured_piece.symbol().lower())
        board.push(move)
        captures.append({"white": captured_by_white.copy(), "black": captured_by_black.copy()})
    return captures


def _email_game_listing(username: Optional[str], status: Optional[str], limit: int, offset: int) -> dict:
    if status and status not in ("pending", "accepted", "declined", "expired", "active", "completed"):
        raise HTTPException(status_code=400, detail="Unknown status filter.")
    conn = get_db()
    try:
        _init_community_tables(conn)
        invite_scope = " WHERE sender = ? OR recipient = ?" if username else ""
        game_scope = " WHERE white_player = ? OR black_player = ?" if username else ""
        scope_values = [username, username] if username else []
        now = datetime.now(timezone.utc).isoformat()
        invite_query = (
            "SELECT id, sender, recipient, created_at, expires_at, responded_at, recipient_color, first_move, "
            "CASE WHEN status = 'pending' AND expires_at < ? THEN 'expired' ELSE status END AS status "
            "FROM email_game_invites" + invite_scope
        )
        stats = {state: 0 for state in ("pending", "accepted", "declined", "expired")}
        for row in conn.execute("SELECT status, count(*) AS total FROM (" + invite_query + ") GROUP BY status", [now, *scope_values]):
            stats[row["status"]] = row["total"]
        stats["sent"] = sum(stats.values())
        invite_filter = " WHERE status = ?" if status else ""
        filter_values = [status] if status else []
        invite_rows = conn.execute(
            "SELECT * FROM (" + invite_query + ")" + invite_filter + " ORDER BY id DESC LIMIT ? OFFSET ?",
            [now, *scope_values, *filter_values, limit, offset]
        ).fetchall()
        game_query = "SELECT * FROM email_games" + game_scope
        game_filter = " WHERE status = ?" if status else ""
        game_total = conn.execute("SELECT count(*) FROM (" + game_query + ")" + game_filter, [*scope_values, *filter_values]).fetchone()[0]
        game_rows = conn.execute(
            "SELECT * FROM (" + game_query + ")" + game_filter + " ORDER BY id DESC LIMIT ? OFFSET ?",
            [*scope_values, *filter_values, limit, offset]
        ).fetchall()
        invite_total = conn.execute("SELECT count(*) FROM (" + invite_query + ")" + invite_filter, [now, *scope_values, *filter_values]).fetchone()[0]
        return {"success": True, "invitations": [dict(row) for row in invite_rows],
                "games": [_email_game_record(row) for row in game_rows], "invitation_stats": stats,
                "invitation_total": invite_total, "game_total": game_total, "limit": limit, "offset": offset}
    finally:
        conn.close()


@app.get("/community/email-games")
async def list_email_games(authorization: Optional[str] = Header(None), status: Optional[str] = None,
                           limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    user = _email_game_user(authorization)
    return _email_game_listing(user["username"], status, limit, offset)


@app.get("/community/admin/email-games")
async def admin_email_games(authorization: Optional[str] = Header(None), status: Optional[str] = None,
                           limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    user = _email_game_user(authorization)
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return _email_game_listing(None, status, limit, offset)


@app.get("/community/email-games/{game_id}")
async def get_email_game(game_id: int, authorization: Optional[str] = Header(None)):
    user = _email_game_user(authorization)
    conn = get_db()
    try:
        _init_community_tables(conn)
        row = conn.execute("SELECT * FROM email_games WHERE id = ? AND (white_player = ? OR black_player = ?)",
                           (game_id, user["username"], user["username"])).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Game not found.")
        game = _email_game_record(row)
        game["captured_pieces"] = _email_game_capture_history(game["move_history"])[-1]
        return {"success": True, "game": game, "username": user["username"]}
    finally:
        conn.close()


def _completed_email_game(conn: sqlite3.Connection, game_id: int, username: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM email_games WHERE id = ? AND status = 'completed' AND (white_player = ? OR black_player = ?)",
        (game_id, username, username)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Completed game not found.")
    return row


def _email_game_pgn(row: sqlite3.Row) -> str:
    game = chess.pgn.Game()
    game.headers["Event"] = "Chess AI Email Game"
    game.headers["Site"] = "Chess AI App"
    try:
        game.headers["Date"] = datetime.fromisoformat(row["created_at"]).strftime("%Y.%m.%d")
    except (TypeError, ValueError):
        game.headers["Date"] = "????.??.??"
    game.headers["Round"] = "-"
    game.headers["White"] = row["white_player"]
    game.headers["Black"] = row["black_player"]
    game.headers["Result"] = row["result"] or "*"

    board = chess.Board()
    node = game
    for item in _json_module.loads(row["move_history"]):
        try:
            move = chess.Move.from_uci(item["uci"])
        except (KeyError, ValueError, chess.InvalidMoveError) as exc:
            raise HTTPException(status_code=409, detail="Stored move history cannot be replayed.") from exc
        if move not in board.legal_moves:
            raise HTTPException(status_code=409, detail="Stored move history cannot be replayed.")
        node = node.add_variation(move)
        board.push(move)
    if board.fen() != row["fen"]:
        raise HTTPException(status_code=409, detail="Stored game position does not match its move history.")
    return game.accept(chess.pgn.StringExporter(headers=True, variations=False, comments=False))


@app.get("/community/email-games/{game_id}/replay")
async def replay_email_game(game_id: int, authorization: Optional[str] = Header(None)):
    user = _email_game_user(authorization)
    conn = get_db()
    try:
        _init_community_tables(conn)
        game = _completed_email_game(conn, game_id, user["username"])
        board = chess.Board()
        positions = [board.fen()]
        history = _json_module.loads(game["move_history"])
        captured_pieces = _email_game_capture_history(history)
        for item in history:
            try:
                move = chess.Move.from_uci(item["uci"])
            except (KeyError, ValueError, chess.InvalidMoveError) as exc:
                raise HTTPException(status_code=409, detail="Stored move history cannot be replayed.") from exc
            if move not in board.legal_moves:
                raise HTTPException(status_code=409, detail="Stored move history cannot be replayed.")
            board.push(move)
            positions.append(board.fen())
        if board.fen() != game["fen"]:
            raise HTTPException(status_code=409, detail="Stored game position does not match its move history.")
        return {"success": True, "positions": positions, "captured_pieces": captured_pieces,
                "move_history": history,
                "result": game["result"], "completion_reason": game["completion_reason"]}
    finally:
        conn.close()


@app.get("/community/email-games/{game_id}/pgn")
async def export_email_game_pgn(game_id: int, authorization: Optional[str] = Header(None)):
    user = _email_game_user(authorization)
    conn = get_db()
    try:
        _init_community_tables(conn)
        game = _completed_email_game(conn, game_id, user["username"])
        content = _email_game_pgn(game)
    finally:
        conn.close()
    return Response(
        content=content,
        media_type="application/x-chess-pgn",
        headers={"Content-Disposition": f'attachment; filename="email-game-{game_id}.pgn"'}
    )


@app.post("/auth/email-game-link")
async def request_email_game_link(request: EmailGameLinkRequest):
    message = "If that verified account can sign in by email, a sign-in link will be sent."
    address = request.email.strip()
    if not address or len(address) > 254:
        return {"success": True, "message": message}

    conn = get_db()
    try:
        _init_community_tables(conn)
        conn.execute("BEGIN IMMEDIATE")
        user = conn.execute(
            "SELECT username, email FROM users WHERE LOWER(email) = LOWER(?) AND is_verified = 1 AND is_admin = 0",
            (address,)
        ).fetchone()
        now = datetime.now(timezone.utc)
        if user:
            recent = conn.execute(
                "SELECT 1 FROM email_game_magic_links WHERE username = ? AND created_at > ? LIMIT 1",
                (user["username"], (now - timedelta(seconds=60)).isoformat())
            ).fetchone()
            if not recent:
                token = secrets.token_urlsafe(32)
                conn.execute(
                    "INSERT INTO email_game_magic_links (username, token_hash, created_at, expires_at) VALUES (?, ?, ?, ?)",
                    (user["username"], hashlib.sha256(token.encode()).hexdigest(), now.isoformat(),
                     (now + timedelta(minutes=30)).isoformat())
                )
                link = f"{APP_BASE_URL.rstrip('/')}/email-game.html?magic_token={token}"
                _queue_email(
                    conn, user["email"], "Your Chess AI sign-in link",
                    f"Use this link to sign in to your email games. It expires in 30 minutes and can be used once.\n\n{link}\n",
                    now.isoformat()
                )
        conn.commit()
    finally:
        conn.close()
    return {"success": True, "message": message}


@app.post("/auth/email-game-link/consume")
async def consume_email_game_link(request: EmailGameLinkConsumeRequest):
    if not request.token or len(request.token) > 256:
        raise HTTPException(status_code=400, detail="This sign-in link is invalid or expired.")
    now = datetime.now(timezone.utc)
    token_hash = hashlib.sha256(request.token.encode()).hexdigest()
    conn = get_db()
    try:
        _init_community_tables(conn)
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT l.username, u.email FROM email_game_magic_links l "
            "JOIN users u ON u.username = l.username "
            "WHERE l.token_hash = ? AND l.used_at IS NULL AND l.expires_at > ? "
            "AND u.is_verified = 1 AND u.is_admin = 0",
            (token_hash, now.isoformat())
        ).fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="This sign-in link is invalid or expired.")
        updated = conn.execute(
            "UPDATE email_game_magic_links SET used_at = ? WHERE token_hash = ? AND used_at IS NULL",
            (now.isoformat(), token_hash)
        )
        if updated.rowcount != 1:
            raise HTTPException(status_code=400, detail="This sign-in link is invalid or expired.")
        conn.execute(
            "UPDATE users SET last_login = ?, last_activity = ?, current_activity = 'online' WHERE username = ?",
            (now.isoformat(), now.isoformat(), row["username"])
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {"success": True, "token": create_token(row["username"], False, row["email"]),
            "username": row["username"], "is_admin": False}


@app.post("/community/email-games/{game_id}/moves")
async def submit_email_game_move(game_id: int, request: EmailGameMoveRequest,
                                 authorization: Optional[str] = Header(None)):
    user = _email_game_user(authorization)
    if not request.move.strip() or len(request.move) > 12:
        raise HTTPException(status_code=400, detail="Enter a valid chess move.")

    conn = get_db()
    try:
        _init_community_tables(conn)
        conn.execute("BEGIN IMMEDIATE")
        game = conn.execute(
            "SELECT * FROM email_games WHERE id = ? AND (white_player = ? OR black_player = ?)",
            (game_id, user["username"], user["username"])
        ).fetchone()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found.")
        if game["status"] != "active":
            raise HTTPException(status_code=409, detail="This game is already complete.")
        if game["current_player"] != user["username"]:
            raise HTTPException(status_code=403, detail="It is not your turn.")
        if request.expected_version != game["version"]:
            raise HTTPException(status_code=409, detail="The board changed. Refresh before moving.")

        board = chess.Board(game["fen"])
        move_text = request.move.strip()
        try:
            move = board.parse_san(move_text)
        except (ValueError, chess.InvalidMoveError):
            try:
                move = chess.Move.from_uci(move_text.lower())
            except (ValueError, chess.InvalidMoveError):
                raise HTTPException(status_code=400, detail="That move is not legal in this position.")
            if move not in board.legal_moves:
                raise HTTPException(status_code=400, detail="That move is not legal in this position.")

        san = board.san(move)
        board.push(move)
        history = _json_module.loads(game["move_history"])
        history.append({"uci": move.uci(), "san": san})
        now = datetime.now(timezone.utc).isoformat()
        outcome = board.outcome()
        status = "completed" if outcome else "active"
        result = board.result() if outcome else None
        winner = None
        if outcome and outcome.winner is not None:
            winner = game["white_player"] if outcome.winner == chess.WHITE else game["black_player"]
        completion_reason = outcome.termination.name.lower() if outcome else None
        current_player = (game["white_player"] if board.turn == chess.WHITE else game["black_player"])
        updated = conn.execute(
            "UPDATE email_games SET fen = ?, move_history = ?, version = version + 1, "
            "current_player = ?, status = ?, turn_started_at = ?, last_move_at = ?, result = ?, "
            "winner = ?, completion_reason = ?, completed_at = ?, draw_offer_by = NULL "
            "WHERE id = ? AND version = ? AND status = 'active'",
            (board.fen(), _json_module.dumps(history), current_player, status, now, now, result,
             winner, completion_reason, now if outcome else None,
             game_id, request.expected_version)
        )
        if updated.rowcount != 1:
            raise HTTPException(status_code=409, detail="The board changed. Refresh before moving.")
        _cancel_pending_game_notifications(conn, game_id, now)
        if status == "active":
            next_player = conn.execute("SELECT email FROM users WHERE username = ?", (current_player,)).fetchone()
            if next_player:
                game_link = f"{APP_BASE_URL.rstrip('/')}/email-game.html?game_id={game_id}"
                next_color = "White" if current_player == game["white_player"] else "Black"
                _queue_email(
                    conn, next_player["email"], f"Your turn in a chess game with {user['username']}",
                    f"{user['username']} played {san}.\n\nNext move: {next_color}. It is your turn.\n\nView the game: {game_link}\n",
                    now, game_id, "turn"
                )
        else:
            _queue_game_result_notifications(
                conn, game_id, game["white_player"], game["black_player"], result, winner,
                completion_reason, now
            )
        conn.commit()
        result = conn.execute("SELECT * FROM email_games WHERE id = ?", (game_id,)).fetchone()
        return {"success": True, "game": _email_game_record(result), "move": {"uci": move.uci(), "san": san}}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@app.post("/community/email-games/{game_id}/actions")
async def apply_email_game_action(game_id: int, request: EmailGameActionRequest,
                                  authorization: Optional[str] = Header(None)):
    if request.action not in ("resign", "offer_draw", "accept_draw", "decline_draw"):
        raise HTTPException(status_code=400, detail="Unknown game action.")
    user = _email_game_user(authorization)
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        _init_community_tables(conn)
        conn.execute("BEGIN IMMEDIATE")
        game = conn.execute(
            "SELECT * FROM email_games WHERE id = ? AND (white_player = ? OR black_player = ?)",
            (game_id, user["username"], user["username"])
        ).fetchone()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found.")
        if game["status"] != "active":
            raise HTTPException(status_code=409, detail="This game is already complete.")
        if request.expected_version != game["version"]:
            raise HTTPException(status_code=409, detail="The board changed. Refresh before acting.")

        white_player = game["white_player"]
        black_player = game["black_player"]
        if request.action == "resign":
            winner = black_player if user["username"] == white_player else white_player
            result = "0-1" if winner == black_player else "1-0"
            reason = "resignation"
            conn.execute(
                "UPDATE email_games SET status = 'completed', result = ?, winner = ?, completion_reason = ?, "
                "completed_at = ?, draw_offer_by = NULL, version = version + 1 "
                "WHERE id = ? AND version = ? AND status = 'active'",
                (result, winner, reason, now, game_id, request.expected_version)
            )
            _queue_game_result_notifications(conn, game_id, white_player, black_player, result, winner, reason, now)
            message = "You resigned. The game is complete."
        elif request.action == "offer_draw":
            if game["current_player"] != user["username"]:
                raise HTTPException(status_code=403, detail="Only the player to move can offer a draw.")
            if game["draw_offer_by"]:
                raise HTTPException(status_code=409, detail="A draw offer is already pending.")
            opponent = black_player if user["username"] == white_player else white_player
            opponent_row = conn.execute("SELECT email FROM users WHERE username = ?", (opponent,)).fetchone()
            if not opponent_row:
                raise HTTPException(status_code=404, detail="The other player no longer has an account.")
            conn.execute(
                "UPDATE email_games SET draw_offer_by = ?, version = version + 1 WHERE id = ? AND version = ? AND status = 'active'",
                (user["username"], game_id, request.expected_version)
            )
            link = f"{APP_BASE_URL.rstrip('/')}/email-game.html?game_id={game_id}"
            next_color = _email_game_turn_color(game)
            _queue_email(
                conn, opponent_row["email"], "Draw offer in your email chess game",
                f"Next move: {next_color}. {user['username']} offered a draw.\n\nReview and respond: {link}\n",
                now, game_id, "draw_offer"
            )
            message = "Draw offer sent."
        else:
            if not game["draw_offer_by"] or game["draw_offer_by"] == user["username"]:
                raise HTTPException(status_code=409, detail="There is no draw offer from the other player.")
            offerer = game["draw_offer_by"]
            if request.action == "accept_draw":
                result, winner, reason = "1/2-1/2", None, "agreed_draw"
                conn.execute(
                    "UPDATE email_games SET status = 'completed', result = ?, winner = NULL, completion_reason = ?, "
                    "completed_at = ?, draw_offer_by = NULL, version = version + 1 "
                    "WHERE id = ? AND version = ? AND status = 'active'",
                    (result, reason, now, game_id, request.expected_version)
                )
                _queue_game_result_notifications(conn, game_id, white_player, black_player, result, winner, reason, now)
                message = "Draw accepted. The game is complete."
            else:
                offerer_row = conn.execute("SELECT email FROM users WHERE username = ?", (offerer,)).fetchone()
                conn.execute(
                    "UPDATE email_games SET draw_offer_by = NULL, version = version + 1 WHERE id = ? AND version = ? AND status = 'active'",
                    (game_id, request.expected_version)
                )
                conn.execute(
                    "UPDATE email_outbox SET status = 'cancelled', body = '', claimed_until = NULL, "
                    "last_error = 'Draw offer was declined' "
                    "WHERE game_id = ? AND notification_type = 'draw_offer' AND status = 'pending'",
                    (game_id,)
                )
                if offerer_row:
                    link = f"{APP_BASE_URL.rstrip('/')}/email-game.html?game_id={game_id}"
                    next_color = _email_game_turn_color(game)
                    _queue_email(
                        conn, offerer_row["email"], "Your draw offer was declined",
                        f"Next move: {next_color}. {user['username']} declined your draw offer.\n\nView the game: {link}\n",
                        now, game_id, "draw_response"
                    )
                message = "Draw offer declined."

        conn.commit()
        updated = conn.execute("SELECT * FROM email_games WHERE id = ?", (game_id,)).fetchone()
        return {"success": True, "message": message, "game": _email_game_record(updated)}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@app.post("/community/email-games/{game_id}/remind")
async def remind_email_game_player(game_id: int, authorization: Optional[str] = Header(None)):
    user = _email_game_user(authorization)
    now = datetime.now(timezone.utc)
    conn = get_db()
    try:
        _init_community_tables(conn)
        conn.execute("BEGIN IMMEDIATE")
        game = conn.execute(
            "SELECT * FROM email_games WHERE id = ? AND (white_player = ? OR black_player = ?)",
            (game_id, user["username"], user["username"])
        ).fetchone()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found.")
        if game["status"] != "active":
            raise HTTPException(status_code=409, detail="This game is already complete.")
        if game["current_player"] == user["username"]:
            raise HTTPException(status_code=409, detail="It is your turn; a reminder is not needed.")
        if game["last_reminder_at"]:
            last_reminder = datetime.fromisoformat(game["last_reminder_at"])
            if last_reminder.tzinfo is None:
                last_reminder = last_reminder.replace(tzinfo=timezone.utc)
            if now - last_reminder < timedelta(hours=24):
                raise HTTPException(status_code=429, detail="A reminder was already sent within the last 24 hours.")
        recipient = conn.execute("SELECT email FROM users WHERE username = ?", (game["current_player"],)).fetchone()
        if not recipient:
            raise HTTPException(status_code=404, detail="The player to move no longer has an account.")
        game_link = f"{APP_BASE_URL.rstrip('/')}/email-game.html?game_id={game_id}"
        next_color = _email_game_turn_color(game)
        _queue_email(
            conn, recipient["email"], "Reminder: your chess game is waiting for your move",
            f"Next move: {next_color}. {user['username']} is waiting for your move.\n\nView the game: {game_link}\n",
            now.isoformat(), game_id, "reminder"
        )
        conn.execute("UPDATE email_games SET last_reminder_at = ? WHERE id = ?", (now.isoformat(), game_id))
        conn.commit()
        return {"success": True, "message": "Reminder queued for email delivery.",
                "last_reminder_at": now.isoformat()}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@app.post("/community/clear-activity")
async def clear_game_activity(authorization: Optional[str] = Header(None)):
    """Clear the current user's game activity status shown to admins."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}
    payload = verify_jwt_token(authorization.replace("Bearer ", ""))
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}

    username = payload.get("username")
    conn = get_db()
    _init_community_tables(conn)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        "INSERT INTO community_messages (sender, content, message_type, created_at) VALUES (?, ?, 'game_status_clear', ?)",
        (username, '', now)
    )
    conn.commit()
    conn.close()
    return {"success": True}


# ========== Rewards Endpoints ==========

CLASSIC_GAMES_CATALOG = {
    'opera-game':         {'name': 'The Opera Game',          'badge': '🎭', 'title': 'Opera Maestro'},
    'immortal-game':      {'name': 'The Immortal Game',       'badge': '♾️',  'title': 'Immortal Scholar'},
    'evergreen-game':     {'name': 'The Evergreen Game',      'badge': '🌿', 'title': 'Evergreen Aficionado'},
    'game-of-century':    {'name': 'Game of the Century',     'badge': '🏆', 'title': 'Century Witness'},
    'fischer-spassky-g6': {'name': 'Fischer vs Spassky G6',   'badge': '⚔️',  'title': 'Cold War Classic'},
    'kasparov-topalov':   {'name': "Kasparov's Immortal",     'badge': '👑', 'title': "Kasparov's Devotee"},
}

GRAND_SCHOLAR_BADGE = {'badge': '🎓', 'title': 'Grand Scholar', 'description': 'Reviewed all 6 classic games'}


class CompleteReviewRequest(BaseModel):
    game_key: str


@app.post("/rewards/complete-review")
async def complete_review(
    request: CompleteReviewRequest,
    authorization: Optional[str] = Header(None)
):
    """Record that the authenticated user has completed a classic game review."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}
    payload = verify_jwt_token(authorization.replace("Bearer ", ""))
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}

    game_key = request.game_key.strip()
    if game_key not in CLASSIC_GAMES_CATALOG:
        return {"success": False, "message": f"Unknown game key: {game_key}"}

    username = payload.get("username")
    now = datetime.now(timezone.utc).isoformat()

    conn = get_db()
    cursor = conn.cursor()

    # Insert if not already recorded (UNIQUE constraint prevents duplicates)
    cursor.execute(
        "INSERT OR IGNORE INTO classic_game_reviews (username, game_key, completed_at) VALUES (?, ?, ?)",
        (username, game_key, now)
    )
    newly_completed = cursor.rowcount == 1
    conn.commit()

    # Fetch all completed game keys for this user
    cursor.execute(
        "SELECT game_key FROM classic_game_reviews WHERE username = ?",
        (username,)
    )
    completed_keys = {row["game_key"] for row in cursor.fetchall()}
    conn.close()

    game_info = CLASSIC_GAMES_CATALOG[game_key]
    all_complete = completed_keys >= set(CLASSIC_GAMES_CATALOG.keys())

    return {
        "success": True,
        "newly_completed": newly_completed,
        "game_key": game_key,
        "game_name": game_info["name"],
        "badge": game_info["badge"],
        "badge_title": game_info["title"],
        "completed_count": len(completed_keys),
        "total_games": len(CLASSIC_GAMES_CATALOG),
        "grand_scholar_unlocked": all_complete and newly_completed and len(completed_keys) == len(CLASSIC_GAMES_CATALOG),
    }


@app.get("/rewards/my-reviews")
async def my_reviews(authorization: Optional[str] = Header(None)):
    """Return the authenticated user's classic game review progress and earned badges."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}
    payload = verify_jwt_token(authorization.replace("Bearer ", ""))
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}

    username = payload.get("username")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT game_key, completed_at FROM classic_game_reviews WHERE username = ? ORDER BY completed_at",
        (username,)
    )
    rows = cursor.fetchall()
    conn.close()

    completed = {row["game_key"]: row["completed_at"] for row in rows}

    games = []
    for key, info in CLASSIC_GAMES_CATALOG.items():
        games.append({
            "game_key": key,
            "game_name": info["name"],
            "badge": info["badge"],
            "badge_title": info["title"],
            "completed": key in completed,
            "completed_at": completed.get(key),
        })

    all_complete = len(completed) == len(CLASSIC_GAMES_CATALOG)
    return {
        "success": True,
        "username": username,
        "games": games,
        "completed_count": len(completed),
        "total_games": len(CLASSIC_GAMES_CATALOG),
        "grand_scholar": all_complete,
        "grand_scholar_badge": GRAND_SCHOLAR_BADGE if all_complete else None,
    }


# ========== Feedback Endpoints ==========

FEEDBACK_CATEGORIES = ('bug', 'suggestion', 'feature')
FEEDBACK_CATEGORY_LABELS = {
    'bug': 'Bug Report',
    'suggestion': 'Suggestion',
    'feature': 'Feature Request',
}


class FeedbackRequest(BaseModel):
    category: str
    message: str


@app.post("/feedback/submit")
async def submit_feedback(
    request: FeedbackRequest,
    authorization: Optional[str] = Header(None)
):
    """Submit a feedback message. Requires authentication."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}
    payload = verify_jwt_token(authorization.replace("Bearer ", ""))
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}

    category = request.category.strip().lower()
    if category not in FEEDBACK_CATEGORIES:
        return {"success": False, "message": f"Invalid category. Must be one of: {', '.join(FEEDBACK_CATEGORIES)}"}

    message = request.message.strip()
    if not message:
        return {"success": False, "message": "Message cannot be empty."}
    if len(message) > 2000:
        return {"success": False, "message": "Message too long (max 2000 characters)."}

    username = payload.get("username")
    now = datetime.now(timezone.utc).isoformat()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO feedback (username, category, message, created_at) VALUES (?, ?, ?, ?)",
        (username, category, message, now)
    )
    conn.commit()
    feedback_id = cursor.lastrowid
    conn.close()

    return {"success": True, "id": feedback_id, "message": "Feedback submitted. Thank you!"}


@app.get("/feedback/list")
async def list_feedback(
    status: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """Return all feedback. Admin only."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}
    payload = verify_jwt_token(authorization.replace("Bearer ", ""))
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}
    if not payload.get("is_admin"):
        return {"success": False, "message": "Admin privileges required."}

    conn = get_db()
    cursor = conn.cursor()
    if status in ('open', 'resolved'):
        cursor.execute(
            "SELECT id, username, category, message, status, created_at, resolved_at FROM feedback WHERE status = ? ORDER BY created_at DESC",
            (status,)
        )
    else:
        cursor.execute(
            "SELECT id, username, category, message, status, created_at, resolved_at FROM feedback ORDER BY created_at DESC"
        )
    rows = cursor.fetchall()
    conn.close()

    return {
        "success": True,
        "feedback": [
            {
                "id": row["id"],
                "username": row["username"],
                "category": row["category"],
                "category_label": FEEDBACK_CATEGORY_LABELS.get(row["category"], row["category"]),
                "message": row["message"],
                "status": row["status"],
                "created_at": row["created_at"],
                "resolved_at": row["resolved_at"],
            }
            for row in rows
        ]
    }


@app.post("/feedback/{feedback_id}/resolve")
async def resolve_feedback(
    feedback_id: int,
    authorization: Optional[str] = Header(None)
):
    """Mark a feedback item as resolved (or re-open if already resolved). Admin only."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}
    payload = verify_jwt_token(authorization.replace("Bearer ", ""))
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}
    if not payload.get("is_admin"):
        return {"success": False, "message": "Admin privileges required."}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, status FROM feedback WHERE id = ?", (feedback_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": "Feedback not found."}

    new_status = 'open' if row["status"] == 'resolved' else 'resolved'
    resolved_at = datetime.now(timezone.utc).isoformat() if new_status == 'resolved' else None
    cursor.execute(
        "UPDATE feedback SET status = ?, resolved_at = ? WHERE id = ?",
        (new_status, resolved_at, feedback_id)
    )
    conn.commit()
    conn.close()
    return {"success": True, "status": new_status}


@app.delete("/feedback/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    authorization: Optional[str] = Header(None)
):
    """Delete a feedback item. Admin only."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"success": False, "message": "Authorization required."}
    payload = verify_jwt_token(authorization.replace("Bearer ", ""))
    if not payload:
        return {"success": False, "message": "Invalid or expired token."}
    if not payload.get("is_admin"):
        return {"success": False, "message": "Admin privileges required."}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    if not deleted:
        return {"success": False, "message": "Feedback not found."}
    return {"success": True}