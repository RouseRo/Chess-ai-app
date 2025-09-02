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
    # Load AI Models
    for key, model_name in test_config.get("ai_models", {}).items():
        if not key.startswith("//"):
            players.append(('ai', key, model_name))
    # Load Stockfish Configs
    for key, sf_config in test_config.get("stockfish_configs", {}).items():
        if not key.startswith("//"):
            players.append(('stockfish', key, sf_config))
    return players

def load_puzzles():
    """Loads mate-in-1 puzzles from the test config file."""
    return [p for p in test_config.get("chess_problems", []) if p.get("mate_in") == 1]

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
def test_mate_in_1_puzzle(player_spec, puzzle):
    """
    Tests if a player (AI or Stockfish) can solve a mate-in-1 puzzle.
    """
    player_type, player_key, player_data = player_spec
    
    # 1. Setup Player
    if player_type == 'ai':
        player = AIPlayer(model_name=player_data)
        strategy_prompt = test_config.get("puzzle_solving", {}).get("strategy_prompt")
        assert strategy_prompt, "Puzzle solving strategy prompt not found in test config."
    elif player_type == 'stockfish':
        stockfish_path = main_config.get("stockfish_path")
        assert stockfish_path and os.path.exists(stockfish_path), f"Stockfish path '{stockfish_path}' from main config.json is invalid."
        player = StockfishPlayer(path=stockfish_path, parameters=player_data['parameters'])
        strategy_prompt = None # Stockfish doesn't use a text prompt
    else:
        pytest.fail(f"Unknown player type: {player_type}")

    print(f"\nTesting player '{player.model_name}' on puzzle '{puzzle['name']}'...")

    # 2. Setup Game
    game = Game(player, AIPlayer("opponent")) # Opponent is a placeholder
    assert game.set_board_from_fen(puzzle["fen"]), f"Failed to load FEN for puzzle {puzzle['name']}"
    
    print("Board state:")
    print(game.board)
    
    # 3. Get Move
    move_uci = player.compute_move(game.board, strategy_message=strategy_prompt)
    
    assert move_uci is not None, "Player failed to provide a move."
    print(f"  - Player suggested move: {move_uci}")

    # 4. Validate and Check for Checkmate
    try:
        move = chess.Move.from_uci(move_uci)
        assert move in game.board.legal_moves, f"Player returned an illegal move: {move_uci}"
    except ValueError:
        pytest.fail(f"Player returned an invalid UCI move string: {move_uci}")

    game.board.push(move)
    if not game.board.is_checkmate():
        print("\nBoard state after player's move (not a checkmate):")
        print(game.board)
        pytest.fail(f"The move {move_uci} did not result in a checkmate.")
    
    print(f"  - SUCCESS: Player {player.model_name} solved {puzzle['name']} with {move_uci}.")
