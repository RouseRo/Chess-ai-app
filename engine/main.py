from fastapi import FastAPI, Response, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import chess
import os

# Import the refactored ExpertService and AIPlayer
from src.expert_service import ExpertService
from src.ai_player import AIPlayer

# Dummy UI for API context (no display, no input)
class DummyUI:
    def display_message(self, msg): pass
    def get_user_input(self, prompt): return ""

# Initialize OpenRouter AIPlayer with a valid default model name
ai_player = AIPlayer(model_name="openai/gpt-3.5-turbo")

# Instantiate ExpertService for API use, passing the AIPlayer instance
expert_service = ExpertService(
    ui=DummyUI(),
    expert_model_name="openai/gpt-3.5-turbo",
    ai_player=ai_player
)

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MoveRequest(BaseModel):
    fen: str
    move: str  # SAN or UCI

@app.post("/move")
async def move(request: Request):
    data = await request.json()
    move = data.get("move")
    fen = data.get("fen")
    board = chess.Board(fen)

    # Only push user's move if provided
    if move is not None:
        user_move_uci = move.replace("-", "")
        board.push_uci(user_move_uci)

    # Engine move (pick a random legal move for demo)
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

# ----------- Expert API Endpoints -----------

class ExpertRequest(BaseModel):
    question: str = None
    fen: str = None

@app.post("/expert/question")
def ask_chess_question(req: ExpertRequest):
    answer = expert_service.ask_chess_question(question=req.question)
    return {"response": answer}

@app.get("/expert/fact")
def get_chess_fact():
    return {"response": expert_service.get_fun_fact()}

@app.post("/expert/analyze")
def analyze_position(req: ExpertRequest):
    return {"response": expert_service.analyze_position(position_fen=req.fen)}

@app.get("/expert/opening")
def get_opening_advice():
    return {"response": expert_service.opening_advice()}

@app.get("/expert/news")
def get_chess_news():
    return {"response": expert_service.get_latest_chess_news()}

@app.post("/expert/ask")
def ask_expert(req: ExpertRequest):
    return {"response": expert_service.ask_expert(question=req.question)}

@app.get("/expert/joke")
def get_expert_joke():
    return {"response": expert_service.get_a_joke()}