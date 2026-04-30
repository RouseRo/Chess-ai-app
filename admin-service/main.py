from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import sqlite3
import bcrypt
from datetime import datetime

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

@app.get("/admin/users", response_model=List[UserResponse])
async def get_all_users():
    """Get list of all users."""
    users = list_all_users()
    
    user_responses = []
    for user in users:
        user_responses.append(
            UserResponse(
                username=user.get("username"),
                email=user.get("email"),
                created_at=user.get("created_at", ""),
                is_admin=bool(user.get("is_admin", 0)),
                verified=bool(user.get("is_verified", 0)),
                games_count=user.get("games_count", 0)
            )
        )
    
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