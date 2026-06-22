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
def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
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
async def verify(request: TokenRequest):
    """Verify a JWT token."""
    payload = verify_jwt_token(request.token)
    
    if payload:
        return {
            "valid": True,
            "username": payload.get("username"),
            "is_admin": payload.get("is_admin", False),
            "email": payload.get("email", "")
        }
    
    return {"valid": False, "message": "Invalid or expired token."}


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