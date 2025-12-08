from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import os
import jwt
import bcrypt
import json
from datetime import datetime, timedelta

app = FastAPI(
    title="Chess AI Auth Service",
    description="Authentication and authorization service for Chess AI App",
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

print(f"[DEBUG] Auth Service USER_DATA_DIR: {USER_DATA_DIR}")
print(f"[DEBUG] Directory exists: {os.path.exists(USER_DATA_DIR)}")
print(f"[DEBUG] Profiles dir: {os.path.join(USER_DATA_DIR, 'profiles')}")

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "chess-ai-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# ========== Pydantic Models ==========

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class TokenResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    is_admin: Optional[bool] = None
    message: Optional[str] = None

class LogoutRequest(BaseModel):
    token: str

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
    
    if not os.path.exists(profiles_dir):
        return users
    
    try:
        for filename in os.listdir(profiles_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(profiles_dir, filename), 'r') as f:
                        user_data = json.load(f)
                        users.append(user_data)
                except (json.JSONDecodeError, IOError):
                    continue
    except Exception as e:
        print(f"Error listing users: {e}")
    
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

def create_access_token(username: str, is_admin: bool) -> str:
    """Create JWT token for user."""
    payload = {
        "username": username,
        "is_admin": is_admin,
        "exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def verify_token(token: str) -> tuple[bool, Optional[str], Optional[bool]]:
    """Verify JWT token and return (success, username, is_admin)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("username")
        is_admin = payload.get("is_admin", False)
        
        if username is None:
            return False, None, None
        
        return True, username, is_admin
    except jwt.ExpiredSignatureError:
        return False, None, None
    except jwt.InvalidTokenError:
        return False, None, None

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    password_bytes = password.encode('utf-8')
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    if not hashed_password or hashed_password == '':
        return plain_password == ''
    
    try:
        password_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception as e:
        print(f"Password verification error: {e}")
        return plain_password == hashed_password

# ========== Health Check ==========

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "chess-ai-auth-service",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "status": "online",
        "service": "chess-ai-auth-service",
        "version": "1.0.0"
    }

# ========== Authentication Endpoints ==========

@app.post("/auth/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    """Register a new user."""
    if not req.username or not req.email or not req.password:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    if len(req.password) > 72:
        raise HTTPException(status_code=400, detail="Password must be less than 72 characters")
    
    users = list_all_users()
    if any(user.get('username') == req.username for user in users):
        raise HTTPException(status_code=409, detail="Username already exists")
    
    if any(user.get('email') == req.email for user in users):
        raise HTTPException(status_code=409, detail="Email already registered")
    
    hashed_password = hash_password(req.password)
    
    user_data = {
        "username": req.username,
        "email": req.email,
        "password_hash": hashed_password,
        "created_at": datetime.utcnow().isoformat(),
        "is_admin": False,
        "verified": True,
        "games": []
    }
    
    if save_user(req.username, user_data):
        return {
            "success": True,
            "message": "User registered successfully",
            "username": req.username,
            "email": req.email,
            "is_admin": False
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to register user")

@app.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Login user and return JWT token."""
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    user = get_user(req.username)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    password_hash = user.get('password_hash', user.get('password', ''))
    
    if not verify_password(req.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token = create_access_token(req.username, user.get('is_admin', False))
    
    return {
        "success": True,
        "token": token,
        "username": req.username,
        "email": user.get('email'),
        "is_admin": user.get('is_admin', False)
    }

@app.post("/auth/verify")
async def verify(authorization: str = Header(None)):
    """Verify JWT token validity."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    token = authorization.replace("Bearer ", "")
    success, username, is_admin = verify_token(token)
    
    if not success:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user = get_user(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "success": True,
        "username": username,
        "email": user.get('email'),
        "is_admin": is_admin
    }

@app.post("/auth/refresh")
async def refresh_token(authorization: str = Header(None)):
    """Refresh expired JWT token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    token = authorization.replace("Bearer ", "")
    success, username, is_admin = verify_token(token)
    
    if not success:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    new_token = create_access_token(username, is_admin)
    
    return {
        "success": True,
        "token": new_token,
        "username": username,
        "is_admin": is_admin
    }

@app.post("/auth/logout")
async def logout(req: LogoutRequest):
    """Logout user (invalidate token on client side)."""
    return {
        "success": True,
        "message": "Logout successful"
    }

@app.post("/auth/change-password")
async def change_password(req: ChangePasswordRequest, authorization: str = Header(None)):
    """Change user password."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    token = authorization.replace("Bearer ", "")
    success, username, is_admin = verify_token(token)
    
    if not success:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user = get_user(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    password_hash = user.get('password_hash', user.get('password', ''))
    if not verify_password(req.old_password, password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    if len(req.new_password) > 72:
        raise HTTPException(status_code=400, detail="Password must be less than 72 characters")
    
    new_password_hash = hash_password(req.new_password)
    
    user['password_hash'] = new_password_hash
    if 'password' in user:
        del user['password']
    
    if save_user(username, user):
        return {
            "success": True,
            "message": "Password changed successfully"
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to change password")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)