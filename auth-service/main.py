"""
Authentication Service for Chess AI App.
Uses SQLite database for user storage.
"""

from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3
import os
import secrets
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from threading import Lock

app = FastAPI(title="Chess Auth Service", version="1.0.0")

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
    print(f"[AUTH] Database path: {DATABASE_PATH}")
    init_db()
    print(f"[AUTH] Service started")
    
    # List users
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, is_admin, is_verified FROM users")
    users = cursor.fetchall()
    print(f"[AUTH] Users in database: {[dict(u) for u in users]}")
    conn.close()


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
        
        return {
            "success": True,
            "message": "Registration successful! Please check your email for verification."
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
    """Return list of currently online users."""
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

    online = []
    for row in rows:
        if _is_online(row["last_activity"], row["current_activity"]):
            online.append({
                "username": row["username"],
                "activity": row["current_activity"] or "online"
            })
    return {"success": True, "users": online}


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

    if sender.lower() == recipient.lower():
        return {"success": False, "message": "Cannot invite yourself."}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE LOWER(username) = LOWER(?)", (recipient,))
    recipient_row = cursor.fetchone()
    if not recipient_row:
        conn.close()
        return {"success": False, "message": "User not found."}

    actual_recipient = recipient_row["username"]
    _init_community_tables(conn)
    now = datetime.now(timezone.utc).isoformat()
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