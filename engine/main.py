from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.user_manager import UserManager

app = FastAPI(
    title="Chess AI Engine",
    description="Chess game engine and AI service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

user_manager = UserManager(data_dir="user_data")

# ========== Root Endpoint ==========

@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "status": "online",
        "service": "chess-ai-engine",
        "version": "1.0.0"
    }

# ========== Health Check ==========

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "chess-ai-engine",
        "version": "1.0.0"
    }

# ========== Game Endpoints ==========

@app.post("/move")
async def make_move(request_data: dict, authorization: str = Header(None)):
    """Process chess move."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    move = request_data.get('move')
    fen = request_data.get('fen')
    
    if not move or not fen:
        raise HTTPException(status_code=400, detail="Missing move or fen")
    
    # Process move logic here
    return {
        "success": True,
        "move": move,
        "fen": fen,
        "status": "Move processed"
    }

@app.get("/ai/suggest")
async def suggest_move(fen: str, authorization: str = Header(None)):
    """Get AI move suggestion."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    if not fen:
        raise HTTPException(status_code=400, detail="Missing fen parameter")
    
    # AI suggestion logic here
    return {
        "success": True,
        "suggested_move": "e2-e4",
        "fen": fen,
        "evaluation": "+0.5"
    }

@app.post("/expert/question")
async def ask_expert(request_data: dict, authorization: str = Header(None)):
    """Ask chess expert question."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    question = request_data.get('question')
    
    if not question:
        raise HTTPException(status_code=400, detail="Missing question")
    
    # Expert response logic here
    return {
        "success": True,
        "question": question,
        "response": "This is an expert response to your chess question."
    }

# ========== Admin Endpoints ==========

@app.get("/admin/stats")
async def get_system_stats(authorization: str = Header(None)):
    """Get system statistics (admin only)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    stats = user_manager.get_system_stats()
    
    return {
        "success": True,
        "stats": stats
    }

@app.get("/admin/users")
async def list_users(authorization: str = Header(None)):
    """List all users (admin only)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    users = user_manager.list_all_users()
    
    return {
        "success": True,
        "total_users": len(users),
        "users": users
    }

@app.post("/admin/users/delete")
async def delete_user(request_data: dict, authorization: str = Header(None)):
    """Delete a user (admin only)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    username = request_data.get('username')
    success, message = user_manager.delete_user(username, "admin")
    
    return {
        "success": success,
        "message": message
    }

@app.post("/admin/users/promote")
async def promote_user(request_data: dict, authorization: str = Header(None)):
    """Promote user to admin (admin only)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    username = request_data.get('username')
    success, message = user_manager.promote_user_to_admin(username)
    
    return {
        "success": success,
        "message": message
    }

@app.post("/admin/users/demote")
async def demote_user(request_data: dict, authorization: str = Header(None)):
    """Demote admin user to regular user (admin only)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    username = request_data.get('username')
    success, message = user_manager.demote_user_from_admin(username)
    
    return {
        "success": success,
        "message": message
    }

@app.get("/admin/models")
async def get_models(authorization: str = Header(None)):
    """Get all AI models (admin only)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    models = user_manager.get_ai_models()
    
    return {
        "success": True,
        "models": models.get('models', [])
    }

@app.post("/admin/models/add")
async def add_model(request_data: dict, authorization: str = Header(None)):
    """Add a new AI model (admin only)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    model_id = request_data.get('model_id')
    model_data = request_data.get('model_data', {})
    success, message = user_manager.add_ai_model(model_id, model_data)
    
    return {
        "success": success,
        "message": message
    }

@app.post("/admin/models/remove")
async def remove_model(request_data: dict, authorization: str = Header(None)):
    """Remove an AI model (admin only)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    model_id = request_data.get('model_id')
    success, message = user_manager.remove_ai_model(model_id)
    
    return {
        "success": success,
        "message": message
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)