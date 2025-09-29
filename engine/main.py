from fastapi import FastAPI, Response
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
def make_move(req: MoveRequest):
    board = chess.Board(req.fen)
    try:
        board.push_san(req.move)
        return {"fen": board.fen(), "status": "ok"}
    except Exception as e:
        return {"fen": req.fen, "status": f"error: {str(e)}"}

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