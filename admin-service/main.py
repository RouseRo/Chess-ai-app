from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import sqlite3
import bcrypt
import json
from datetime import datetime, timezone, timedelta

app = FastAPI(
    title="Chess AI Admin Service",
    description="Admin dashboard and user management service for Chess AI App",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DATABASE_PATH = os.environ.get("DATABASE_PATH", "/app/data/users.db")

print(f"\n[INIT] ========== ADMIN SERVICE INITIALIZATION ==========")
print(f"[INIT] DATABASE_PATH: {DATABASE_PATH}")
print(f"[INIT] Database exists: {os.path.exists(DATABASE_PATH)}")
print(f"[INIT] ========== END INITIALIZATION ==========\n")

# ========== Pydantic Models ==========

class UserResponse(BaseModel):
    username: str
    email: str
    created_at: str
    is_admin: bool
    verified: bool
    games_count: int
    last_login: Optional[str] = None
    last_activity: Optional[str] = None
    current_activity: Optional[str] = None
    is_online: bool = False
    status_label: str = "Offline"
    game_status: str = ""

class UserDetailResponse(BaseModel):
    username: str
    email: str
    created_at: str
    last_login: Optional[str] = None
    is_admin: bool
    verified: bool
    games: List[str] = []

class AdminActionResponse(BaseModel):
    success: bool
    message: str

class AIModelResponse(BaseModel):
    id: str
    name: str
    type: str
    skill_level: Optional[int] = None
    provider: Optional[str] = None
    enabled: bool

# ========== Helper Functions ==========

def get_db_connection():
    """Get SQLite database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_user(username: str) -> Optional[dict]:
    """Get user data from database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"Error reading user: {e}")
        return None

def _get_game_status(username: str, conn) -> str:
    """Derive a human-readable game activity status from recent community messages."""
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        cursor = conn.cursor()

        # Ensure table exists before querying
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS community_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                message_type TEXT DEFAULT 'chat',
                target_users TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        events = []

        # Did this user send a game invite?
        cursor.execute(
            """SELECT target_users, created_at FROM community_messages
               WHERE sender = ? AND message_type = 'game_invite' AND created_at >= ?
               ORDER BY created_at DESC LIMIT 1""",
            (username, cutoff)
        )
        invite_sent = cursor.fetchone()
        if invite_sent:
            try:
                targets = json.loads(invite_sent["target_users"] or "[]")
                target = next((t for t in targets if t != username), None)
            except Exception:
                target = None
            label = f"Invited {target} to play chess" if target else "Sent a game invitation"
            events.append((invite_sent["created_at"], label))

        # Did this user accept an invite (sent a DM with acceptance text)?
        cursor.execute(
            """SELECT content, target_users, created_at FROM community_messages
               WHERE sender = ? AND message_type = 'dm'
               AND content LIKE '%I accepted your game invitation%' AND created_at >= ?
               ORDER BY created_at DESC LIMIT 1""",
            (username, cutoff)
        )
        acceptance_sent = cursor.fetchone()
        if acceptance_sent:
            content = acceptance_sent["content"]
            color = "White" if "play as White" in content else ("Black" if "play as Black" in content else "?")
            try:
                targets = json.loads(acceptance_sent["target_users"] or "[]")
                inviter = next((t for t in targets if t != username), None)
            except Exception:
                inviter = None
            label = f"Accepted invite from {inviter}, playing as {color}" if inviter else f"Accepted an invite, playing as {color}"
            events.append((acceptance_sent["created_at"], label))

        # Did this user receive an acceptance DM?
        cursor.execute(
            """SELECT sender, content, created_at FROM community_messages
               WHERE message_type = 'dm' AND target_users LIKE ?
               AND content LIKE '%I accepted your game invitation%' AND created_at >= ?
               ORDER BY created_at DESC LIMIT 1""",
            (f'%"{username}"%', cutoff)
        )
        acceptance_received = cursor.fetchone()
        if acceptance_received:
            content = acceptance_received["content"]
            accepter = acceptance_received["sender"]
            color = "White" if "play as White" in content else ("Black" if "play as Black" in content else "?")
            events.append((acceptance_received["created_at"], f"Invite accepted by {accepter} ({color})"))

        if not events:
            return ""
        events.sort(key=lambda x: x[0], reverse=True)
        return events[0][1]
    except Exception as e:
        print(f"[game_status] Error for {username}: {e}")
        return ""


def list_all_users() -> list:
    """List all users from database."""
    users = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            users.append(dict(row))
    except Exception as e:
        print(f"Error listing users: {e}")
    
    return users

def get_stats() -> dict:
    """Get system statistics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) as total FROM users WHERE is_admin = 1")
        admin_count = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) as total FROM users WHERE is_verified = 1")
        verified_users = cursor.fetchone()["total"]
        
        # For now, total_games is 0 as we're not tracking games in this version
        total_games = 0
        
        conn.close()
        
        return {
            "total_users": total_users,
            "admin_count": admin_count,
            "verified_users": verified_users,
            "total_games": total_games,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {
            "total_users": 0,
            "admin_count": 0,
            "verified_users": 0,
            "total_games": 0,
            "timestamp": datetime.now().isoformat()
        }

def update_user_admin_status(username: str, is_admin: bool) -> bool:
    """Update user admin status."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_admin = ? WHERE username = ?", (is_admin, username))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating admin status: {e}")
        return False

def verify_user(username: str) -> bool:
    """Verify user email."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_verified = 1 WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error verifying user: {e}")
        return False

def delete_user(username: str) -> bool:
    """Delete a user from database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False

def load_ai_models() -> list:
    """Load AI models from JSON file."""
    models = []
    try:
        # Try multiple possible paths for the models file
        possible_paths = [
            "/app/user_data/ai_models.json",
            "/app/data/ai_models.json",
            "user_data/ai_models.json",
            "../user_data/ai_models.json",
            "./user_data/ai_models.json"
        ]
        
        print("[DEBUG] Looking for ai_models.json in these locations:")
        models_file = None
        for path in possible_paths:
            exists = os.path.exists(path)
            print(f"  - {path}: {exists}")
            if exists:
                models_file = path
                break
        
        if not models_file:
            print(f"[ERROR] ai_models.json not found. Current working directory: {os.getcwd()}")
            print(f"[ERROR] Contents of /app: {os.listdir('/app') if os.path.exists('/app') else 'N/A'}")
            return []
        
        print(f"[DEBUG] Loading AI models from: {models_file}")
        with open(models_file, 'r') as f:
            data = json.load(f)
            models = data.get("models", [])
            print(f"[DEBUG] Loaded {len(models)} AI models")
    except Exception as e:
        print(f"[ERROR] Error loading AI models: {e}")
        import traceback
        traceback.print_exc()
    
    return models

# ========== Health Check ==========

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "chess-ai-admin-service",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "status": "online",
        "service": "chess-ai-admin-service",
        "version": "1.0.0"
    }

# ========== Admin Endpoints ==========

@app.get("/admin/stats")
async def admin_stats():
    """Get system statistics."""
    return get_stats()

@app.get("/admin/models", response_model=List[AIModelResponse])
async def get_ai_models():
    """Get list of available AI models."""
    models_data = load_ai_models()
    
    models_responses = []
    for model in models_data:
        models_responses.append(
            AIModelResponse(
                id=model.get("id"),
                name=model.get("name"),
                type=model.get("type"),
                skill_level=model.get("skill_level"),
                provider=model.get("provider"),
                enabled=model.get("enabled", False)
            )
        )
    
    return models_responses

@app.get("/admin/users", response_model=List[UserResponse])
async def get_all_users():
    """Get list of all users."""
    users = list_all_users()
    now = datetime.now(timezone.utc)
    # Open a single connection for game status queries across all users
    try:
        _gs_conn = get_db_connection()
        _gs_conn.row_factory = sqlite3.Row
    except Exception:
        _gs_conn = None

    user_responses = []
    for user in users:
        last_activity = user.get("last_activity")
        current_activity = user.get("current_activity") or "offline"
        is_online = False
        status_label = "Offline"

        if last_activity:
            try:
                dt = datetime.fromisoformat(last_activity)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                minutes_ago = (now - dt).total_seconds() / 60
                if minutes_ago <= 5:
                    is_online = True
                    if current_activity == "playing":
                        status_label = "Playing a Game"
                    else:
                        status_label = "Online"
                elif minutes_ago <= 60:
                    mins = int(minutes_ago)
                    status_label = f"Last seen {mins}m ago"
                else:
                    hours = int(minutes_ago / 60)
                    status_label = f"Last seen {hours}h ago"
            except Exception:
                pass

        user_responses.append(
            UserResponse(
                username=user.get("username"),
                email=user.get("email"),
                created_at=user.get("created_at", ""),
                is_admin=bool(user.get("is_admin", 0)),
                verified=bool(user.get("is_verified", 0)),
                games_count=user.get("games_count", 0),
                last_login=user.get("last_login"),
                last_activity=last_activity,
                current_activity=current_activity,
                is_online=is_online,
                status_label=status_label,
                game_status=_get_game_status(user.get("username"), _gs_conn) if _gs_conn else ""
            )
        )

    if _gs_conn:
        _gs_conn.close()
    return user_responses

@app.get("/admin/users/{username}", response_model=UserDetailResponse)
async def get_user_details(username: str):
    """Get detailed user information."""
    user = get_user(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserDetailResponse(
        username=user.get("username"),
        email=user.get("email"),
        created_at=user.get("created_at", ""),
        is_admin=bool(user.get("is_admin", 0)),
        verified=bool(user.get("is_verified", 0)),
        games=[]
    )

@app.post("/admin/users/{username}/promote", response_model=AdminActionResponse)
async def promote_user_to_admin(username: str):
    """Promote a user to admin."""
    user = get_user(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("is_admin", 0):
        raise HTTPException(status_code=400, detail="User is already an admin")
    
    if update_user_admin_status(username, True):
        return {
            "success": True,
            "message": f"User {username} promoted to admin"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to promote user")

@app.post("/admin/users/{username}/demote", response_model=AdminActionResponse)
async def demote_user_from_admin(username: str):
    """Demote an admin user to regular user."""
    user = get_user(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.get("is_admin", 0):
        raise HTTPException(status_code=400, detail="User is not an admin")
    
    if update_user_admin_status(username, False):
        return {
            "success": True,
            "message": f"User {username} demoted from admin"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to demote user")

@app.post("/admin/users/{username}/verify", response_model=AdminActionResponse)
async def verify_user_endpoint(username: str):
    """Verify a user's email."""
    user = get_user(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("is_verified", 0):
        raise HTTPException(status_code=400, detail="User is already verified")
    
    if verify_user(username):
        return {
            "success": True,
            "message": f"User {username} verified"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to verify user")

@app.delete("/admin/users/{username}", response_model=AdminActionResponse)
async def delete_user_endpoint(username: str):
    """Delete a user account."""
    user = get_user(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if delete_user(username):
        return {
            "success": True,
            "message": f"User {username} deleted"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to delete user")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)