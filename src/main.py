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

from game import Game, RED, ENDC
from ai_player import AIPlayer
from stockfish_player import StockfishPlayer
from human_player import HumanPlayer
from ui_manager import UIManager
from file_manager import FileManager
from expert_service import ExpertService
from player_factory import PlayerFactory
from data_models import PlayerStats, GameHeader, stats_to_dict, GameLoopAction


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
        self._load_config()
        # Initialize services and factories after config is loaded
        self.expert_service = ExpertService(self.ui, self.chess_expert_model)
        self.player_factory = PlayerFactory(
            self.ui, self.ai_models, self.stockfish_configs, self.stockfish_path
        )

    def _load_config(self):
        """Loads configuration from config.json."""
        try:
            with open('src/config.json', 'r') as f:
                config = json.load(f)
                self.white_openings = config.get("white_openings", {})
                self.black_defenses = config.get("black_defenses", {})
                self.ai_models = config.get("ai_models", {})
                self.stockfish_path = config.get("stockfish_path")
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

    def parse_log_header(self, lines, all_player_keys) -> tuple[Optional[GameHeader], Optional[str]]:
        """Parses the header of a log file and returns a GameHeader object."""
        header_data = {}
        for line in lines[:10]:  # Check first 10 lines
            match = re.match(r"\[(\w+)\s+\"(.+?)\"\]", line)
            if match:
                key, value = match.groups()
                header_data[key.lower()] = value

        required_keys = ['white', 'black', 'white_key', 'black_key']
        if not all(k in header_data for k in required_keys):
            return None, "Header is missing required tags (White, Black, White_Key, Black_Key)."

        if header_data['white_key'] not in all_player_keys or header_data['black_key'] not in all_player_keys:
            return None, "Player key in log is not in current config."

        return GameHeader(
            white_name=header_data['white'],
            black_name=header_data['black'],
            white_key=header_data['white_key'],
            black_key=header_data['black_key'],
            white_strategy=header_data.get('whitestrategy'),
            black_strategy=header_data.get('blackstrategy'),
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
            
            game = Game(player1, player2, white_strategy=header.white_strategy, black_strategy=header.black_strategy, white_player_key=header.white_key, black_player_key=header.black_key)
            
            # Find last FEN
            last_fen = header.initial_fen
            for line in lines:
                if "FEN:" in line:
                    last_fen = line.split("FEN:")[1].strip()
            
            game.set_board_from_fen(last_fen)
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

                    elif choice == '5': # Fun Fact
                        self.expert_service.get_fun_fact()

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
#--- Entry Point ---
if __name__ == "__main__":
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        filemode='w'
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    app = ChessApp()
    app.run()