from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
import sys
import os
from typing import Optional

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.user_manager import UserManager

app = FastAPI(
    title="Chess AI Admin Service",
    description="Admin management service for Chess AI App",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize UserManager with shared user_data directory
user_manager = UserManager(data_dir="user_data")

# ========== Pydantic Models ==========

class DeleteUserRequest(BaseModel):
    username: str

class PromoteUserRequest(BaseModel):
    username: str

class DemoteUserRequest(BaseModel):
    username: str

class AddModelRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    model_id: str
    name: str
    type: str
    provider: Optional[str] = None
    skill_level: Optional[int] = None

class RemoveModelRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    model_id: str

class UpdateModelRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    model_id: str
    updates: dict

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# ========== Helper Functions ==========

def get_admin_user(authorization: str = Header(None)) -> str:
    """Verify admin token and return admin username."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = authorization.replace("Bearer ", "")
    
    if not user_manager.is_admin(token):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    success, username = user_manager.verify_token(token)
    if not success:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return username

# ========== Health Check ==========

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "chess-ai-admin-service",
        "version": "1.0.0"
    }

# ========== Admin User Management Endpoints ==========

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
async def delete_user(req: DeleteUserRequest, authorization: str = Header(None)):
    """Delete a user (admin only)."""
    admin_username = get_admin_user(authorization)
    
    success, message = user_manager.delete_user(req.username, admin_username)
    
    return {
        "success": success,
        "message": message,
        "admin": admin_username
    }

@app.post("/admin/users/promote")
async def promote_user(req: PromoteUserRequest, authorization: str = Header(None)):
    """Promote user to admin (admin only)."""
    admin_username = get_admin_user(authorization)
    
    success, message = user_manager.promote_user_to_admin(req.username)
    
    return {
        "success": success,
        "message": message,
        "admin": admin_username
    }

@app.post("/admin/users/demote")
async def demote_user(req: DemoteUserRequest, authorization: str = Header(None)):
    """Demote admin user to regular user (admin only)."""
    admin_username = get_admin_user(authorization)
    
    success, message = user_manager.demote_user_from_admin(req.username)
    
    return {
        "success": success,
        "message": message,
        "admin": admin_username
    }

# ========== Admin AI Models Endpoints ==========

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
async def add_model(req: AddModelRequest, authorization: str = Header(None)):
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
async def remove_model(req: RemoveModelRequest, authorization: str = Header(None)):
    """Remove an AI model (admin only)."""
    admin_username = get_admin_user(authorization)
    
    success, message = user_manager.remove_ai_model(req.model_id)
    
    return {
        "success": success,
        "message": message,
        "admin": admin_username
    }

@app.post("/admin/models/update")
async def update_model(req: UpdateModelRequest, authorization: str = Header(None)):
    """Update AI model configuration (admin only)."""
    admin_username = get_admin_user(authorization)
    
    success, message = user_manager.update_ai_model(req.model_id, req.updates)
    
    return {
        "success": success,
        "message": message,
        "admin": admin_username
    }

# ========== Admin System Statistics ==========

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

# ========== Admin Password Change ==========

@app.post("/admin/change-password")
async def change_password(req: ChangePasswordRequest, authorization: str = Header(None)):
    """Change admin password."""
    admin_username = get_admin_user(authorization)
    
    success, message = user_manager.change_password(
        admin_username,
        req.old_password,
        req.new_password
    )
    
    return {
        "success": success,
        "message": message
    }

# ========== Auth Endpoints ==========

@app.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Admin login."""
    success, token = user_manager.authenticate_admin(req.username, req.password)
    
    if not success:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    return {
        "access_token": token,
        "token_type": "bearer"
    }

# ========== Static Files ==========

@app.get("/")
async def serve_admin_dashboard():
    """Serve admin dashboard HTML."""
    return FileResponse("admin-service/static/admin.html", media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)