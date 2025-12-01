from fastapi import FastAPI, Response, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chess
import os
import sys

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.user_manager import UserManager

# Initialize UserManager
user_manager = UserManager(data_dir="user_data")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------- Pydantic Models -----------

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class LogoutRequest(BaseModel):
    token: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class AdminDeleteUserRequest(BaseModel):
    username: str

class AdminPromoteUserRequest(BaseModel):
    username: str

class AdminDemoteUserRequest(BaseModel):
    username: str

class AdminAddModelRequest(BaseModel):
    model_id: str
    name: str
    type: str
    provider: str = None
    skill_level: int = None

class AdminUpdateModelRequest(BaseModel):
    model_id: str
    updates: dict

class AdminRemoveModelRequest(BaseModel):
    model_id: str

# ----------- Helper Functions -----------

def get_admin_user(authorization: str = Header(None)) -> str:
    """Verify admin token and return admin username."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    
    if not user_manager.is_admin(token):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    success, username = user_manager.verify_token(token)
    if not success:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return username

# ----------- Authentication Endpoints -----------

@app.post("/auth/register")
async def register(req: RegisterRequest):
    """Register a new user."""
    success, message = user_manager.register_user(
        req.username, 
        req.email, 
        req.password
    )
    return {
        "success": success,
        "message": message
    }

@app.post("/auth/login")
async def login(req: LoginRequest):
    """Login user and return session token."""
    success, message, token = user_manager.login_user(
        req.username, 
        req.password
    )
    user_info = user_manager.get_user_info(req.username) if success else None
    return {
        "success": success,
        "message": message,
        "token": token,
        "user": user_info
    }

@app.post("/auth/logout")
async def logout(req: LogoutRequest):
    """Logout user by removing session token."""
    success = user_manager.logout_user(req.token)
    return {
        "success": success,
        "message": "Logged out successfully" if success else "Logout failed"
    }

@app.get("/auth/verify")
async def verify_token(authorization: str = Header(None)):
    """Verify session token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    success, username = user_manager.verify_token(token)

    if not success:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    is_admin = user_manager.is_admin(token)
    user_info = user_manager.get_user_info(username)
    
    return {
        "success": True,
        "username": username,
        "is_admin": is_admin,
        "user_info": user_info
    }

@app.get("/auth/user/{username}")
async def get_user(username: str, authorization: str = Header(None)):
    """Get user information (requires authentication)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    success, auth_username = user_manager.verify_token(token)

    if not success:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_info = user_manager.get_user_info(username)
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "success": True,
        "user_info": user_info
    }

@app.post("/auth/change-password")
async def change_password(req: ChangePasswordRequest, authorization: str = Header(None)):
    """Change user password."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    success, username = user_manager.verify_token(token)

    if not success:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    success, message = user_manager.change_password(username, req.old_password, req.new_password)
    
    return {
        "success": success,
        "message": message
    }

# ----------- Admin User Management Endpoints -----------

@app.get("/admin/users")
async def list_users(authorization: str = Header(None)):
    """List all users (admin only)."""
    admin_username = get_admin_user(authorization)
    users = user_manager.list_all_users()
    
    return {
        "success": True,
        "admin": admin_username,
        "total_users": len(users),
        "users": users
    }

@app.post("/admin/users/delete")
async def delete_user(req: AdminDeleteUserRequest, authorization: str = Header(None)):
    """Delete a user (admin only)."""
    admin_username = get_admin_user(authorization)
    
    success, message = user_manager.delete_user(req.username, admin_username)
    
    return {
        "success": success,
        "message": message,
        "admin": admin_username
    }

@app.post("/admin/users/promote")
async def promote_user(req: AdminPromoteUserRequest, authorization: str = Header(None)):
    """Promote user to admin (admin only)."""
    admin_username = get_admin_user(authorization)
    
    success, message = user_manager.promote_user_to_admin(req.username)
    
    return {
        "success": success,
        "message": message,
        "admin": admin_username
    }

@app.post("/admin/users/demote")
async def demote_user(req: AdminDemoteUserRequest, authorization: str = Header(None)):
    """Demote admin user to regular user (admin only)."""
    admin_username = get_admin_user(authorization)
    
    success, message = user_manager.demote_user_from_admin(req.username)
    
    return {
        "success": success,
        "message": message,
        "admin": admin_username
    }

# ----------- Admin AI Model Management Endpoints -----------

@app.get("/admin/models")
async def get_models(authorization: str = Header(None)):
    """Get all AI models (admin only)."""
    admin_username = get_admin_user(authorization)
    models = user_manager.get_ai_models()
    
    return {
        "success": True,
        "admin": admin_username,
        "models": models.get('models', [])
    }

@app.post("/admin/models/add")
async def add_model(req: AdminAddModelRequest, authorization: str = Header(None)):
    """Add a new AI model (admin only)."""
    admin_username = get_admin_user(authorization)
    
    model_data = {
        "name": req.name,
        "type": req.type,
        "enabled": False
    }
    
    if req.provider:
        model_data["provider"] = req.provider
    if req.skill_level:
        model_data["skill_level"] = req.skill_level
    
    success, message = user_manager.add_ai_model(req.model_id, model_data)
    
    return {
        "success": success,
        "message": message,
        "admin": admin_username
    }

@app.post("/admin/models/remove")
async def remove_model(req: AdminRemoveModelRequest, authorization: str = Header(None)):
    """Remove an AI model (admin only)."""
    admin_username = get_admin_user(authorization)
    
    success, message = user_manager.remove_ai_model(req.model_id)
    
    return {
        "success": success,
        "message": message,
        "admin": admin_username
    }

@app.post("/admin/models/update")
async def update_model(req: AdminUpdateModelRequest, authorization: str = Header(None)):
    """Update AI model configuration (admin only)."""
    admin_username = get_admin_user(authorization)
    
    success, message = user_manager.update_ai_model(req.model_id, req.updates)
    
    return {
        "success": success,
        "message": message,
        "admin": admin_username
    }

# ----------- Admin System Statistics -----------

@app.get("/admin/stats")
async def get_system_stats(authorization: str = Header(None)):
    """Get system statistics (admin only)."""
    admin_username = get_admin_user(authorization)
    stats = user_manager.get_system_stats()
    
    return {
        "success": True,
        "admin": admin_username,
        "stats": stats
    }

# ----------- Game Endpoints -----------

class MoveRequest(BaseModel):
    fen: str
    move: str = None

@app.post("/move")
async def move(request: Request):
    data = await request.json()
    move = data.get("move")
    fen = data.get("fen")
    board = chess.Board(fen)

    if move is not None:
        user_move_uci = move.replace("-", "")
        board.push_uci(user_move_uci)

    import random
    legal_moves = list(board.legal_moves)
    if legal_moves:
        engine_move = random.choice(legal_moves)
        board.push(engine_move)
        engine_move_uci = engine_move.uci()
        status = "Move accepted"
    else:
        engine_move_uci = None
        status = "No legal moves for engine"

    new_fen = board.fen()
    return JSONResponse({
        "status": status,
        "fen": new_fen,
        "engine_move": engine_move_uci,
        "source": "chess-engine-1"
    })

@app.options("/move")
def options_move():
    return Response(status_code=200)

class ExpertRequest(BaseModel):
    question: str = None

@app.post("/expert/question")
def ask_chess_question(req: ExpertRequest):
    return {"response": "Chess expertise response"}

@app.get("/expert/fact")
def get_chess_fact():
    return {"response": "A fun chess fact"}

@app.get("/expert/joke")
def get_expert_joke():
    return {"response": "A chess joke"}

@app.get("/expert/news")
def get_chess_news():
    return {"response": "Latest chess news"}

@app.get("/")
def read_root():
    return {"Hello": "World", "message": "Chess AI App Running"}