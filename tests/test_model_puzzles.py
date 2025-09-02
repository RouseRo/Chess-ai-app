import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import json
import chess
from src.ai_player import AIPlayer
from src.stockfish_player import StockfishPlayer
from src.game import Game

# Use a separate config file for testing
TEST_CONFIG_FILE = 'config_pytest.json'

# Helper to get the absolute path to a file in the src directory
def get_src_path(filename):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', filename))

def load_test_config():
    """Loads the specified test configuration file."""
    with open(get_src_path(TEST_CONFIG_FILE), 'r') as f:
        return json.load(f)

def load_main_config():
    """Loads the main application configuration file to get the stockfish path."""
    with open(get_src_path('config.json'), 'r') as f:
        return json.load(f)

# Load configs once for all test setup functions
test_config = load_test_config()
main_config = load_main_config()

def load_players():
    """Loads all player configurations (AI and Stockfish) from the test config."""
    players = []
    for key, model_name in test_config.get("ai_models", {}).items():
        if not key.startswith("//"):
            players.append(('ai', key, model_name))
    for key, sf_config in test_config.get("stockfish_configs", {}).items():
        if not key.startswith("//"):
            players.append(('stockfish', key, sf_config))
    return players

def load_puzzles():
    """Loads all puzzles that have a 'mate_in' key from the test config file."""
    return [p for p in test_config.get("chess_problems", []) if "mate_in" in p]

def player_id(player_spec):
    """Creates a readable ID for each player test case."""
    player_type, key, data = player_spec
    if player_type == 'ai':
        return f"AI-{data.split('/')[-1]}"
    if player_type == 'stockfish':
        return f"Stockfish-{key}-{data['name'].replace(' ', '')}"
    return key

def puzzle_id(puzzle):
    """Creates a readable ID for each puzzle test case."""
    return puzzle['name'].replace('&', '').replace(' ', '-')

@pytest.mark.parametrize("player_spec", load_players(), ids=player_id)
@pytest.mark.parametrize("puzzle", load_puzzles(), ids=puzzle_id)
def test_puzzle_solving(player_spec, puzzle):
    """
    Tests if a player (AI or Stockfish) can solve a mate-in-N puzzle
    against a strong Stockfish defender.
    """
    player_type, player_key, player_data = player_spec
    
    # 1. Setup Player-Under-Test
    if player_type == 'ai':
        player_under_test = AIPlayer(model_name=player_data)
        strategy_prompt = test_config.get("puzzle_solving", {}).get("strategy_prompt")
    elif player_type == 'stockfish':
        stockfish_path = main_config.get("stockfish_path")
        assert stockfish_path and os.path.exists(stockfish_path), f"Stockfish path '{stockfish_path}' from main config.json is invalid."
        player_under_test = StockfishPlayer(path=stockfish_path, parameters=player_data['parameters'])
        strategy_prompt = None
    else:
        pytest.fail(f"Unknown player type: {player_type}")

    # 2. Setup Defender Player (always a strong Stockfish)
    defender_params = {"Skill Level": 20, "Minimum Thinking Time": 500}
    defender = StockfishPlayer(path=main_config.get("stockfish_path"), parameters=defender_params)

    # 3. Setup Game
    board = chess.Board(puzzle["fen"])
    moves_to_mate = puzzle["mate_in"]
    
    print(f"\nTesting player '{player_under_test.model_name}' on puzzle '{puzzle['name']}' (Mate in {moves_to_mate})...")
    print("Initial Board State:")
    print(board)

    # 4. Main Test Loop
    for i in range(moves_to_mate):
        # Player-under-test's turn
        move_uci = player_under_test.compute_move(board, strategy_message=strategy_prompt)
        assert move_uci is not None, f"Player failed to provide a move on turn {i+1}."
        
        move = chess.Move.from_uci(move_uci)
        assert move in board.legal_moves, f"Player returned an illegal move '{move_uci}' on turn {i+1}."
        board.push(move)
        print(f"  - Turn {i+1} (P): {move_uci}")

        # Check for mate. If found at any point, it's a success.
        if board.is_checkmate():
            print("\nFinal board state (Checkmate):")
            print(board)
            print(f"  - SUCCESS: Player solved {puzzle['name']} in {i + 1} moves (or fewer).")
            return # Test passes

        # Defender's turn (if not the last move)
        if i < moves_to_mate - 1:
            if board.is_game_over():
                 pytest.fail(f"Game ended prematurely (e.g., stalemate) after player's move {move_uci}.")
            
            defender_move_uci = defender.compute_move(board)
            assert defender_move_uci is not None, "Defender failed to provide a move."
            
            defender_move = chess.Move.from_uci(defender_move_uci)
            assert defender_move in board.legal_moves, f"Defender made an illegal move: {defender_move_uci}"
            board.push(defender_move)
            print(f"  - Turn {i+1} (D): {defender_move_uci}")

    # 5. Final check
    if not board.is_checkmate():
        print("\nFinal board state (not a checkmate):")
        print(board)
        pytest.fail(f"Player failed to deliver checkmate within {moves_to_mate} moves.")
