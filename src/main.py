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
from human_player import HumanPlayer
from ui_manager import UIManager
from file_manager import FileManager

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

    def _create_player(self, player_key):
        """Creates a player object based on the provided key."""
        if player_key.startswith('m'):
            model_name = self.ai_models.get(player_key)
            if model_name:
                return AIPlayer(model_name=model_name)
        elif player_key.startswith('s'):
            config = self.stockfish_configs.get(player_key)
            if config:
                return StockfishPlayer(self.stockfish_path, parameters=config['parameters'])
        elif player_key == 'hu':
            # This path is for loading games, where we don't have the color context easily.
            # We'll create a generic human player and the game logic will handle the rest.
            # A more robust implementation might parse the player name from the log.
            return HumanPlayer(name="Human")
        
        raise ValueError(f"Unknown player key: {player_key}")

    def _create_player_with_name_prompt(self, player_key, color_str):
        """Creates a player, prompting for a name if the player is human."""        
        if player_key == 'hu':
            name = self.ui.get_human_player_name(color_str)
            return HumanPlayer(name=name)
        
        if player_key.startswith('m'):
            model_name = self.ai_models.get(player_key)
            if model_name:
                return AIPlayer(model_name=model_name)
        elif player_key.startswith('s'):
            config = self.stockfish_configs.get(player_key)
            if config:
                return StockfishPlayer(self.stockfish_path, parameters=config['parameters'])
        
        raise ValueError(f"Unknown player key: {player_key}")

    def _ask_expert(self, question=None):
        """Handles the logic for asking the chess expert a question."""
        if not question:
            question = self.ui.get_user_input("What is your chess question? ")
        
        if not question:
            return

        self.ui.display_message("\nAsking the Chess Master...")
        try:
            expert_player = AIPlayer(model_name=self.chess_expert_model)
            answer = expert_player.get_chess_fact_or_answer(question)
            
            self.ui.display_message("\n--- Chess Master's Answer ---")
            self.ui.display_message(answer)
            self.ui.display_message("-----------------------------")
        except Exception as e:
            self.ui.display_message(f"{RED}Sorry, I couldn't get an answer. Error: {e}{ENDC}")
        
        self.ui.get_user_input("Press Enter to return.")

    def _get_fun_fact(self):
        """Gets and displays a fun chess fact from the expert AI."""
        self.ui.display_message("\nGetting a fun chess fact...")
        try:
            expert_player = AIPlayer(model_name=self.chess_expert_model)
            # Passing no question gets a random fact
            answer = expert_player.get_chess_fact_or_answer()
            
            self.ui.display_message("\n--- Fun Chess Fact ---")
            self.ui.display_message(answer)
            self.ui.display_message("----------------------")
        except Exception as e:
            self.ui.display_message(f"{RED}Sorry, I couldn't get a fact. Error: {e}{ENDC}")

        self.ui.get_user_input("Press Enter to return to the main menu.")

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

            player1 = self._create_player(header['white_key'])
            player2 = self._create_player(header['black_key'])
            
            game = Game(player1, player2, white_strategy=header['white_strategy'], black_strategy=header['black_strategy'], white_player_key=header['white_key'], black_player_key=header['black_key'])
            
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
    def parse_log_header(lines, all_keys):
        """Parses the header of a log file to extract game setup information."""
        header = {}

        for line in lines:
            if "Move:" in line:
                break # End of header

            # Modern format (explicit keys)
            if "White Player Key:" in line:
                header["white_key"] = line.split(":", 1)[1].strip()
            elif "Black Player Key:" in line:
                header["black_key"] = line.split(":", 1)[1].strip()
            
            # Fallback for older logs (infer keys)
            elif "White:" in line and "white_key" not in header:
                player_name = line.split(":", 1)[1].strip()
                for key in all_keys:
                    if f"({key})" in player_name:
                        header["white_key"] = key
                        break
            elif "Black:" in line and "black_key" not in header:
                player_name = line.split(":", 1)[1].strip()
                for key in all_keys:
                    if f"({key})" in player_name:
                        header["black_key"] = key
                        break

            # Common fields
            elif "White Strategy:" in line:
                header["white_strategy"] = line.split(":", 1)[1].strip()
            elif "Black Strategy:" in line:
                header["black_strategy"] = line.split(":", 1)[1].strip()
            elif "Initial FEN:" in line:
                header["initial_fen"] = line.split(":", 1)[1].strip()

        # Validation
        required_fields = ["white_key", "black_key", "initial_fen"]
        missing_fields = [field for field in required_fields if field not in header]
        
        # Set default for optional strategy fields
        header.setdefault('white_strategy', 'No Classic Chess Opening')
        header.setdefault('black_strategy', 'No Classic Chess Opening')

        if not missing_fields:
            return header, None
        else:
            reason = f"Could not find required fields in log header: {', '.join(missing_fields)}."
            return None, reason

    # --- In-Game Menu Handlers ---

    def handle_load_game_in_menu(self, game):
        """Handles the 'load game' option from the in-game menu."""
        game_summaries = self.file_manager.get_saved_game_summaries()
        if not game_summaries:
            self.ui.display_message("No saved games found.")
            return game, 'continue'

        chosen_summary = self.ui.display_saved_games_and_get_choice(game_summaries)
        
        if chosen_summary == 'm':
            return game, 'quit_to_menu'
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
                return loaded_game, 'skip_turn'
        return game, 'continue'

    def handle_practice_load_in_menu(self, game):
        """Handles the 'load practice position' option from the in-game menu."""
        with open('src/puzzles.json', 'r') as f:
            positions = json.load(f)
        
        position = self.ui.display_practice_positions_and_get_choice(positions)

        if position and position not in ['?', 'm', 'q']:
            white_player_key, black_player_key = self.ui.display_model_menu_and_get_choice(self.ai_models, self.stockfish_configs)
            
            player1 = self._create_player_with_name_prompt(white_player_key, "White")
            player2 = self._create_player_with_name_prompt(black_player_key, "Black")

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

    def _update_player_stats(self, white_player, black_player, result):
        """Updates and saves the win/loss/draw stats for players."""
        stats = self.file_manager.load_player_stats()
        
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
        
        self.file_manager.save_player_stats(stats)
        self.ui.display_message("\nPlayer stats have been updated.")

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
            self.file_manager.save_game_log()
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
            self.file_manager.save_game_log()
            return game, 'continue'
        elif menu_choice.startswith('?'):
            question = menu_choice[1:].strip()
            self._ask_expert(question)
            return game, 'continue'
        elif menu_choice == 'r':
            return game, 'continue'
        elif menu_choice == 'q':
            # The quit logic is now handled in the play_game loop
            return game, 'quit_app'
        return game, 'continue'

    # --- Core Game Loop ---

    def play_game(self, game):
        """The main loop for a single game."""
        auto_moves_remaining = 0

        while not game.board.is_game_over():
            self.ui.display_board(game.board)
            current_player = game.get_current_player()

            try:
                if isinstance(current_player, HumanPlayer):
                    # --- Human Player's Turn ---
                    turn_color = "White" if game.board.turn else "Black"
                    move_number = game.board.fullmove_number
                    prompt = f"Move {move_number} ({current_player.model_name} as {turn_color}): Enter your move (e.g. e2e4), 'q' to quit, or 'm' for menu: "
                    user_input = self.ui.get_user_input(prompt)

                    if user_input.lower() == 'q':
                        if self._handle_quit_request(game):
                            continue # User cancelled quit
                    elif user_input.lower() == 'm':
                        game, action = self.handle_in_game_menu(game)
                        if action == 'quit_app':
                            if self._handle_quit_request(game):
                                continue
                        elif action in ['skip_turn', 'continue']:
                            continue
                    else:
                        game.make_manual_move(user_input)

                else:
                    # --- AI Player's Turn ---
                    if auto_moves_remaining > 0:
                        if game.board.turn == chess.WHITE: # Decrement only after a full move cycle
                            auto_moves_remaining -= 1
                    else: # Not auto-playing, so prompt for interaction
                        self.ui.display_turn_message(game) # "AI is thinking..."
                        # Check for user interruption before AI move
                        # This is a simplified non-blocking check for this example
                        # A real implementation would need threading for a true non-blocking input
                        
                    game.play_turn()

            except ValueError as e:
                self.ui.display_message(f"{RED}Invalid move: {e}{ENDC}")
                continue
        
        self.ui.display_game_over_message(game)
        self._update_player_stats(game.players[chess.WHITE], game.players[chess.BLACK], game.get_game_result())
        
        # Ask to save the completed game
        save_choice = self.ui.get_user_input("\nSave final game log? (y/N): ").lower()
        if save_choice == 'y':
            self.file_manager.save_game_log()
        
        self.ui.get_user_input("Press Enter to return to the main menu.")

    # --- Main Application Runner ---

    def run(self):
        """Main function to run the chess application."""
        while True:
            choice = self.ui.display_main_menu()

            try:
                if choice == '1': # New Game
                    self._initialize_new_game_log()
                    game = self.setup_new_game()
                    if game:
                        self.ui.display_game_start_message(game)
                        self.play_game(game)

                elif choice == '2': # Load Saved Game
                    game_summaries = self.file_manager.get_saved_game_summaries()
                    if not game_summaries:
                        self.ui.display_message("No saved games found.")
                        continue
                    
                    chosen_summary = self.ui.display_saved_games_and_get_choice(game_summaries)

                    if chosen_summary == 'm':
                        continue
                    elif chosen_summary == 'q':
                        self.ui.display_message("Exiting application.")
                        sys.exit()
                    elif chosen_summary:
                        chosen_file = chosen_summary['filename']
                        game = self.load_game_from_log(chosen_file)
                        if game:
                            self.play_game(game)

                elif choice == '3': # Load Practice Position
                    with open('src/puzzles.json', 'r') as f:
                        positions = json.load(f)
                    
                    position = self.ui.display_practice_positions_and_get_choice(positions)
                    
                    if position and position not in ['?', 'm', 'q']:
                        white_player_key, black_player_key = self.ui.display_model_menu_and_get_choice(self.ai_models, self.stockfish_configs)
                        
                        player1 = self._create_player_with_name_prompt(white_player_key, "White")
                        player2 = self._create_player_with_name_prompt(black_player_key, "Black")

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

                elif choice == '5': # Fun Chess Fact
                    self._get_fun_fact()
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

# --- Entry Point ---
if __name__ == "__main__":
    app = ChessApp()
    app.run()