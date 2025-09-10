import os
import sys
import json
import glob
import shutil
import logging
import re
from datetime import datetime, timezone
from dataclasses import asdict
from typing import Optional

import chess

from src.game import Game, RED, ENDC
from src.ai_player import AIPlayer
from src.stockfish_player import StockfishPlayer
from src.human_player import HumanPlayer
from src.ui_manager import UIManager
from src.file_manager import FileManager
from src.expert_service import ExpertService
from src.player_factory import PlayerFactory
from src.data_models import PlayerStats, GameHeader, stats_to_dict, GameLoopAction
from src.user_manager import UserManager
from src.auth_ui import AuthUI


# --- Constants ---
LOG_FILE = 'chess_game.log'
PLAYER_STATS_FILE = 'logs/player_stats.json'

class ChessApp:
    """The main application class that orchestrates the game."""
    
    def __init__(self):
        """Initializes the application, loading configurations."""
        self.ui = UIManager()
        self.file_manager = FileManager(self.ui)
        self.white_openings = {}
        self.black_defenses = {}
        self.ai_models = {}
        self.stockfish_path = None
        self.stockfish_configs = {}
        self.chess_expert_model = ""
        
        # Add user management components
        self.user_manager = UserManager(data_dir="user_data", dev_mode=True)  # Set dev_mode=True
        self.auth_ui = AuthUI()
        self.session_token = None
        self.current_user = None
        
        self._load_config()
        # Initialize services and factories after config is loaded
        self.expert_service = ExpertService(self.ui, self.chess_expert_model)
        self.player_factory = PlayerFactory(
            self.ui, self.ai_models, self.stockfish_configs, self.stockfish_path
        )

        # Try to load session from file if it exists
        self._load_session()

    def _load_config(self):
        """Loads configuration from config.json."""
        try:
            with open('src/config.json', 'r') as f:
                config = json.load(f)
                self.white_openings = config.get("white_openings", {})
                self.black_defenses = config.get("black_defenses", {})
                self.ai_models = config.get("ai_models", {})
                # Use environment variable if set, else config value, else default "stockfish"
                self.stockfish_path = os.environ.get("STOCKFISH_EXECUTABLE", config.get("stockfish_path", "stockfish"))
                self.stockfish_configs = config.get("stockfish_configs", {})
                self.chess_expert_model = config.get('chess_expert_model', 'google/gemini-2.5-pro')
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.ui.display_message(f"{RED}Fatal Error: Could not load or parse 'src/config.json'.{ENDC}")
            self.ui.display_message(f"Reason: {e}")
            self.ui.display_message("Please ensure the file exists and is a valid JSON.")
            sys.exit(1)

    def _initialize_new_game_log(self):
        """Shuts down existing log handlers and re-initializes the log file in write mode."""
        # Shut down any existing handlers to release the file lock
        logging.shutdown()
        # Re-initialize logging in write mode to clear the file
        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            filemode='w'
        )
        logging.getLogger("httpx").setLevel(logging.WARNING)

    def _load_player_stats(self):
        """Loads player statistics from a JSON file into PlayerStats objects."""
        try:
            with open(PLAYER_STATS_FILE, 'r') as f:
                stats_data = json.load(f)
                # Convert dicts to PlayerStats objects
                self.player_stats = {name: PlayerStats(**data) for name, data in stats_data.items()}
        except (FileNotFoundError, json.JSONDecodeError):
            self.player_stats = {}

    def _save_player_stats(self):
        """Saves player statistics to a JSON file."""
        with open(PLAYER_STATS_FILE, 'w') as f:
            # Convert PlayerStats objects to dicts for JSON serialization
            json.dump(stats_to_dict(self.player_stats), f, indent=4)

    def _update_player_stats(self, game):
        """Updates player stats based on the game result."""
        result = game.board.result()
        white_name = game.players[chess.WHITE].model_name
        black_name = game.players[chess.BLACK].model_name

        # Ensure players are in stats, creating new PlayerStats objects if not
        self.player_stats.setdefault(white_name, PlayerStats())
        self.player_stats.setdefault(black_name, PlayerStats())

        if result == "1-0":  # White wins
            self.player_stats[white_name].wins += 1
            self.player_stats[black_name].losses += 1
        elif result == "0-1":  # Black wins
            self.player_stats[black_name].wins += 1
            self.player_stats[white_name].losses += 1
        else:  # Draw
            self.player_stats[white_name].draws += 1
            self.player_stats[black_name].draws += 1
        self._save_player_stats()

    def parse_log_header(self, lines, all_player_keys, debug=False) -> tuple[Optional[GameHeader], Optional[str]]:
        """
        Parses the header of a log file and returns a GameHeader object.
        
        Args:
            lines: Lines from the log file
            all_player_keys: List of valid player keys
            debug: If True, prints detailed diagnostic information
        """
        if debug:
            print("\n==== DIAGNOSTICS: PARSING LOG HEADER ====", flush=True)
            print(f"Processing {len(lines)} lines, looking at first 10", flush=True)
            print(f"Available player keys: {all_player_keys}", flush=True)
        
        header_data = {}
        
        # Display the first few lines for inspection
        if debug:
            print("\n--- FIRST 10 LINES OF FILE ---", flush=True)
            for i, line in enumerate(lines[:10]):
                print(f"LINE {i+1}: {line.strip()}", flush=True)
        
        # Process with existing regex pattern
        if debug:
            print("\n--- REGEX MATCHING RESULTS ---", flush=True)
        
        for i, line in enumerate(lines[:10]):
            if debug:
                print(f"Processing line {i+1}: {line.strip()}", flush=True)
            
            match = re.match(r"\[(\w+)\s+\"(.+?)\"\]", line)
            if match:
                key, value = match.groups()
                header_data[key.lower()] = value
                if debug:
                    print(f"  ✓ MATCHED: key='{key.lower()}', value='{value}'", flush=True)
            else:
                # Try alternative pattern based on actual log format
                alt_match = re.search(r'.*- ([^:]+):\s*(.+)', line)
                if alt_match:
                    key, value = alt_match.groups()
                    clean_key = key.lower().replace(' ', '_')
                    header_data[clean_key] = value
                    if debug:
                        print(f"  ✓ ALT MATCHED: key='{clean_key}', value='{value}'", flush=True)
        
        if debug:
            print("\n--- PARSED HEADER DATA ---", flush=True)
            for k, v in header_data.items():
                print(f"  {k}: {v}", flush=True)
        
        # Check required keys - FIXED: Use the actual keys found in the log
        required_keys = ['white', 'black', 'white_player_key', 'black_player_key']
        
        if debug:
            print("\n--- REQUIRED KEYS CHECK ---", flush=True)
            for k in required_keys:
                if k in header_data:
                    print(f"  ✓ Found required key: {k} = {header_data[k]}", flush=True)
                else:
                    print(f"  ✗ Missing required key: {k}", flush=True)
                    # Try to find similar keys that might match
                    possible_matches = [hk for hk in header_data.keys() if k in hk]
                    if possible_matches:
                        print(f"    Possible matches: {possible_matches}", flush=True)
        
        if not all(k in header_data for k in required_keys):
            missing = [k for k in required_keys if k not in header_data]
            error_msg = f"Header is missing required tags ({', '.join(missing)})."
            if debug:
                print(f"\n❌ ERROR: {error_msg}", flush=True)
            return None, error_msg

        # Check if keys are in config
        if debug:
            print("\n--- PLAYER KEY VALIDATION ---", flush=True)
            for k, player_key_field in [('white_player_key', 'white_key'), ('black_player_key', 'black_key')]:
                if header_data[k] in all_player_keys:
                    print(f"  ✓ Valid player key: {k} = {header_data[k]}", flush=True)
                else:
                    print(f"  ✗ Invalid player key: {k} = {header_data[k]}", flush=True)
                    print(f"    Available keys: {all_player_keys}", flush=True)
        
        if header_data['white_player_key'] not in all_player_keys or header_data['black_player_key'] not in all_player_keys:
            error_msg = "Player key in log is not in current config."
            if debug:
                print(f"\n❌ ERROR: {error_msg}", flush=True)
            return None, error_msg

        if debug:
            print("\n✅ HEADER PARSING SUCCESSFUL", flush=True)
        
        # Create GameHeader object - FIXED: Use the correct key names
        return GameHeader(
            white_name=header_data['white'],
            black_name=header_data['black'],
            white_key=header_data['white_player_key'],  # Changed from 'white_key'
            black_key=header_data['black_player_key'],  # Changed from 'black_key'
            white_strategy=header_data.get('white_strategy'),
            black_strategy=header_data.get('black_strategy'),
            result=header_data.get('result'),
            termination=header_data.get('termination'),
            date=header_data.get('date')
        ), None

    def load_game_from_log(self, log_file):
        """Loads a game state from a log file."""
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            all_keys = list(self.ai_models.keys()) + list(self.stockfish_configs.keys()) + ['hu']
            header, error_reason = self.parse_log_header(lines, all_keys)
            if not header:
                self.ui.display_message(f"Failed to load game: {error_reason}")
                return None

            player1 = self.player_factory.create_player(header.white_key, name_override=header.white_name)
            player2 = self.player_factory.create_player(header.black_key, name_override=header.black_name)
            
            game = Game(player1, player2, white_strategy=header.white_strategy, 
                   black_strategy=header.black_strategy, 
                   white_player_key=header.white_key, 
                   black_player_key=header.black_key)
            
            # Extract FEN information directly from log file instead of using header
            initial_fen = None
            for line in lines:
                if "Initial FEN:" in line:
                    initial_fen = line.split("Initial FEN:")[1].strip()
                    break
            
            # Find last FEN (start with initial, then update with any move FENs)
            last_fen = initial_fen
            for line in lines:
                if "FEN:" in line and "Initial FEN:" not in line:
                    fen_part = line.split("FEN:")[1].strip()
                    # Handle potential trailing commas or other text
                    if ' ' in fen_part:
                        # Only take the FEN part up to any comment or trailing text
                        last_fen = fen_part.split(',')[0].strip()
                    else:
                        last_fen = fen_part
            
            if last_fen:
                game.set_board_from_fen(last_fen)
                print(f"Set board position from FEN", flush=True)
            else:
                print("Warning: No FEN found in log file", flush=True)
            
            return game
        except Exception as e:
            self.ui.display_message(f"Error loading log file: {e}")
            return None

    # --- In-Game Menu Handlers ---

    def handle_load_game_in_menu(self, game):
        """Handles the 'load game' option from the in-game menu."""
        game_summaries = self.file_manager.get_saved_game_summaries()
        if not game_summaries:
            self.ui.display_message("No saved games found.")
            return game, GameLoopAction.CONTINUE

        chosen_summary = self.ui.display_saved_games_and_get_choice(game_summaries)
        
        if chosen_summary == 'm':
            return game, GameLoopAction.RETURN_TO_MENU
        elif chosen_summary == 'q':
            self.ui.display_message("Exiting application.")
            sys.exit()
        elif chosen_summary:
            chosen_file = chosen_summary['filename']
            loaded_game = self.load_game_from_log(chosen_file)
            if loaded_game:
                logging.shutdown()
                shutil.copy(chosen_file, 'chess_game.log')
                logging.basicConfig(filename='chess_game.log', level=logging.INFO, format='%(asctime)s - %(message)s', filemode='a')
                logging.getLogger("httpx").setLevel(logging.WARNING)
                self.ui.display_message(f"Successfully loaded game from {chosen_file}.")
                return loaded_game, GameLoopAction.SKIP_TURN
        return game, GameLoopAction.CONTINUE

    def handle_practice_load_in_menu(self, game):
        """Handles the 'load practice position' option from the in-game menu."""
        with open('src/puzzles.json', 'r') as f:
            positions = json.load(f)
        
        position = self.ui.display_practice_positions_and_get_choice(positions)

        if position and position not in ['?', 'm', 'q']:
            white_player_key, black_player_key = self.ui.display_model_menu_and_get_choice(self.ai_models, self.stockfish_configs)
            
            player1 = self.player_factory.create_player(white_player_key, color_label="White")
            player2 = self.player_factory.create_player(black_player_key, color_label="Black")

            new_game = Game(player1, player2, white_player_key=white_player_key, black_player_key=black_player_key)
            new_game.set_board_from_fen(position['fen'])
            new_game.initialize_game()
            
            self.ui.display_message(f"Loaded practice position: {position['name']}")
            return new_game, GameLoopAction.SKIP_TURN
        elif position and position.startswith('?'):
            question = position[1:].strip()
            self.expert_service.ask_expert(question)
        elif position == 'm':
            return game, GameLoopAction.RETURN_TO_MENU
        elif position == 'q':
            self.ui.display_message("Exiting application.")
            sys.exit()
            
        return game, GameLoopAction.CONTINUE

    def _update_player_stats(self, white_player, black_player, result):
        """Updates, saves, and displays the win/loss/draw stats for players in the last game."""
        stats = self.file_manager.load_player_stats() or {}
        
        white_name = white_player.model_name
        black_name = black_player.model_name

        # Ensure players exist in the stats dictionary
        for player_name in {white_name, black_name}:
            if player_name not in stats:
                stats[player_name] = {"wins": 0, "losses": 0, "draws": 0}

        # Update stats based on the result
        if result == "1-0":  # White wins
            stats[white_name]["wins"] += 1
            stats[black_name]["losses"] += 1
        elif result == "0-1":  # Black wins
            stats[black_name]["wins"] += 1
            stats[white_name]["losses"] += 1
        elif result == "1/2-1/2":  # Draw
            stats[white_name]["draws"] += 1
            stats[black_name]["draws"] += 1
        
        # Save the updated stats back to the file
        self.file_manager.save_player_stats(stats)

        # Reload from disk to ensure we're displaying the persisted values
        stats = self.file_manager.load_player_stats() or {}

        # Display the newly updated stats for the players in the game
        self.ui.display_message("\n--- Updated Player Stats ---")
        
        white_stats = stats.get(white_name, {"wins": 0, "losses": 0, "draws": 0})
        white_stats_str = f"Wins: {white_stats['wins']}, Losses: {white_stats['losses']}, Draws: {white_stats['draws']}"
        self.ui.display_message(f"{white_name}: {white_stats_str}")

        if white_name != black_name:
            black_stats = stats.get(black_name, {"wins": 0, "losses": 0, "draws": 0})
            black_stats_str = f"Wins: {black_stats['wins']}, Losses: {black_stats['losses']}, Draws: {black_stats['draws']}"
            self.ui.display_message(f"{black_name}: {black_stats_str}")
        
        self.ui.display_message("----------------------------")

    def _view_player_stats(self):
        """Loads and displays player statistics."""
        stats = self.file_manager.load_player_stats()
        self.ui.display_player_stats(stats)
        self.ui.get_user_input("Press Enter to return to the main menu.")

    def _handle_quit_request(self, game):
        """
        Handles a quit request. For a human, asks to resign/save/cancel.
        For an AI, triggers resignation. Exits the app on resign/save.
        Returns True if the game loop should continue (i.e., user cancelled).
        """
        current_player = game.get_current_player()
        if isinstance(current_player, HumanPlayer):
            quit_choice = self.ui.get_human_quit_choice()
            if quit_choice == 'r':
                self._handle_resignation(game)  # This exits
            elif quit_choice == 's':
                self.file_manager.save_game_log()
                self.ui.display_message("Game saved. Exiting application.")
                sys.exit()
            elif quit_choice == 'q':
                self.ui.display_message("Exiting without saving.")
                sys.exit()
            else:  # 'c' to cancel
                return True  # Signal to continue
        else:
            self._handle_resignation(game)  # This exits
        
        return False # Should not be reached if resignation happens

    def _handle_resignation(self, game):
        """Handles the logic for a player resigning."""
        resigning_color = "White" if game.board.turn == chess.WHITE else "Black"
        resigning_player = game.get_current_player().model_name
        self.ui.display_message(f"\n{resigning_player} ({resigning_color}) has resigned.")
        
        # Update stats
        result = "0-1" if resigning_color == "White" else "1-0"
        self._update_player_stats(game.players[chess.WHITE], game.players[chess.BLACK], result)

        # Ask to save and then exit
        save_choice = self.ui.get_user_input("Save final game log? (y/N): ").lower()
        if save_choice == 'y':
            self.file_manager.save_game_log()
        self.ui.display_message("Exiting application.")
        sys.exit()

    def handle_in_game_menu(self, game):
        """Handles the in-game menu options, returning a new game object and an action."""
        menu_choice = self.ui.display_in_game_menu()

        if menu_choice == 'l': # Load Game
            return self.handle_load_game_in_menu(game)
        elif menu_choice == 'p': # Load Practice
            return self.handle_practice_load_in_menu(game)
        elif menu_choice == 's': # Save
            self.file_manager.save_game_log()
            return game, GameLoopAction.CONTINUE
        elif menu_choice.startswith('?'): # Ask Expert
            question = menu_choice[1:].strip()
            self.expert_service.ask_expert(question)
            return game, GameLoopAction.CONTINUE
        elif menu_choice == 'r': # Return to Game
            return game, GameLoopAction.CONTINUE
        elif menu_choice == 'q': # Quit
            return game, GameLoopAction.QUIT_APPLICATION
        
        return game, GameLoopAction.CONTINUE

    def play_turn(self, game):
        """Plays a single turn of the game, returning the game object and an action."""
        self.ui.display_board(game.board)
        current_player = game.get_current_player()

        try:
            if isinstance(current_player, HumanPlayer):
                turn_color = "White" if game.board.turn else "Black"
                move_number = game.board.fullmove_number
                prompt = f"Move {move_number} ({current_player.model_name} as {turn_color}): Enter your move (e.g. e2e4), 'q' to quit, or 'm' for menu: "
                user_input = self.ui.prompt_for_move(game)

                if user_input.lower() == 'q':
                    return game, GameLoopAction.QUIT_APPLICATION
                elif user_input.lower() == 'm':
                    return self.handle_in_game_menu(game)
                else:
                    game.make_manual_move(user_input)
            else:
                self.ui.display_turn_message(game)
                game.play_turn()
        except ValueError as e:
            self.ui.display_message(f"{RED}Invalid move: {e}{ENDC}")

        return game, GameLoopAction.CONTINUE

    def _determine_game_result(self, game):
        """Return canonical result string ('1-0', '0-1', '1/2-1/2') based on board state."""
        board = game.board
        # Checkmate: the side to move has been checkmated, so the winner is the opposite color
        if board.is_checkmate():
            winner = not board.turn
            return "1-0" if winner == chess.WHITE else "0-1"
        # Draw conditions
        if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_threefold_repetition() or board.can_claim_fifty_moves():
            return "1/2-1/2"
        # Fallback to board.result() which returns '1-0', '0-1' or '1/2-1/2'
        try:
            return board.result()
        except Exception:
            return "1/2-1/2"

    # --- Main Application Runner ---

    def run(self):
        """Main function to run the chess application."""
        # First, handle authentication
        if not self._handle_authentication():
            print("Exiting application.")
            return
        
        game = None
        while True:
            if game:
                if game.board.is_game_over():
                    self.ui.display_game_over_message(game)
                    # determine result from board state to avoid incorrect mappings
                    result = self._determine_game_result(game)
                    self._update_player_stats(game.players[chess.WHITE], game.players[chess.BLACK], result)
                    save_choice = self.ui.get_user_input("\nSave final game log? (y/N): ").lower()
                    if save_choice == 'y':
                        self.file_manager.save_game_log()
                    self.ui.get_user_input("Press Enter to return to the main menu.")
                    game = None # Game is over, return to main
                    continue

                new_game, action = self.play_turn(game)
                game = new_game # Always update the game object

                if action == GameLoopAction.QUIT_APPLICATION:
                    if self._handle_quit_request(game):
                        continue # User cancelled quit
                    else:
                        game = None # Quit was handled, return to menu
                        continue
                elif action == GameLoopAction.RETURN_TO_MENU:
                    game = None
                    continue
                elif action in [GameLoopAction.CONTINUE, GameLoopAction.SKIP_TURN]:
                    continue
            else:
                # --- Main Menu ---
                choice = self.ui.display_main_menu()
                try:
                    if choice == '1':  # New Game
                        self._initialize_new_game_log()
                        game = self.setup_new_game()
                        if not game:
                            self.ui.display_message("New game cancelled.")
                            continue
                        self.ui.display_game_start_message(game)

                    elif choice == '2':  # Load Saved Game
                        game_summaries = self.file_manager.get_saved_game_summaries()
                        if not game_summaries:
                            self.ui.display_message("No saved games found.")
                            continue
                        chosen_summary = self.ui.display_saved_games_and_get_choice(game_summaries)
                        if chosen_summary and chosen_summary not in ['m', 'q']:
                            game = self.load_game_from_log(chosen_summary['filename'])

                    elif choice == '3':  # Load Practice Position
                        with open('src/puzzles.json', 'r') as f:
                            positions = json.load(f)
                        position = self.ui.display_practice_positions_and_get_choice(positions)
                        if not position or position in ['m', 'q']:
                            continue
                        self._initialize_new_game_log()
                        white_key, black_key = self.ui.display_model_menu_and_get_choice(self.ai_models, self.stockfish_configs)
                        if white_key is None or black_key is None:
                            self.ui.display_message("Model selection cancelled. Returning to main menu.")
                            continue
                        player1 = self.player_factory.create_player(white_key, color_label="White")
                        player2 = self.player_factory.create_player(black_key, color_label="Black")
                        if player1 is None or player2 is None:
                            self.ui.display_message("Player creation cancelled. Returning to main menu.")
                            continue
                        game = Game(player1, player2, white_player_key=white_key, black_player_key=black_key)
                        game.set_board_from_fen(position['fen'])
                        game.initialize_game()
                        self.ui.display_game_start_message(game)

                    elif choice == '4': # View Player Stats
                        self._view_player_stats()

                    elif choice.startswith('?'):
                        question = choice[1:].strip()
                        self.expert_service.ask_expert(question)

                    elif choice == 'q':
                        self.ui.display_message("Exiting application.")
                        sys.exit()

                except Exception as e:
                    self.ui.display_message(f"\n{RED}An unexpected error occurred: {e}{ENDC}")
                    logging.error(f"An unexpected error occurred: {e}", exc_info=True)
                    self.ui.get_user_input("Press Enter to acknowledge and return to the main menu.")
    
    def setup_new_game(self):
        """Create and return a new Game from UI choices. Returns None if the user cancels."""
        # Ask UI for setup choices (handles model selection and optional opening/defense)
        choices = self.ui.display_setup_menu_and_get_choices(
            getattr(self, "white_openings", {}),
            getattr(self, "black_defenses", {}),
            getattr(self, "ai_models", {}),
            getattr(self, "stockfish_configs", {})
        )
        if not choices:
            return None

        white_opening, black_defense, white_key, black_key = choices

        white_player = self.player_factory.create_player(white_key, color_label="White")
        black_player = self.player_factory.create_player(black_key, color_label="Black")

        game = Game(white_player, black_player, white_player_key=white_key, black_player_key=black_key)
        # apply optional opening/defense if the game API supports it
        try:
            if white_opening:
                game.set_opening(white_opening)
            if black_defense:
                game.set_defense(black_defense)
        except Exception:
            # ignore if not supported by current Game implementation
            pass

        game.initialize_game()
        return game

    def _display_main_menu(self):
        """Displays the main menu options."""
        print("\n--- Main Menu ---", flush=True)
        print("  1: Play a New Game", flush=True)
        print("  2: Load a Saved Game", flush=True)
        print("  3: Load a Practice Position", flush=True)
        print("  4: View Player Stats", flush=True)
        # Option 5 (Fun Chess Fact) is removed
        print("  ?: Ask a Chess Expert", flush=True)
        print("  q: Quit", flush=True)
        print("Enter your choice: ", end="", flush=True)

    def _display_chess_expert_menu(self):
        """Displays the chess expert menu options."""
        print("\n--- Ask the Chessmaster ---", flush=True)
        print("  1: Analyze a position", flush=True)
        print("  2: Ask for opening advice", flush=True)
        print("  3: Get a tactical puzzle", flush=True)
        print("  4: Tell me a fun chess fact", flush=True)  # New option
        print("  b: Back to main menu", flush=True)
        print("Enter your choice: ", end="", flush=True)

    def _handle_chess_expert_menu(self):
        """Handles the chess expert menu options."""
        self._display_chess_expert_menu()
        choice = input().strip().lower()
        
        if choice == '1':
            # Handle position analysis
            pass
        elif choice == '2':
            # Handle opening advice
            pass
        elif choice == '3':
            # Handle tactical puzzle
            pass
        elif choice == '4':
            # Fun fact option - reuse existing fun fact functionality
            self._show_fun_chess_fact()
        elif choice == 'b':
            return
        else:
            print(f"{RED}Invalid choice. Please try again.{ENDC}", flush=True)

    def _load_session(self):
        """Attempt to load a saved session if it exists."""
        session_file = os.path.join("user_data", "current_session.txt")
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r') as f:
                    saved_token = f.read().strip()
                    
                # Validate the token
                user_data = self.user_manager.get_current_user(saved_token)
                if user_data:
                    self.session_token = saved_token
                    self.current_user = user_data
                    print(f"Welcome back, {user_data['username']}!")
            except Exception as e:
                print(f"Error loading saved session: {e}")

    def _handle_authentication(self):
        """Handle user authentication flow. Return True if authenticated."""
        # If already authenticated, return True immediately
        if self.current_user:
            return True
            
        while not self.current_user:
            choice = self.auth_ui.display_auth_menu()
            
            if choice == '1':  # Login
                username_or_email, password = self.auth_ui.get_login_credentials()
                success, message, token = self.user_manager.login(username_or_email, password)
                
                self.auth_ui.display_message(message)
                if success:
                    self.session_token = token
                    self.current_user = self.user_manager.get_current_user(token)
                    self._save_session()
                    return True
    
            elif choice == '2':  # Register
                registration_info = self.auth_ui.get_registration_info()
                if registration_info:
                    username, email, password = registration_info
                    success, message = self.user_manager.register_user(username, email, password)
                    
                    self.auth_ui.display_message(message)
                    if success:
                        if self.user_manager.dev_mode:
                            # In dev mode, show a special message about verification
                            print("In development mode, verification tokens are displayed in the console.")
                            print("You can use the token shown above to verify your account.")
                        
                        # Ask for verification token
                        verify_now = input("Would you like to enter your verification code now? (y/n): ").lower() == 'y'
                        if verify_now:
                            token = self.auth_ui.get_verification_token()
                            success, msg = self.user_manager.verify_email(token)
                            self.auth_ui.display_message(msg)
                            
                            # If verification was successful, try to auto-login
                            if success:
                                print("Attempting automatic login after verification...")
                                success, message, token = self.user_manager.login(username, password)
                                if success:
                                    self.session_token = token
                                    self.current_user = self.user_manager.get_current_user(token)
                                    self._save_session()
                                    return True
    
            elif choice == 'q':  # Quit
                return False

        return True  # Already authenticated

    def _save_session(self):
        """Save the current session token to a file."""
        if self.session_token:
            os.makedirs("user_data", exist_ok=True)
            session_file = os.path.join("user_data", "current_session.txt")
            
            with open(session_file, 'w') as f:
                f.write(self.session_token)

    def get_password(prompt="Password: "):
        """Get password with or without masking based on environment"""
        # Check if we're in test mode
        if os.environ.get("CHESS_APP_TEST_MODE") == "1":
            # In test mode, accept password input directly without masking
            return input(prompt)
        else:
            # In normal mode, use getpass for secure password input
            import getpass
            return getpass.getpass(prompt)

#--- Entry Point ---
def main():
    if os.environ.get("CHESS_APP_TEST_MODE") == "1":
        # In test mode, skip authentication and go straight to main menu loop
        app = ChessApp()
        app.current_user = {"username": "TestUser"}  # Simulate a logged-in user
        app.run()
    else:
        app = ChessApp()
        app.run()

if __name__ == "__main__":
    main()