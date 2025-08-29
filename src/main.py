import chess
import logging
import os
import re
from datetime import datetime
import glob
import shutil
import json
import sys
from game import Game
from ai_player import AIPlayer
from ui_manager import UIManager

class ChessApp:
    def __init__(self):
        """Initializes the application, loading configurations."""
        self.ui = UIManager()
        self.white_openings = {}
        self.black_defenses = {}
        self.ai_models = {}
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
                self.chess_expert_model = config.get("chess_expert_model")
                if not self.chess_expert_model:
                    raise ValueError("chess_expert_model not found in config.")
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            self.ui.display_message(f"Error loading config.json: {e}")
            self.ui.display_message("Please ensure src/config.json exists and is correctly formatted.")
            sys.exit(1)

    def _ask_expert(self):
        """Handles the logic for asking the chess expert a question."""
        question = self.ui.get_chess_question()
        if not question:
            return

        self.ui.display_message("\nThinking deeply...")
        expert_player = AIPlayer(model_name=self.chess_expert_model)
        system_prompt = "You are a chess expert playing at the grandmaster level. Think deeply about the question."
        
        answer = expert_player.ask_question(question, system_prompt)
        
        self.ui.display_message("\n--- Grandmaster's Answer ---")
        self.ui.display_message(answer)
        self.ui.display_message("----------------------------")
        self.ui.get_user_input("Press Enter to return to the practice menu.")

    # --- Game Setup & Loading Methods ---

    @staticmethod
    def parse_log_header(log_file):
        """Parses the first line of the log to get game settings."""
        try:
            with open(log_file, 'r') as f:
                first_line = f.readline()
                pattern = r"White: (.*?) \(Strategy: (.*?)\) \| Black: (.*?) \(Strategy: (.*?)\)"
                match = re.search(pattern, first_line)
                if match:
                    white_model, white_strategy, black_model, black_strategy = match.groups()
                    return white_model.strip(), white_strategy.strip(), black_model.strip(), black_strategy.strip()
        except (FileNotFoundError, IndexError):
            return None
        return None

    def setup_new_game(self):
        """Handles the user interaction for setting up a new game."""
        white_opening_key, black_defense_key, white_model_key, black_model_key = \
            self.ui.display_setup_menu_and_get_choices(self.white_openings, self.black_defenses, self.ai_models)

        white_model_name = self.ai_models[white_model_key]
        black_model_name = self.ai_models[black_model_key]
        ai_player1 = AIPlayer(model_name=white_model_name)
        ai_player2 = AIPlayer(model_name=black_model_name)

        white_strategy = self.white_openings[white_opening_key]
        black_strategy = self.black_defenses[black_defense_key]

        return Game(ai_player1, ai_player2, white_strategy=white_strategy, black_strategy=black_strategy)

    def load_game_from_log(self, log_file):
        """Loads game settings and board state from a log file."""
        settings = self.parse_log_header(log_file)
        if settings:
            white_model_name, white_strategy, black_model_name, black_strategy = settings
            ai_player1 = AIPlayer(model_name=white_model_name)
            ai_player2 = AIPlayer(model_name=black_model_name)
            game = Game(ai_player1, ai_player2, white_strategy=white_strategy, black_strategy=black_strategy)
            
            if game.load_last_position_from_log(log_file):
                self.ui.display_message("\n--- Continuing Previous Game ---")
                return game
        return None

    # --- In-Game Menu Handlers ---

    def handle_load_game_in_menu(self, game):
        """Handles the 'load game' option from the in-game menu."""
        saved_games = glob.glob('chess_game_*.log')
        if not saved_games:
            self.ui.display_message("No saved games found.")
            return game, False

        chosen_file = self.ui.display_saved_games_and_get_choice(saved_games)
        if chosen_file:
            loaded_game = self.load_game_from_log(chosen_file)
            if loaded_game:
                logging.shutdown()
                shutil.copy(chosen_file, 'chess_game.log')
                logging.basicConfig(filename='chess_game.log', level=logging.INFO, format='%(asctime)s - %(message)s', filemode='a')
                logging.getLogger("httpx").setLevel(logging.WARNING)
                self.ui.display_message(f"Successfully loaded game from {chosen_file}.")
                return loaded_game, True
            else:
                self.ui.display_message("Could not load game from log file.")
        return game, False

    def handle_practice_load_in_menu(self, game):
        """Handles the 'load practice position' option from the in-game menu."""
        try:
            with open('src/endgame_positions.json', 'r') as f:
                positions = json.load(f)
            
            chosen_pos = self.ui.display_practice_positions_and_get_choice(positions)
            if chosen_pos:
                if game.set_board_from_fen(chosen_pos['fen']):
                    self.ui.display_message(f"Loaded position: {chosen_pos['name']}")
                    return True
                else:
                    self.ui.display_message("Failed to load position.")
        except (FileNotFoundError, json.JSONDecodeError):
            self.ui.display_message("Could not load practice positions file.")
        return False

    def handle_swap_model_in_menu(self, game):
        """Handles the 'swap AI model' option from the in-game menu."""
        player_choice = self.ui.get_user_input("Change model for (w)hite or (b)lack? ").lower()
        if player_choice in ['w', 'b']:
            color_to_swap = chess.WHITE if player_choice == 'w' else chess.BLACK
            
            self.ui.display_message("\n--- Available AI Models ---")
            for key, value in self.ai_models.items():
                self.ui.display_message(f"  {key}: {value}")
            
            model_key = self.ui.get_user_input("Enter the key of the new model (e.g., m1): ").lower()
            if model_key in self.ai_models:
                new_model_name = self.ai_models[model_key]
                new_player = AIPlayer(model_name=new_model_name)
                game.swap_player_model(color_to_swap, new_player)
                self.ui.display_message(f"Successfully swapped {'White' if color_to_swap == chess.WHITE else 'Black'}'s model to {new_model_name}.")
            else:
                self.ui.display_message("Invalid model key.")
        else:
            self.ui.display_message("Invalid selection. Please choose 'w' or 'b'.")

    def handle_in_game_menu(self, game):
        """Displays and handles the in-game menu options."""
        menu_choice = self.ui.display_game_menu_and_get_choice()
        if menu_choice == 'l':
            return self.handle_load_game_in_menu(game)
        elif menu_choice == 'p':
            skip_turn = self.handle_practice_load_in_menu(game)
            return game, skip_turn
        elif menu_choice == 's':
            self.handle_swap_model_in_menu(game)
        return game, False

    # --- Core Game Loop ---

    def play_game(self, game):
        """Contains the main game loop for playing a chess game."""
        auto_moves_remaining = 0
        while not game.is_game_over():
            game.display_board()
            is_manual_move = False

            if auto_moves_remaining > 0:
                if game.board.turn == chess.WHITE:
                    auto_moves_remaining -= 1
            else:
                turn_color = "White" if game.board.turn == chess.WHITE else "Black"
                prompt = f"Press Enter for AI move, 'q' to quit, 'm' for menu, a number for auto-play, or enter a move for {turn_color} (e.g. e2e4): "
                user_input = self.ui.get_user_input(prompt)
                
                if user_input.lower() == 'q':
                    save_choice = self.ui.get_user_input("Save game before quitting? (y/n): ").lower()
                    if save_choice == 'y':
                        logging.shutdown()
                        try:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            new_filename = f"chess_game_{timestamp}.log"
                            os.rename('chess_game.log', new_filename)
                            self.ui.display_message(f"Game saved as {new_filename}")
                        except FileNotFoundError:
                            self.ui.display_message("Log file not found, could not save.")
                    self.ui.display_message("Exiting game.")
                    break
                
                elif user_input.lower() == 'm':
                    game, skip_turn = self.handle_in_game_menu(game)
                    if skip_turn:
                        continue
                
                else:
                    try:
                        num_moves = int(user_input)
                        auto_moves_remaining = max(0, num_moves - 1)
                    except ValueError:
                        if user_input == '':
                            pass
                        else:
                            move_uci = user_input.strip().lower()
                            if game.make_move(move_uci, author="User"):
                                is_manual_move = True
                            else:
                                self.ui.display_message("Invalid or illegal move. Please try again.")
                                continue

            if not is_manual_move:
                self.ui.display_turn_message(game)
                move = game.players[game.board.turn].compute_move(game.board, strategy_message=game.strategies[game.board.turn])
                if move:
                    game.make_move(move, author="AI")
                else:
                    self.ui.display_message("AI failed to provide a move. Ending game.")
                    break
            
        logging.info(f"Game Over. Result: {game.get_game_result()}")
        self.ui.display_game_over_message(game)

    # --- Main Application Runner ---

    def run(self):
        """Main function to run the chess application."""
        while True:
            choice = self.ui.display_main_menu()

            if choice == '1': # New Game
                logging.basicConfig(filename='chess_game.log', level=logging.INFO, format='%(asctime)s - %(message)s', filemode='w')
                logging.getLogger("httpx").setLevel(logging.WARNING)
                
                game = self.setup_new_game()
                start_message = f"New Game Started. White: {game.players[chess.WHITE].model_name} (Strategy: {game.strategies[chess.WHITE]}) | Black: {game.players[chess.BLACK].model_name} (Strategy: {game.strategies[chess.BLACK]})"
                logging.info(start_message)
                
                self.ui.display_game_start_message(game)
                self.play_game(game)

            elif choice == '2': # Load Saved Game
                saved_games = glob.glob('chess_game_*.log')
                if not saved_games:
                    self.ui.display_message("No saved games found.")
                    continue
                
                chosen_file = self.ui.display_saved_games_and_get_choice(saved_games)
                if chosen_file:
                    shutil.copy(chosen_file, 'chess_game.log')
                    logging.basicConfig(filename='chess_game.log', level=logging.INFO, format='%(asctime)s - %(message)s', filemode='a')
                    logging.getLogger("httpx").setLevel(logging.WARNING)
                    
                    game = self.load_game_from_log('chess_game.log')
                    if game:
                        self.play_game(game)
                    else:
                        self.ui.display_message("Failed to load game.")

            elif choice == '3': # Load Practice Position
                try:
                    with open('src/endgame_positions.json', 'r') as f:
                        positions = json.load(f)
                    
                    while True: # Loop to allow asking questions or loading a position
                        chosen_item = self.ui.display_practice_positions_and_get_choice(positions)
                        
                        if chosen_item == '?':
                            self._ask_expert()
                            continue # Go back to the practice menu
                        
                        if chosen_item:
                            # This is a position dictionary, so proceed to load it
                            white_model_key, black_model_key = self.ui.display_model_menu_and_get_choice(self.ai_models)
                            
                            logging.basicConfig(filename='chess_game.log', level=logging.INFO, format='%(asctime)s - %(message)s', filemode='w')
                            logging.getLogger("httpx").setLevel(logging.WARNING)

                            white_model_name = self.ai_models[white_model_key]
                            black_model_name = self.ai_models[black_model_key]
                            ai_player1 = AIPlayer(model_name=white_model_name)
                            ai_player2 = AIPlayer(model_name=black_model_name)

                            checkmate_strategy = "Play for a direct checkmate."
                            game = Game(ai_player1, ai_player2, white_strategy=checkmate_strategy, black_strategy=checkmate_strategy)

                            if game.set_board_from_fen(chosen_item['fen']):
                                self.ui.display_message(f"Loaded position: {chosen_item['name']}")
                                self.ui.display_message(f"Strategy for both players: {checkmate_strategy}")
                                self.play_game(game)
                            else:
                                self.ui.display_message("Failed to load position.")
                            break # Exit the while loop after a game is played
                        else:
                            # User entered invalid input for position, or wants to go back
                            break # Exit to main menu

                except (FileNotFoundError, json.JSONDecodeError):
                    self.ui.display_message("Could not load practice positions file or invalid input.")

            elif choice == '4': # Quit
                self.ui.display_message("Thank you for playing!")
                sys.exit()

if __name__ == "__main__":
    app = ChessApp()
    app.run()                