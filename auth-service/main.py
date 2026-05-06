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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    return {"success": True, "message": "Logged out successfully."}


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