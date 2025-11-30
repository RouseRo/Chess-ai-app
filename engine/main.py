from fastapi import FastAPI, Response, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chess
import os
import sys

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import UserManager - use correct path
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

# ----------- Authentication Models -----------

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class LogoutRequest(BaseModel):
    token: str

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
    return {
        "success": success,
        "message": message,
        "token": token
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

    user_info = user_manager.get_user_info(username)
    return {
        "success": True,
        "username": username,
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
    return {"Hello": "World"}