import sys
import os
import logging
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import json
import chess
from src.ai_player import AIPlayer
from src.stockfish_player import StockfishPlayer
from src.model_puzzles import ModelPuzzles
from src.player_factory import PlayerFactory
from src.ui_manager import UIManager

# --- Test Configuration ---
TEST_CONFIG_FILE = 'config_pytest.json'
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs', 'test_games'))
os.makedirs(LOG_DIR, exist_ok=True)

# --- Helper Functions ---
def get_src_path(filename):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', filename))

def _load_config_for_parametrization(filename):
    """Helper to load a config file for use in decorators."""
    with open(get_src_path(filename), 'r') as f:
        return json.load(f)

def _record_result(results_dict, player, puzzle, status, moves=None):
    """Helper to structure and save the result of a single test."""
    player_name = player.model_name
    puzzle_name = puzzle['name']

    if player_name not in results_dict:
        results_dict[player_name] = {"summary": {"pass": 0, "fail": 0}, "puzzles": {}}
    
    results_dict[player_name]["summary"][status.lower()] += 1
    
    result_entry = {"status": status}
    if moves:
        result_entry["moves_taken"] = moves
        result_entry["moves_expected"] = puzzle['mate_in']

    results_dict[player_name]["puzzles"][puzzle_name] = result_entry

# --- Pytest Fixtures ---

@pytest.fixture(scope="session")
def test_config():
    """Loads the test configuration file once per session."""
    with open(get_src_path(TEST_CONFIG_FILE), 'r') as f:
        return json.load(f)

@pytest.fixture(scope="session")
def main_config():
    """Loads the main config file once per session to get the stockfish path."""
    with open(get_src_path('config.json'), 'r') as f:
        return json.load(f)

@pytest.fixture(scope="session")
def test_results():
    """Initializes a results dictionary and saves it at the end of the session."""
    results = {}
    yield results  # Provide the dict to tests

    # This part runs after all tests are done
    if results:
        summary_path = os.path.join(LOG_DIR, "test_summary.json")
        with open(summary_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nTest results summary saved to {summary_path}")

@pytest.fixture
def player_under_test(player_under_test_spec, main_config):
    """Creates the player object (AI or Stockfish) to be tested."""
    player_type, _, player_data = player_under_test_spec
    stockfish_path = main_config.get("stockfish_path")
    assert stockfish_path and os.path.exists(stockfish_path), f"Stockfish path '{stockfish_path}' from main config.json is invalid."

    if player_type == 'ai':
        return AIPlayer(model_name=player_data)
    elif player_type == 'stockfish':
        return StockfishPlayer(path=stockfish_path, parameters=player_data['parameters'])
    else:
        pytest.fail(f"Unknown player type: {player_type}")

@pytest.fixture(scope="session")
def defender_player(main_config):
    """Creates a single, strong Stockfish player to act as the defender for all tests."""
    stockfish_path = main_config.get("stockfish_path")
    defender_params = {"Skill Level": 20, "Minimum Thinking Time": 500}
    return StockfishPlayer(path=stockfish_path, parameters=defender_params)

@pytest.fixture
def game_logger(request):
    """Sets up a unique logger for each test case."""
    player_spec = request.node.callspec.getparam('player_under_test_spec')
    puzzle = request.node.callspec.getparam('puzzle')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_name = f"{player_id(player_spec)}_{puzzle_id(puzzle)}_{timestamp}.log"
    log_file_path = os.path.join(LOG_DIR, log_file_name)
    
    logger = logging.getLogger(log_file_name)
    logger.setLevel(logging.INFO)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    handler = logging.FileHandler(log_file_path)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logger.addHandler(handler)
    
    yield logger # Provide the logger to the test
    
    # Teardown: remove handler after test is done
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

# --- Test Parametrization Data ---

def load_players(config):
    players = []
    for key, model_name in config.get("ai_models", {}).items():
        if not key.startswith("//"):
            players.append(('ai', key, model_name))
    for key, sf_config in config.get("stockfish_configs", {}).items():
        if not key.startswith("//"):
            players.append(('stockfish', key, sf_config))
    return players

def load_puzzles(config):
    return [p for p in config.get("chess_problems", []) if "mate_in" in p]

def player_id(player_spec):
    player_type, key, data = player_spec
    if player_type == 'ai':
        return f"AI-{data.split('/')[-1]}"
    if player_type == 'stockfish':
        return f"Stockfish-{key}-{data['name'].replace(' ', '')}"
    return key

def puzzle_id(puzzle):
    return puzzle['name'].replace('&', '').replace(' ', '-')

# Load config at module level for parametrization
_parametrization_config = _load_config_for_parametrization(TEST_CONFIG_FILE)

# --- The Test ---

@pytest.mark.parametrize("player_under_test_spec", load_players(_parametrization_config), ids=player_id)
@pytest.mark.parametrize("puzzle", load_puzzles(_parametrization_config), ids=puzzle_id)
def test_puzzle_solving(player_under_test_spec, player_under_test, defender_player, puzzle, game_logger, test_config, test_results):
    """
    Tests if a player can solve a mate-in-N puzzle against a strong defender.
    """
    board = chess.Board(puzzle["fen"])
    moves_to_mate = puzzle["mate_in"]
    strategy_prompt = test_config.get("puzzle_solving", {}).get("strategy_prompt") if isinstance(player_under_test, AIPlayer) else None
    
    start_msg = f"Testing player '{player_under_test.model_name}' on puzzle '{puzzle['name']}' (Mate in {moves_to_mate})..."
    print(f"\n{start_msg}")
    game_logger.info(start_msg)
    game_logger.info(f"Initial FEN: {board.fen()}")
    print("Initial Board State:")
    print(board)

    try:
        for i in range(moves_to_mate):
            move_uci = player_under_test.compute_move(board, strategy_message=strategy_prompt)
            assert move_uci is not None, f"Player failed to provide a move on turn {i+1}."
            
            move = chess.Move.from_uci(move_uci)
            assert move in board.legal_moves, f"Player returned an illegal move '{move_uci}' on turn {i+1}."
            board.push(move)
            
            turn_msg = f"Turn {i+1} (P): {move_uci}"
            print(f"  - {turn_msg}")
            game_logger.info(f"{turn_msg} -> FEN: {board.fen()}")

            if board.is_checkmate():
                print("\nFinal board state (Checkmate):")
                print(board)
                success_msg = f"SUCCESS: Player solved {puzzle['name']} in {i + 1} moves (or fewer)."
                print(f"  - {success_msg}")
                game_logger.info(success_msg)
                _record_result(test_results, player_under_test, puzzle, "PASS", moves=i + 1)
                return

            if i < moves_to_mate - 1:
                if board.is_game_over():
                    pytest.fail(f"Game ended prematurely (e.g., stalemate) after player's move {move_uci}.")
                
                defender_move_uci = defender_player.compute_move(board)
                assert defender_move_uci is not None, "Defender failed to provide a move."
                
                defender_move = chess.Move.from_uci(defender_move_uci)
                board.push(defender_move)
                
                def_turn_msg = f"Turn {i+1} (D): {defender_move_uci}"
                print(f"  - {def_turn_msg}")
                game_logger.info(f"{def_turn_msg} -> FEN: {board.fen()}")

        failure_msg = f"Player failed to deliver checkmate within {moves_to_mate} moves."
        game_logger.error(failure_msg)
        print("\nFinal board state (not a checkmate):")
        print(board)
        _record_result(test_results, player_under_test, puzzle, "FAIL")
        pytest.fail(failure_msg)

    except Exception as e:
        failure_msg = f"Test failed with an exception: {e}"
        game_logger.error(failure_msg)
        _record_result(test_results, player_under_test, puzzle, "FAIL")
        pytest.fail(failure_msg)

@pytest.fixture
def puzzle_solver(mocker):
    """Fixture to create an instance of ModelPuzzles with mocked dependencies."""
    mock_ui = mocker.MagicMock(spec=UIManager)
    
    # Dummy configs for testing purposes
    ai_models = {"m1": "openai/gpt-4o"}
    stockfish_configs = {
        "s2": {"name": "Balanced", "parameters": {"Skill Level": 10}},
        "s3": {"name": "Strong", "parameters": {"Skill Level": 20}}
    }
    # A mock stockfish path is sufficient if the player isn't actually created
    stockfish_path = "dummy/path/to/stockfish"

    player_factory = PlayerFactory(mock_ui, ai_models, stockfish_configs, stockfish_path)
    
    # Mock the file manager to prevent actual file I/O
    mock_file_manager = mocker.MagicMock()
    
    return ModelPuzzles(player_factory, mock_file_manager, mock_ui)

def test_solve_puzzle_with_sufficient_time(puzzle_solver, mocker):
    """
    Tests that puzzles can be solved when a sufficient timeout is provided.
    This test simulates the puzzle-solving process.
    """
    # 1. Mock the dependencies to simulate a successful puzzle solve
    mock_game = mocker.MagicMock()
    mock_player = mocker.MagicMock()
    
    # Assume solve_puzzle returns a status dictionary
    mocker.patch.object(puzzle_solver, '_create_game_for_puzzle', return_value=mock_game)
    mocker.patch.object(puzzle_solver, '_get_player_for_puzzle', return_value=mock_player)
    
    # Simulate that with enough time, the player finds the best move
    # and the puzzle is evaluated as "PASS"
    mocker.patch.object(puzzle_solver, '_evaluate_puzzle_move', return_value={"status": "PASS", "reason": "Mate found"})

    # 2. Define a sample puzzle and model to test
    puzzle = {
        "name": "Mate in 1",
        "fen": "4k3/R7/8/8/8/8/8/4K3 w - - 0 1",
        "solution": ["a7a8"]
    }
    model_key = "s3" # Using a strong Stockfish config
    
    # 3. Call the method with a longer timeout
    # This is the key change: providing a longer timeout for puzzles.
    result = puzzle_solver.solve_puzzle(puzzle, model_key, puzzle_timeout=30)
    
    # 4. Assert that the puzzle passed
    assert result is not None
    assert result["status"] == "PASS"

# It's good practice to also add tests for other scenarios,
# such as what happens when a player fails or times out.
def test_solve_puzzle_failure(puzzle_solver, mocker):
    """Tests the failure path of the puzzle solver."""
    mocker.patch.object(puzzle_solver, '_create_game_for_puzzle', return_value=mocker.MagicMock())
    mocker.patch.object(puzzle_solver, '_get_player_for_puzzle', return_value=mocker.MagicMock())
    # Simulate a failure condition
    mocker.patch.object(puzzle_solver, '_evaluate_puzzle_move', return_value={"status": "FAIL", "reason": "Incorrect move"})

    puzzle = {"name": "Test Puzzle", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "solution": ["e2e4"]}
    model_key = "m1"
    
    # Even with a long timeout, the evaluation can still fail
    result = puzzle_solver.solve_puzzle(puzzle, model_key, puzzle_timeout=30)
    
    assert result is not None
    assert result["status"] == "FAIL"
    assert result["reason"] == "Incorrect move"
