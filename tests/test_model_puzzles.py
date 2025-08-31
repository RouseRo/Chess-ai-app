import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import json
import chess
from src.ai_player import AIPlayer
from src.game import Game

# Helper to get the absolute path to a file in the src directory
def get_src_path(filename):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', filename))

def load_models():
    """Loads AI model names from the config file."""
    with open(get_src_path('config.json'), 'r') as f:
        config = json.load(f)
    return list(config["ai_models"].values())

def load_puzzles():
    """Loads mate-in-1 puzzles from the positions file."""
    with open(get_src_path('endgame_positions.json'), 'r') as f:
        positions = json.load(f)
    # Filter for puzzles that are explicitly marked as "mate in 1"
    return [p for p in positions if p.get("mate_in") == 1]

def puzzle_id(puzzle):
    """Creates a readable ID for each puzzle test case."""
    return puzzle['name'].replace(" ", "-")

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
    
    # 2. Get AI Move
    # This prompt is highly specific to guide the AI to the correct output format.
    strategy_prompt = "You are a chess engine. Your task is to find the single best move that results in immediate checkmate. Your answer must only be the move in UCI format (e.g., e2e4, f1h1)."
    
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
    assert game.board.is_checkmate(), f"The move {move_uci} did not result in a checkmate."
    print(f"  - SUCCESS: Model {model_name} solved {puzzle['name']} with {move_uci}.")
