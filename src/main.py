import chess
import logging
import os
import re
from datetime import datetime
import glob
import shutil
import json
import sys
from game import Game, RED, ENDC
from ai_player import AIPlayer
from stockfish_player import StockfishPlayer
from ui_manager import UIManager

class ChessApp:
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

    def _ask_expert(self):
        """Handles the logic for asking the chess expert a question."""
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

        return Game(player1, player2, white_strategy=white_strategy, black_strategy=black_strategy)

    def load_game_from_log(self, log_file):
        """Loads game settings and board state from a log file."""
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            header = self.parse_log_header(lines)
            if not header:
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
        header = {}
        patterns = {
            'white_key': r"White: .* \((m\d+|s\d+)\)",
            'black_key': r"Black: .* \((m\d+|s\d+)\)",
            'white_strategy': r"White Strategy: (.+)",
            'black_strategy': r"Black Strategy: (.+)",
            'initial_fen': r"Initial FEN: (.+)"
        }
        for line in lines[:5]: # Header should be in the first few lines
            for key, pattern in patterns.items():
                match = re.search(pattern, line)
                if match:
                    header[key] = match.group(1).strip()
        return header if len(header) >= 4 else None

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
            else:
                self.ui.display_message("Could not load game from log file.")
        return game, 'continue'

    def handle_practice_load_in_menu(self, game):
        """Handles the 'load practice position' option from the in-game menu."""
        try:
            with open('src/endgame_positions.json', 'r') as f:
                positions = json.load(f)
            
            chosen_pos = self.ui.display_practice_positions_and_get_choice(positions)
            if chosen_pos and chosen_pos != '?':
                if game.set_board_from_fen(chosen_pos['fen']):
                    self.ui.display_message(f"Loaded position: {chosen_pos['name']}")
                    return 'skip_turn'
                else:
                    self.ui.display_message("Failed to load position.")
            elif chosen_pos == '?':
                self._ask_expert()
        except (FileNotFoundError, json.JSONDecodeError):
            self.ui.display_message("Could not load practice positions file or invalid input.")
        return 'continue'

    def handle_swap_model_in_menu(self, game):
        """Handles swapping an AI model mid-game."""
        self.ui.display_message("Swap model feature is currently for AI players.")

    def handle_in_game_menu(self, game):
        """Displays and handles the in-game menu options."""
        menu_choice = self.ui.display_game_menu_and_get_choice()
        if menu_choice == 'l':
            return self.handle_load_game_in_menu(game)
        elif menu_choice == 'p':
            action = self.handle_practice_load_in_menu(game)
            return game, action
        elif menu_choice == 's':
            self.handle_swap_model_in_menu(game)
            return game, 'continue'
        elif menu_choice == '?':
            self._ask_expert()
            return game, 'continue'
        elif menu_choice == 'q':
            return game, 'exit_to_main'
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
                prompt = f"Press Enter for AI move, 'q' to quit, 'm' for menu, a number for auto-play, or enter a move for {turn_color} (e.g. e2e4): "
                user_input = self.ui.get_user_input(prompt)
                
                if user_input.lower() == 'q':
                    save_choice = self.ui.get_user_input("Save game before quitting? (y/N): ").lower()
                    if save_choice == 'y':
                        logging.shutdown()
                        try:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            shutil.copy('chess_game.log', f'chess_game_{timestamp}.log')
                            self.ui.display_message(f"Game saved as chess_game_{timestamp}.log")
                        except FileNotFoundError:
                            self.ui.display_message("Log file not found, could not save.")
                    self.ui.display_message("Exiting game.")
                    break
                
                elif user_input.lower() == 'm':
                    game, action = self.handle_in_game_menu(game)
                    if action == 'skip_turn':
                        continue
                    elif action == 'exit_to_main':
                        self.ui.display_message("\nReturning to Main Menu...")
                        return
                
                else:
                    try:
                        num_moves = int(user_input)
                        auto_moves_remaining = num_moves * 2 -1
                    except ValueError:
                        if user_input == '':
                            pass
                        else:
                            move_uci = user_input.strip().lower()
                            if game.make_move(move_uci, author="User"):
                                is_manual_move = True
                            else:
                                self.ui.display_message(f"{RED}Invalid or illegal move. Please try again.{ENDC}")
                                continue

            if not is_manual_move:
                self.ui.display_turn_message(game)
                game.play_turn()

        logging.info(f"Game Over. Result: {game.get_game_result()}")
        self.ui.display_game_over_message(game)

        # Ask to save the completed game
        save_choice = self.ui.get_user_input("\nSave final game log? (y/N): ").lower()
        if save_choice == 'y':
            logging.shutdown()
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                shutil.copy('chess_game.log', f'chess_game_{timestamp}.log')
                self.ui.display_message(f"Game saved as chess_game_{timestamp}.log")
            except FileNotFoundError:
                self.ui.display_message("Log file not found, could not save.")
        
        self.ui.get_user_input("Press Enter to return to the main menu.")

    # --- Main Application Runner ---

    def run(self):
        """Main function to run the chess application."""
        while True:
            choice = self.ui.display_main_menu()

            try:
                if choice == '1': # New Game
                    logging.basicConfig(filename='chess_game.log', level=logging.INFO, format='%(asctime)s - %(message)s', filemode='w')
                    logging.getLogger("httpx").setLevel(logging.WARNING)
                    game = self.setup_new_game()
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
                        else:
                            self.ui.display_message("Failed to load game.")

                elif choice == '3': # Load Practice Position
                    with open('src/endgame_positions.json', 'r') as f:
                        positions = json.load(f)
                    
                    while True:
                        chosen_item = self.ui.display_practice_positions_and_get_choice(positions)
                        
                        if chosen_item == '?':
                            self._ask_expert()
                            continue
                        
                        if chosen_item:
                            white_player_key, black_player_key = self.ui.display_model_menu_and_get_choice(self.ai_models, self.stockfish_configs)
                            
                            logging.basicConfig(filename='chess_game.log', level=logging.INFO, format='%(asctime)s - %(message)s', filemode='w')
                            logging.getLogger("httpx").setLevel(logging.WARNING)

                            player1 = self._create_player(white_player_key)
                            player2 = self._create_player(black_player_key)

                            checkmate_strategy = "Play for a direct checkmate."
                            game = Game(player1, player2, white_strategy=checkmate_strategy, black_strategy=checkmate_strategy)

                            if game.set_board_from_fen(chosen_item['fen']):
                                self.ui.display_message(f"Loaded position: {chosen_item['name']}")
                                self.play_game(game)
                            else:
                                self.ui.display_message("Failed to load position.")
                            break
                        else:
                            break

                elif choice == '?':
                    self._ask_expert()
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