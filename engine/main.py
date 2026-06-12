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
    """Ask chess expert question with optional live game context."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    question = request_data.get('question')
    fen = request_data.get('fen')
    move_history = request_data.get('move_history', [])   # list of SAN strings
    turn = request_data.get('turn')                        # 'white' or 'black'
    move_count = request_data.get('move_count', 0)
    is_check = request_data.get('is_check', False)
    is_checkmate = request_data.get('is_checkmate', False)
    is_draw = request_data.get('is_draw', False)
    captured_by_white = request_data.get('captured_by_white', [])
    captured_by_black = request_data.get('captured_by_black', [])
    
    if not question:
        raise HTTPException(status_code=400, detail="Missing question")
    
    print(f"[EXPERT] Received question: '{question}', FEN: {fen[:30] if fen else 'None'}...")

    # Build a contextual prompt when a live game is in progress
    contextual_question = question
    if fen and fen != 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1':
        context_parts = [f"Current position (FEN): {fen}"]
        if move_count:
            context_parts.append(f"Move number: {move_count}")
        if turn:
            context_parts.append(f"It is {turn}'s turn.")
        if is_checkmate:
            context_parts.append("The game has ended in checkmate.")
        elif is_draw:
            context_parts.append("The game has ended in a draw.")
        elif is_check:
            context_parts.append(f"The {turn} king is in check.")
        if move_history:
            pgn_moves = []
            for i in range(0, len(move_history), 2):
                num = i // 2 + 1
                w = move_history[i] if i < len(move_history) else ''
                b = move_history[i + 1] if i + 1 < len(move_history) else ''
                pgn_moves.append(f"{num}. {w} {b}".strip())
            context_parts.append("Moves so far: " + " ".join(pgn_moves))
        piece_names = {'p': 'pawn', 'r': 'rook', 'b': 'bishop', 'n': 'knight', 'q': 'queen'}
        if captured_by_white:
            names = [piece_names.get(p, p) for p in captured_by_white]
            context_parts.append(f"White has captured: {', '.join(names)}.")
        if captured_by_black:
            names = [piece_names.get(p, p) for p in captured_by_black]
            context_parts.append(f"Black has captured: {', '.join(names)}.")
        contextual_question = "\n".join(context_parts) + f"\n\nQuestion: {question}"

    try:
        if AI_AVAILABLE:
            print("[EXPERT] Using AIPlayer directly for expert response")
            player = AIPlayer(model_name="anthropic/claude-fable-5")
            response = player.get_chess_fact_or_answer(contextual_question)
            print(f"[EXPERT] Response received: {response[:100] if response else 'None'}...")

            if not response or response.strip() == "":
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
        else:
            print("[EXPERT] AIPlayer not available, using positional fallback")
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
    """Generate a position-aware response using python-chess when AI is unavailable."""
    print(f"[EXPERT FALLBACK] Generating response for: '{question}'")

    # If we have a FEN, extract basic position facts using python-chess
    position_context = ""
    if fen:
        try:
            board = chess.Board(fen)
            turn = "White" if board.turn == chess.WHITE else "Black"
            legal_count = board.legal_moves.count()
            in_check = board.is_check()

            piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                            chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
            white_material = sum(piece_values.get(pt, 0)
                                 for pt in piece_values
                                 for _ in board.pieces(pt, chess.WHITE))
            black_material = sum(piece_values.get(pt, 0)
                                 for pt in piece_values
                                 for _ in board.pieces(pt, chess.BLACK))
            diff = white_material - black_material

            material_str = "material is equal"
            if diff > 0:
                material_str = f"White is ahead by {diff} point(s)"
            elif diff < 0:
                material_str = f"Black is ahead by {abs(diff)} point(s)"

            check_str = " The king is in check." if in_check else ""
            position_context = (
                f"Position summary: It is {turn}'s turn with {legal_count} legal moves available. "
                f"{material_str}.{check_str}\n\n"
            )
        except Exception:
            pass

    question_lower = question.lower()

    if "best move" in question_lower or "suggest" in question_lower or "what move" in question_lower:
        return (position_context +
                "Move selection tip: Look for forcing moves first (checks, captures, threats). "
                "Then consider improving your worst-placed piece or creating a passed pawn.")

    if "opening" in question_lower or "start" in question_lower:
        return (position_context +
                "Opening principles: Control the center (e4/d4), develop knights before bishops, "
                "castle early, and connect your rooks.")

    if "endgame" in question_lower:
        return (position_context +
                "Endgame principles: Activate your king, push passed pawns, and create threats. "
                "Practice K+P vs K and rook endgames.")

    if "tactic" in question_lower or "pin" in question_lower or "fork" in question_lower or "combination" in question_lower:
        return (position_context +
                "Tactical motifs: Look for pins, forks, skewers, and discovered attacks. "
                "Always check if your opponent has threats before executing a combination.")

    if "strateg" in question_lower or "plan" in question_lower or "analyze" in question_lower:
        return (position_context +
                "Strategic principles: Control the center, develop pieces quickly, ensure king safety, "
                "and improve your worst-placed piece.")

    if "winning" in question_lower or "advantage" in question_lower or "material" in question_lower:
        return position_context + "Use Stockfish or an AI model for a deeper evaluation of this position."

    return (position_context +
            "Chess tip: Look for forcing moves (checks, captures, threats), consider your opponent's "
            "threats, and improve your worst-placed piece.")

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