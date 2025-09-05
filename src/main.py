import os
import sys
import json
import glob
import shutil
import logging
import re
from datetime import datetime
import chess
from game import Game, RED, ENDC
from ai_player import AIPlayer
from stockfish_player import StockfishPlayer
from ui_manager import UIManager

# --- Constants ---
LOG_FILE = 'chess_game.log'
PLAYER_STATS_FILE = 'logs/player_stats.json'

class ChessApp:
    """The main application class that orchestrates the game."""
    def __init__(self):
        """Initializes the application, loading configurations."""
        self.ui = UIManager()
        self.white_openings = {}
        self.black_defenses = {}
        self.ai_models = {}
        self.stockfish_path = None
        self.stockfish_configs = {}
        self.chess_expert_model = ""
        self._load_config()

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
                self.chess_expert_model = config.get("chess_expert_model")
                if not self.chess_expert_model:
                    raise ValueError("chess_expert_model not found in config.")
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            self.ui.display_message(f"Error loading config.json: {e}")
            self.ui.display_message("Please ensure src/config.json exists and is correctly formatted.")
            sys.exit(1)

    def _create_player(self, player_key):
        """Creates a player object (AI or Stockfish) based on the key."""
        if player_key.startswith('m'):
            model_name = self.ai_models[player_key]
            return AIPlayer(model_name=model_name)
        elif player_key.startswith('s'):
            if not self.stockfish_path or not os.path.exists(self.stockfish_path):
                raise FileNotFoundError(f"Stockfish executable not found at path: {self.stockfish_path}. Please check your config.json.")
            config = self.stockfish_configs[player_key]
            return StockfishPlayer(path=self.stockfish_path, parameters=config['parameters'])
        else:
            raise ValueError(f"Unknown player key: {player_key}")

    def _ask_expert(self, question=None):
        """Handles the logic for asking the chess expert a question."""
        if not question:
            question = self.ui.get_chess_question()
        
        if not question:
            return

        self.ui.display_message("\nConsulting the expert...")
        expert_player = AIPlayer(model_name=self.chess_expert_model)
        system_prompt = "You are a chess expert playing at the grandmaster level."
        
        answer = expert_player.ask_question(question, system_prompt)
        
        self.ui.display_message("\n--- Grandmaster's Answer ---")
        self.ui.display_message(answer)
        self.ui.display_message("----------------------------")
        self.ui.get_user_input("Press Enter to return to the menu.")

    # --- Game Setup & Loading Methods ---

    def setup_new_game(self):
        """Handles the user interaction for setting up a new game."""
        white_opening_key, black_defense_key, white_player_key, black_player_key = \
            self.ui.display_setup_menu_and_get_choices(self.white_openings, self.black_defenses, self.ai_models, self.stockfish_configs)

        player1 = self._create_player(white_player_key)
        player2 = self._create_player(black_player_key)

        white_strategy = self.white_openings[white_opening_key] if white_opening_key != '0' else None
        black_strategy = self.black_defenses[black_defense_key] if black_defense_key != 'z' else None

        game = Game(player1, player2, white_strategy, black_strategy, white_player_key, black_player_key)
        game.initialize_game()
        return game

    def load_game_from_log(self, log_file):
        """Loads game settings and board state from a log file."""
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            header, error_reason = self.parse_log_header(lines)
            if not header:
                self.ui.display_message(f"Failed to load game: {error_reason}")
                return None

            player1 = self._create_player(header['white_key'])
            player2 = self._create_player(header['black_key'])
            
            game = Game(player1, player2, white_strategy=header['white_strategy'], black_strategy=header['black_strategy'])
            
            last_fen = header['initial_fen']
            for line in lines:
                if "FEN:" in line:
                    last_fen = line.split("FEN:")[1].strip()
            
            game.set_board_from_fen(last_fen)
            return game
        except Exception as e:
            self.ui.display_message(f"Error loading log file: {e}")
            return None

    @staticmethod
    def parse_log_header(lines):
        header = {
            'white_strategy': None,
            'black_strategy': None
        }
        patterns = {
            'white_key': r"White: .* \((m\d+|s\d+)\)",
            'black_key': r"Black: .* \((m\d+|s\d+)\)",
            'white_strategy': r"White Strategy: (.+)",
            'black_strategy': r"Black Strategy: (.+)",
            'initial_fen': r"Initial FEN: (.+)"
        }
        for line in lines[:6]: # Header should be in the first few lines
            for key, pattern in patterns.items():
                match = re.search(pattern, line)
                if match:
                    header[key] = match.group(1).strip()
        
        required_fields = ['white_key', 'black_key', 'initial_fen']
        missing_fields = [field for field in required_fields if not header.get(field)]
        
        if not missing_fields:
            return header, None
        else:
            reason = f"Could not find required fields in log header: {', '.join(missing_fields)}."
            return None, reason

    # --- In-Game Menu Handlers ---

    def handle_load_game_in_menu(self, game):
        """Handles the 'load game' option from the in-game menu."""
        saved_games = glob.glob('chess_game_*.log')
        if not saved_games:
            self.ui.display_message("No saved games found.")
            return game, 'continue'

        chosen_file = self.ui.display_saved_games_and_get_choice(saved_games)
        if chosen_file:
            loaded_game = self.load_game_from_log(chosen_file)
            if loaded_game:
                logging.shutdown()
                shutil.copy(chosen_file, 'chess_game.log')
                logging.basicConfig(filename='chess_game.log', level=logging.INFO, format='%(asctime)s - %(message)s', filemode='a')
                logging.getLogger("httpx").setLevel(logging.WARNING)
                self.ui.display_message(f"Successfully loaded game from {chosen_file}.")
                return loaded_game, 'skip_turn'
        return game, 'continue'

    def handle_practice_load_in_menu(self, game):
        """Handles the 'load practice position' option from the in-game menu."""
        with open('src/puzzles.json', 'r') as f:
            positions = json.load(f)
        
        position = self.ui.display_practice_positions_and_get_choice(positions)

        if position and position not in ['?', 'm', 'q']:
            white_player_key, black_player_key = self.ui.display_model_menu_and_get_choice(self.ai_models, self.stockfish_configs)
            
            player1 = self._create_player(white_player_key)
            player2 = self._create_player(black_player_key)

            new_game = Game(player1, player2, white_player_key=white_player_key, black_player_key=black_player_key)
            new_game.set_board_from_fen(position['fen'])
            new_game.initialize_game()
            
            self.ui.display_message(f"Loaded practice position: {position['name']}")
            return new_game, 'skip_turn'
        elif position and position.startswith('?'):
            question = position[1:].strip()
            self._ask_expert(question)
        elif position == 'm':
            return game, 'quit_to_menu'
        elif position == 'q':
            self.ui.display_message("Exiting application.")
            sys.exit()
            
        return game, 'continue'

    def _save_game_log(self):
        """Saves the current game log to a timestamped file."""
        try:
            # Ensure all buffered logs are written to disk before copying
            for handler in logging.getLogger().handlers:
                handler.flush()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f'chess_game_{timestamp}.log'
            shutil.copy('chess_game.log', save_path)
            self.ui.display_message(f"\nGame saved as {save_path}")
        except FileNotFoundError:
            self.ui.display_message("Log file not found, could not save.")
        except Exception as e:
            self.ui.display_message(f"An error occurred while saving: {e}")

    def _load_player_stats(self):
        """Loads player statistics from the JSON file."""
        if not os.path.exists(PLAYER_STATS_FILE):
            return {}
        try:
            with open(PLAYER_STATS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_player_stats(self, stats):
        """Saves player statistics to the JSON file."""
        os.makedirs(os.path.dirname(PLAYER_STATS_FILE), exist_ok=True)
        with open(PLAYER_STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)

    def _update_player_stats(self, white_player, black_player, result):
        """Updates and saves the win/loss/draw stats for players."""
        stats = self._load_player_stats()
        
        players = {white_player.model_name, black_player.model_name}
        for player_name in players:
            if player_name not in stats:
                stats[player_name] = {"wins": 0, "losses": 0, "draws": 0}

        if result == "1-0": # White wins
            stats[white_player.model_name]["wins"] += 1
            stats[black_player.model_name]["losses"] += 1
        elif result == "0-1": # Black wins
            stats[black_player.model_name]["wins"] += 1
            stats[white_player.model_name]["losses"] += 1
        elif result == "1/2-1/2": # Draw
            stats[white_player.model_name]["draws"] += 1
            stats[black_player.model_name]["draws"] += 1
        
        self._save_player_stats(stats)
        self.ui.display_message("\nPlayer stats have been updated.")

    def _view_player_stats(self):
        """Loads and displays player statistics."""
        stats = self._load_player_stats()
        self.ui.display_player_stats(stats)
        self.ui.get_user_input("Press Enter to return to the main menu.")

    def _handle_resignation(self, game):
        """Handles the logic for a player resigning."""
        resigning_color = "White" if game.board.turn == chess.WHITE else "Black"
        resign_message = f"{resigning_color} has resigned."
        
        # Log the resignation and display it in red
        logging.info(resign_message)
        self.ui.display_message(f"\n{RED}{resign_message}{ENDC}")

        # Update stats based on resignation
        result = "0-1" if resigning_color == "White" else "1-0"
        self._update_player_stats(game.players[chess.WHITE], game.players[chess.BLACK], result)
        
        # Ask to save and then exit
        save_choice = self.ui.get_user_input("Save final game log? (y/N): ").lower()
        if save_choice == 'y':
            self._save_game_log()
        self.ui.display_message("Exiting application.")
        sys.exit()

    def handle_in_game_menu(self, game):
        """Displays and handles the in-game menu options."""
        menu_choice = self.ui.display_game_menu_and_get_choice()
        if menu_choice == 'l':
            return self.handle_load_game_in_menu(game)
        elif menu_choice == 'p':
            action = self.handle_practice_load_in_menu(game)
            return game, action
        elif menu_choice == 's':
            self._save_game_log()
            return game, 'continue'
        elif menu_choice.startswith('?'):
            question = menu_choice[1:].strip()
            self._ask_expert(question)
            return game, 'continue'
        elif menu_choice == 'r':
            return game, 'continue'
        elif menu_choice == 'q':
            return game, 'quit_app'
        return game, 'continue'

    # --- Core Game Loop ---

    def play_game(self, game):
        """The main loop for playing a single game of chess."""
        auto_moves_remaining = 0
        while not game.is_game_over():
            self.ui.display_board(game.board)
            is_manual_move = False
            
            if auto_moves_remaining > 0:
                if game.board.turn == chess.WHITE:
                    auto_moves_remaining -= 1
            else:
                turn_color = "White" if game.board.turn else "Black"
                move_number = game.board.fullmove_number
                prompt = f"Move {move_number} ({turn_color}): Press Enter for AI move, 'q' to quit, 'm' for menu, a number for auto-play, or enter a move (e.g. e2e4): "
                user_input = self.ui.get_user_input(prompt)
                
                if user_input.lower() == 'q':
                    self._handle_resignation(game)
                
                elif user_input.lower() == 'm':
                    game, action = self.handle_in_game_menu(game)
                    if action == 'quit_app':
                        self._handle_resignation(game)
                    elif action == 'skip_turn':
                        continue
                    elif action == 'continue':
                        continue
                
                elif user_input.isdigit():
                    auto_moves_remaining = int(user_input)

                elif user_input == "": # User pressed Enter for AI move
                    is_manual_move = False

                else: # Any other text is treated as a manual move
                    is_manual_move = True
                    try:
                        game.make_manual_move(user_input)
                    except ValueError as e:
                        self.ui.display_message(f"{RED}Invalid move: {e}{ENDC}")

            if not is_manual_move:
                self.ui.display_turn_message(game)
                game.play_turn()

        # --- Game Over ---
        logging.info(f"Game Over. Result: {game.get_game_result()}")
        self.ui.display_game_over_message(game)
        self._update_player_stats(game.players[chess.WHITE], game.players[chess.BLACK], game.board.result())

        # Ask to save the completed game
        save_choice = self.ui.get_user_input("\nSave final game log? (y/N): ").lower()
        if save_choice == 'y':
            self._save_game_log()
        
        self.ui.get_user_input("Press Enter to return to the main menu.")

    # --- Main Application Runner ---

    def run(self):
        """Main function to run the chess application."""
        while True:
            choice = self.ui.display_main_menu()

            try:
                if choice == '1': # New Game
                    game = self.setup_new_game()
                    if game:
                        self.ui.display_game_start_message(game)
                        self.play_game(game)

                elif choice == '2': # Load Saved Game
                    saved_games = glob.glob('chess_game_*.log')
                    if not saved_games:
                        self.ui.display_message("No saved games found.")
                        continue
                    chosen_file = self.ui.display_saved_games_and_get_choice(saved_games)
                    if chosen_file:
                        game = self.load_game_from_log(chosen_file)
                        if game:
                            self.play_game(game)

                elif choice == '3': # Load Practice Position
                    with open('src/puzzles.json', 'r') as f:
                        positions = json.load(f)
                    
                    position = self.ui.display_practice_positions_and_get_choice(positions)
                    
                    if position and position not in ['?', 'm', 'q']:
                        white_player_key, black_player_key = self.ui.display_model_menu_and_get_choice(self.ai_models, self.stockfish_configs)
                        
                        player1 = self._create_player(white_player_key)
                        player2 = self._create_player(black_player_key)

                        game = Game(player1, player2, white_player_key=white_player_key, black_player_key=black_player_key)
                        game.set_board_from_fen(position['fen'])
                        game.initialize_game() # Log header with FEN
                        
                        self.ui.display_message(f"Loaded practice position: {position['name']}")
                        self.play_game(game)
                    elif position and position.startswith('?'):
                        question = position[1:].strip()
                        self._ask_expert(question)
                    elif position == 'm':
                        continue
                    elif position == 'q':
                        self.ui.display_message("Exiting application.")
                        sys.exit()

                elif choice == '4': # View Player Stats
                    self._view_player_stats()
                    continue

                elif choice.startswith('?'):
                    question = choice[1:].strip()
                    self._ask_expert(question)
                    continue

                elif choice == 'q': # Quit
                    self.ui.display_message("Thank you for playing!")
                    sys.exit()
            
            except (FileNotFoundError, RuntimeError, ValueError) as e:
                self.ui.display_message(f"{RED}An error occurred: {e}{ENDC}")
                self.ui.get_user_input("Press Enter to return to the main menu.")

if __name__ == "__main__":
    app = ChessApp()
    app.run()
