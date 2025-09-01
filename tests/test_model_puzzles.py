import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import json
import chess
from src.ai_player import AIPlayer
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

# Load the config once for all test setup functions
config = load_test_config()

def load_models():
    """Loads AI model names from the test config file."""
    return [v for k, v in config["ai_models"].items() if not k.startswith("//")]

def load_puzzles():
    """Loads mate-in-1 puzzles from the test config file."""
    return [p for p in config.get("chess_problems", []) if p.get("mate_in") == 1]

def puzzle_id(puzzle):
    """Creates a readable ID for each puzzle test case."""
    # Remove special characters like '&' to avoid pytest -k parsing issues
    name = puzzle['name'].replace('&', '').replace(' ', '-')
    return name

@pytest.mark.parametrize("model_name", load_models())
@pytest.mark.parametrize("puzzle", load_puzzles(), ids=puzzle_id)
def test_mate_in_1_puzzle(model_name, puzzle):
    """
    Tests if an AI model can solve a mate-in-1 puzzle.
    
    Note: This is an integration test that makes real API calls.
    """
    print(f"\nTesting model '{model_name}' on puzzle '{puzzle['name']}'...")

    # 1. Setup
    ai_player = AIPlayer(model_name=model_name)
    game = Game(ai_player, AIPlayer("opponent")) # Opponent player is just a placeholder
    
    assert game.set_board_from_fen(puzzle["fen"]), f"Failed to load FEN for puzzle {puzzle['name']}"
    
    print("Board state:")
    print(game.board)
    
    # 2. Get AI Move - Load prompt from the test config file
    strategy_prompt = "You are a chess grandmaster. Your task is to find the single best move that results in immediate checkmate. Verify that there are no legal moves for the opponent after your move. Your answer must only be the move in UCI format (e.g., e2e4, f1h1)."
    
    move_uci = ai_player.compute_move(game.board, strategy_message=strategy_prompt)
    
    assert move_uci is not None, "AI failed to provide a move."
    print(f"  - AI suggested move: {move_uci}")

    # 3. Validate the move
    try:
        move = chess.Move.from_uci(move_uci)
        assert move in game.board.legal_moves, f"AI returned an illegal move: {move_uci}"
    except ValueError:
        pytest.fail(f"AI returned an invalid UCI move string: {move_uci}")

    # 4. Check for Checkmate
    game.board.push(move)
    if not game.board.is_checkmate():
        print("\nBoard state after AI's move (not a checkmate):")
        print(game.board)
        pytest.fail(f"The move {move_uci} did not result in a checkmate.")
    
    print(f"  - SUCCESS: Model {model_name} solved {puzzle['name']} with {move_uci}.")
