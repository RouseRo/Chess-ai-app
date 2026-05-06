from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
import os
import chess
import random
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.user_manager import UserManager

# Import AI players with error logging
AI_AVAILABLE = False
STOCKFISH_AVAILABLE = False

try:
    from src.ai_player import AIPlayer
    AI_AVAILABLE = True
    print("✓ AIPlayer loaded successfully")
except ImportError as e:
    print(f"✗ AIPlayer not available: {e}")

try:
    from src.stockfish_player import StockfishPlayer
    STOCKFISH_AVAILABLE = True
    print("✓ StockfishPlayer loaded successfully")
except ImportError as e:
    print(f"✗ StockfishPlayer not available: {e}")

# Try to use python-chess's built-in engine support
try:
    import chess.engine
    CHESS_ENGINE_AVAILABLE = True
    print("✓ chess.engine available")
except ImportError:
    CHESS_ENGINE_AVAILABLE = False
    print("✗ chess.engine not available")

# Find Stockfish at startup
def find_stockfish():
    """Find Stockfish executable path."""
    possible_paths = [
        os.environ.get('STOCKFISH_PATH', ''),
        '/usr/games/stockfish',
        '/usr/bin/stockfish',
        '/usr/local/bin/stockfish',
        '/app/stockfish',
        'stockfish'
    ]
    
    # Also try to find using 'which' command
    try:
        result = subprocess.run(['which', 'stockfish'], capture_output=True, text=True)
        if result.returncode == 0:
            which_path = result.stdout.strip()
            if which_path and which_path not in possible_paths:
                possible_paths.insert(0, which_path)
                print(f"✓ Found Stockfish via 'which': {which_path}")
    except Exception as e:
        print(f"Could not run 'which stockfish': {e}")
    
    for path in possible_paths:
        if path and os.path.isfile(path):
            print(f"✓ Stockfish found at: {path}")
            return path
    
    print("✗ Stockfish not found in any known location")
    return None

STOCKFISH_PATH = find_stockfish()

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

# Stockfish engine instance
stockfish_engine = None

def get_stockfish_engine():
    """Get Stockfish engine using python-chess."""
    global stockfish_engine
    if stockfish_engine is None and CHESS_ENGINE_AVAILABLE and STOCKFISH_PATH:
        try:
            stockfish_engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
            print(f"✓ Stockfish engine initialized")
        except Exception as e:
            print(f"✗ Failed to initialize Stockfish engine: {e}")
    return stockfish_engine

# ========== Root Endpoint ==========

@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "status": "online",
        "service": "chess-ai-engine",
        "version": "1.0.0",
        "ai_available": AI_AVAILABLE,
        "stockfish_available": STOCKFISH_AVAILABLE,
        "chess_engine_available": CHESS_ENGINE_AVAILABLE,
        "stockfish_path": STOCKFISH_PATH
    }

# ========== Health Check ==========

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "chess-ai-engine"
    }

# ========== Game Endpoints ==========

@app.post("/move")
async def make_move(request_data: dict, authorization: str = Header(None)):
    """Process chess move and get AI response."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    move = request_data.get('move')
    fen = request_data.get('fen')
    request_ai_move = request_data.get('request_ai_move', True)
    ai_type = request_data.get('ai_type', 'stockfish')
    skill_level = request_data.get('skill_level', 10)
    
    print(f"[MOVE] Received: move={move}, fen={fen[:30] if fen else 'None'}..., request_ai_move={request_ai_move}, ai_type={ai_type}")
    
    if not fen:
        raise HTTPException(status_code=400, detail="Missing fen")
    
    try:
        board = chess.Board(fen)
        
        ai_move_uci = None
        ai_move_san = None
        new_fen = fen
        status = "Move processed"
        
        if request_ai_move and not board.is_game_over():
            print(f"[AI] Requesting AI move, type={ai_type}, stockfish_path={STOCKFISH_PATH}")
            
            # Try Stockfish first via python-chess engine
            if ai_type == 'stockfish' and CHESS_ENGINE_AVAILABLE and STOCKFISH_PATH:
                engine = get_stockfish_engine()
                if engine:
                    try:
                        # Set skill level (0-20)
                        engine.configure({"Skill Level": min(20, max(0, skill_level))})
                        result = engine.play(board, chess.engine.Limit(time=1.0))
                        ai_move_uci = result.move.uci()
                        print(f"[AI] Stockfish move: {ai_move_uci}")
                    except Exception as e:
                        print(f"[AI] Stockfish error: {e}")
            
            # Fallback to StockfishPlayer class
            if not ai_move_uci and STOCKFISH_AVAILABLE:
                try:
                    from src.stockfish_player import StockfishPlayer
                    player = StockfishPlayer(skill_level=skill_level)
                    ai_move_uci = player.get_move(board)
                    print(f"[AI] StockfishPlayer move: {ai_move_uci}")
                except Exception as e:
                    print(f"[AI] StockfishPlayer error: {e}")
            
            # Try AIPlayer for LLM-based AI
            if not ai_move_uci and AI_AVAILABLE and ai_type in ['openai', 'deepseek', 'gemini', 'claude', 'llama']:
                try:
                    from src.ai_player import AIPlayer
                    player = AIPlayer(model_id=ai_type)
                    ai_move_uci = player.get_move(board)
                    print(f"[AI] AIPlayer ({ai_type}) move: {ai_move_uci}")
                except Exception as e:
                    print(f"[AI] AIPlayer error: {e}")
            
            # Ultimate fallback: random legal move
            if not ai_move_uci:
                legal_moves = list(board.legal_moves)
                if legal_moves:
                    ai_move = random.choice(legal_moves)
                    ai_move_uci = ai_move.uci()
                    print(f"[AI] Random fallback move: {ai_move_uci}")
            
            # Apply AI move
            if ai_move_uci:
                try:
                    ai_move_obj = chess.Move.from_uci(ai_move_uci)
                    if ai_move_obj in board.legal_moves:
                        ai_move_san = board.san(ai_move_obj)
                        board.push(ai_move_obj)
                        new_fen = board.fen()
                        status = "AI move applied"
                        print(f"[AI] Applied move: {ai_move_san}")
                    else:
                        print(f"[AI] Move {ai_move_uci} is not legal, using random")
                        legal_moves = list(board.legal_moves)
                        if legal_moves:
                            ai_move_obj = random.choice(legal_moves)
                            ai_move_uci = ai_move_obj.uci()
                            ai_move_san = board.san(ai_move_obj)
                            board.push(ai_move_obj)
                            new_fen = board.fen()
                            status = "AI move applied (fallback)"
                except Exception as e:
                    print(f"[AI] Error applying move: {e}")
                    status = f"AI move error: {str(e)}"
        else:
            print(f"[AI] AI move not requested or game over. request_ai_move={request_ai_move}, game_over={board.is_game_over()}")
        
        # Check game status
        if board.is_checkmate():
            status = "Checkmate!"
        elif board.is_stalemate():
            status = "Stalemate!"
        elif board.is_check():
            status = "Check!"
        elif board.is_game_over():
            status = "Game over"
        
        response = {
            "success": True,
            "status": status,
            "fen": new_fen,
            "ai_move": ai_move_uci,
            "ai_move_san": ai_move_san,
            "ai_type": ai_type,
            "source": "chess-engine-1"
        }
        print(f"[MOVE] Response: ai_move={ai_move_uci}, status={status}")
        return JSONResponse(response)
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing move: {str(e)}")

@app.get("/ai/suggest")
async def suggest_move(fen: str, authorization: str = Header(None), ai_type: str = "stockfish"):
    """Get AI move suggestion."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    if not fen:
        raise HTTPException(status_code=400, detail="Missing fen parameter")
    
    try:
        board = chess.Board(fen)
        
        if board.is_game_over():
            return {"success": False, "error": "Game is over", "fen": fen}
        
        suggested_move = None
        
        if ai_type == 'stockfish' and CHESS_ENGINE_AVAILABLE and STOCKFISH_PATH:
            engine = get_stockfish_engine()
            if engine:
                try:
                    result = engine.play(board, chess.engine.Limit(time=1.0))
                    suggested_move = result.move.uci()
                except Exception as e:
                    print(f"Stockfish suggest error: {e}")
        
        if not suggested_move:
            legal_moves = list(board.legal_moves)
            if legal_moves:
                suggested_move = random.choice(legal_moves).uci()
        
        return {
            "success": True,
            "suggested_move": suggested_move,
            "fen": fen,
            "ai_type": ai_type
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error suggesting move: {str(e)}")

@app.post("/expert/question")
async def ask_expert(request_data: dict, authorization: str = Header(None)):
    """Ask chess expert question."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    question = request_data.get('question')
    fen = request_data.get('fen')
    
    if not question:
        raise HTTPException(status_code=400, detail="Missing question")
    
    print(f"[EXPERT] Received question: '{question}', FEN: {fen[:30] if fen else 'None'}...")
    
    try:
        # Try to import and use ExpertService
        try:
            from src.expert_service import ExpertService
            print("[EXPERT] ExpertService imported successfully")
            
            expert = ExpertService()
            response = expert.ask_question(question, fen)
            
            print(f"[EXPERT] Response received: {response[:100] if response else 'None'}...")
            
            # Validate response
            if not response or response.strip() == "":
                print("[EXPERT] Warning: Expert returned empty response")
                return {
                    "success": False,
                    "question": question,
                    "error": "Expert service returned empty response"
                }
            
            return {
                "success": True,
                "question": question,
                "response": response
            }
            
        except ImportError as e:
            print(f"[EXPERT] ExpertService import failed: {e}")
            print("[EXPERT] Attempting fallback...")
            
            # Fallback: Basic chess advice without expert service
            fallback_response = generate_fallback_response(question, fen)
            return {
                "success": True,
                "question": question,
                "response": fallback_response,
                "source": "fallback"
            }
    
    except Exception as e:
        print(f"[EXPERT] Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "question": question,
            "error": f"Expert service error: {str(e)}"
        }


def generate_fallback_response(question: str, fen: str = None) -> str:
    """Generate basic chess advice when ExpertService is unavailable."""
    print(f"[EXPERT FALLBACK] Generating response for: '{question}'")
    
    question_lower = question.lower()
    
    # Basic chess opening advice
    if "opening" in question_lower or "start" in question_lower:
        return "For strong openings, consider: 1.e4 (Open Game), 1.d4 (Closed Game), or 1.c4 (English Opening). Each leads to different types of positions."
    
    # Endgame advice
    if "endgame" in question_lower or "endgame" in question_lower:
        return "Key endgame principles: Activate your king, push passed pawns, and create threats. Practice fundamental endgames like K+P vs K and Rook endgames."
    
    # Tactical advice
    if "tactic" in question_lower or "combination" in question_lower or "pin" in question_lower or "fork" in question_lower:
        return "Tactical motifs: Look for pins, forks, skewers, and discovered attacks. Always check if your opponent has threats and look for forcing moves (checks, captures, threats)."
    
    # Strategy advice
    if "strateg" in question_lower or "plan" in question_lower:
        return "Strategic principles: Control the center, develop pieces quickly, ensure king safety, and create a coherent plan. Improve your worst-placed piece."
    
    # Move evaluation
    if "best move" in question_lower or "should i" in question_lower:
        return "To find the best move: 1) Look for forcing moves (checks, captures, threats), 2) Evaluate resulting positions, 3) Consider opponent's best responses, 4) Compare candidate moves."
    
    # Default helpful response
    return "Chess tip: Always look for forcing moves (checks, captures, threats), consider your opponent's threats, and improve your worst-placed piece. Study classic games and positions!"

# ========== Admin Endpoints ==========

@app.get("/admin/stats")
async def get_system_stats(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    return {"success": True, "stats": user_manager.get_system_stats()}

@app.get("/admin/users")
async def list_users(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    users = user_manager.list_all_users()
    return {"success": True, "total_users": len(users), "users": users}

@app.post("/admin/users/delete")
async def delete_user(request_data: dict, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    success, message = user_manager.delete_user(request_data.get('username'), "admin")
    return {"success": success, "message": message}

@app.post("/admin/users/promote")
async def promote_user(request_data: dict, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    success, message = user_manager.promote_user_to_admin(request_data.get('username'))
    return {"success": success, "message": message}

@app.post("/admin/users/demote")
async def demote_user(request_data: dict, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    success, message = user_manager.demote_user_from_admin(request_data.get('username'))
    return {"success": success, "message": message}

@app.get("/admin/models")
async def get_models(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    models = user_manager.get_ai_models()
    return {"success": True, "models": models.get('models', [])}

@app.post("/admin/models/add")
async def add_model(request_data: dict, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    success, message = user_manager.add_ai_model(request_data.get('model_id'), request_data.get('model_data', {}))
    return {"success": success, "message": message}

@app.post("/admin/models/remove")
async def remove_model(request_data: dict, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    success, message = user_manager.remove_ai_model(request_data.get('model_id'))
    return {"success": success, "message": message}

# Cleanup on shutdown
@app.on_event("shutdown")
def shutdown_event():
    global stockfish_engine
    if stockfish_engine:
        stockfish_engine.quit()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)