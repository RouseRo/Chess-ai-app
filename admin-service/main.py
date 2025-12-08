from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import json
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

# User data directory - consistent across all services
USER_DATA_DIR = "/app/user_data/users"

print(f"\n[INIT] ========== ADMIN SERVICE INITIALIZATION ==========")
print(f"[INIT] USER_DATA_DIR: {USER_DATA_DIR}")
print(f"[INIT] os.path.exists(USER_DATA_DIR): {os.path.exists(USER_DATA_DIR)}")
print(f"[INIT] os.path.isdir(USER_DATA_DIR): {os.path.isdir(USER_DATA_DIR)}")

if os.path.exists(USER_DATA_DIR):
    try:
        contents = os.listdir(USER_DATA_DIR)
        print(f"[INIT] Contents of {USER_DATA_DIR}: {contents}")
    except Exception as e:
        print(f"[INIT] Error listing {USER_DATA_DIR}: {e}")

profiles_dir = os.path.join(USER_DATA_DIR, "profiles")
print(f"[INIT] profiles_dir: {profiles_dir}")
print(f"[INIT] os.path.exists(profiles_dir): {os.path.exists(profiles_dir)}")
print(f"[INIT] os.path.isdir(profiles_dir): {os.path.isdir(profiles_dir)}")

if os.path.exists(profiles_dir):
    try:
        files = os.listdir(profiles_dir)
        print(f"[INIT] Contents of {profiles_dir}: {files}")
    except Exception as e:
        print(f"[INIT] Error listing {profiles_dir}: {e}")

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

def get_user_file_path(username: str) -> str:
    """Get the file path for a user profile."""
    return os.path.join(USER_DATA_DIR, "profiles", f"{username}.json")

def get_user(username: str) -> Optional[dict]:
    """Get user data from file."""
    user_file = get_user_file_path(username)
    if os.path.exists(user_file):
        try:
            with open(user_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading user file: {e}")
            return None
    return None

def list_all_users() -> list:
    """List all users."""
    users = []
    profiles_dir = os.path.join(USER_DATA_DIR, "profiles")
    
    print(f"\n[LIST_USERS] ========== START ==========")
    print(f"[LIST_USERS] profiles_dir: {profiles_dir}")
    print(f"[LIST_USERS] os.path.exists(profiles_dir): {os.path.exists(profiles_dir)}")
    print(f"[LIST_USERS] os.path.isdir(profiles_dir): {os.path.isdir(profiles_dir)}")
    
    if not os.path.exists(profiles_dir):
        print(f"[LIST_USERS] *** PROFILES DIRECTORY DOES NOT EXIST ***")
        print(f"[LIST_USERS] Attempting to create it...")
        try:
            os.makedirs(profiles_dir, exist_ok=True)
            print(f"[LIST_USERS] Created {profiles_dir}")
        except Exception as e:
            print(f"[LIST_USERS] Failed to create directory: {e}")
        print(f"[LIST_USERS] ========== END (empty) ==========\n")
        return users
    
    try:
        files = os.listdir(profiles_dir)
        print(f"[LIST_USERS] os.listdir() returned: {files}")
        print(f"[LIST_USERS] Number of items: {len(files)}")
        
        for filename in files:
            print(f"[LIST_USERS] Processing: {filename}")
            if filename.endswith('.json'):
                filepath = os.path.join(profiles_dir, filename)
                print(f"[LIST_USERS]   Full path: {filepath}")
                print(f"[LIST_USERS]   File exists: {os.path.exists(filepath)}")
                print(f"[LIST_USERS]   Is file: {os.path.isfile(filepath)}")
                
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                        print(f"[LIST_USERS]   File size: {len(content)} bytes")
                        user_data = json.loads(content)
                        users.append(user_data)
                        print(f"[LIST_USERS]   ✓ Loaded user: {user_data.get('username')}")
                except json.JSONDecodeError as e:
                    print(f"[LIST_USERS]   ✗ JSON Error: {e}")
                except IOError as e:
                    print(f"[LIST_USERS]   ✗ IO Error: {e}")
                except Exception as e:
                    print(f"[LIST_USERS]   ✗ Unexpected error: {type(e).__name__}: {e}")
            else:
                print(f"[LIST_USERS]   Skipping (not .json): {filename}")
        
    except PermissionError as e:
        print(f"[LIST_USERS] ✗ Permission Error: {e}")
    except Exception as e:
        print(f"[LIST_USERS] ✗ Error listing directory: {type(e).__name__}: {e}")
    
    print(f"[LIST_USERS] Total users loaded: {len(users)}")
    print(f"[LIST_USERS] ========== END ==========\n")
    return users

def save_user(username: str, user_data: dict) -> bool:
    """Save user data to file."""
    try:
        profiles_dir = os.path.join(USER_DATA_DIR, "profiles")
        os.makedirs(profiles_dir, exist_ok=True)
        
        user_file = get_user_file_path(username)
        with open(user_file, 'w') as f:
            json.dump(user_data, f, indent=2)
        return True
    except IOError as e:
        print(f"Error saving user: {e}")
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

@app.get("/admin/users", response_model=List[UserResponse])
async def get_all_users():
    """Get list of all users."""
    print(f"\n[ENDPOINT] GET /admin/users called")
    users = list_all_users()
    print(f"[ENDPOINT] list_all_users() returned {len(users)} users")
    
    user_responses = []
    for user in users:
        user_responses.append(
            UserResponse(
                username=user.get("username"),
                email=user.get("email"),
                created_at=user.get("created_at", ""),
                is_admin=user.get("is_admin", False),
                verified=user.get("verified", False),
                games_count=len(user.get("games", []))
            )
        )
    
    print(f"[ENDPOINT] Returning {len(user_responses)} user responses")
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
        last_login=user.get("last_login"),
        is_admin=user.get("is_admin", False),
        verified=user.get("verified", False),
        games=user.get("games", [])
    )

@app.post("/admin/users/{username}/promote", response_model=AdminActionResponse)
async def promote_user_to_admin(username: str):
    """Promote a user to admin."""
    user = get_user(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("is_admin", False):
        raise HTTPException(status_code=400, detail="User is already an admin")
    
    user["is_admin"] = True
    
    if save_user(username, user):
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
    
    if not user.get("is_admin", False):
        raise HTTPException(status_code=400, detail="User is not an admin")
    
    user["is_admin"] = False
    
    if save_user(username, user):
        return {
            "success": True,
            "message": f"User {username} demoted from admin"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to demote user")

@app.post("/admin/users/{username}/verify", response_model=AdminActionResponse)
async def verify_user(username: str):
    """Verify a user's email."""
    user = get_user(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("verified", False):
        raise HTTPException(status_code=400, detail="User is already verified")
    
    user["verified"] = True
    
    if save_user(username, user):
        return {
            "success": True,
            "message": f"User {username} verified"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to verify user")

@app.delete("/admin/users/{username}", response_model=AdminActionResponse)
async def delete_user(username: str):
    """Delete a user account."""
    user_file = get_user_file_path(username)
    
    if not os.path.exists(user_file):
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        os.remove(user_file)
        return {
            "success": True,
            "message": f"User {username} deleted"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")

@app.get("/admin/stats")
async def get_admin_stats():
    """Get admin dashboard statistics."""
    users = list_all_users()
    
    total_users = len(users)
    admin_count = sum(1 for user in users if user.get("is_admin", False))
    verified_count = sum(1 for user in users if user.get("verified", False))
    total_games = sum(len(user.get("games", [])) for user in users)
    
    return {
        "total_users": total_users,
        "admin_count": admin_count,
        "verified_users": verified_count,
        "total_games": total_games,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)