from fastapi import FastAPI, Response
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import chess  # <-- Added import

app = FastAPI()

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

class ExpertRequest(BaseModel):
    question: str = None
    fen: str = None

@app.post("/expert/question")
def ask_chess_question(req: ExpertRequest):
    # Replace with your actual expert_service logic
    if req.question:
        return {"response": f"Chess Expert says: That's a great question! (Placeholder answer for: {req.question})"}
    return {"response": "Please provide a chess question."}

@app.get("/expert/joke")
def get_chess_joke():
    # Replace with your actual expert_service logic
    return {"response": "Why did the chess player bring a suitcase? Because he was traveling to the endgame!"}

@app.get("/expert/fact")
def get_chess_fact():
    return {"response": "Fun Chess Fact: The longest chess game theoretically possible is 5,949 moves!"}

@app.get("/expert/news")
def get_chess_news():
    return {"response": "Current Chess News: Visit https://www.chess.com/news for the latest updates!"}

@app.post("/expert/analyze")
def analyze_position(req: ExpertRequest):
    if req.fen:
        return {"response": f"Analysis for FEN {req.fen}: (Placeholder analysis)"}
    return {"response": "Please provide a FEN string to analyze."}

@app.get("/expert/puzzle")
def get_tactical_puzzle():
    return {"response": "Here's a tactical puzzle: (Placeholder puzzle)"}