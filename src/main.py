import chess
import logging
import os
import re
from datetime import datetime
import glob
import shutil
import json
import sys
from game import Game, BLUE, ENDC
from ai_player import AIPlayer

class ChessApp:
    def __init__(self):
        """Initializes the application, loading configurations."""
        self.white_openings = {'1': "Play the Ruy Lopez.", '2': "Play the Italian Game.", '3': "Play the Queen's Gambit.", '4': "Play the London System.", '5': "Play the King's Gambit."}
        self.black_defenses = {'a': "Play the Sicilian Defense.", 'b': "Play the French Defense.", 'c': "Play the Caro-Kann Defense."}
        self.ai_models = {'m1': "openai/gpt-4o", 'm2': "deepseek/deepseek-chat-v3.1", 'm3': "google/gemini-1.5-pro", 'm4': "anthropic/claude-3-opus", 'm5': "meta-llama/llama-3-70b-instruct"}

    # --- UI & Menu Methods ---

    def display_setup_menu_and_get_choices(self):
        """Displays all setup menus in columns and gets the user's combined choice."""
        white_list = [f"  {k}: {v.replace('Play the ', '')}" for k, v in self.white_openings.items()]
        black_list = [f"  {k}: {v.replace('Play the ', '')}" for k, v in self.black_defenses.items()]
        model_list = [f"  {k}: {v}" for k, v in self.ai_models.items()]

        white_width = max(len(s) for s in white_list) + 4
        black_width = max(len(s) for s in black_list) + 4

        # Print headers
        print(f"\n{'--- White Openings ---':<{white_width}}{'--- Black Defenses ---':<{black_width}}{'--- AI Models ---'}")
        
        # Print rows
        num_rows = max(len(white_list), len(black_list), len(model_list))
        for i in range(num_rows):
            white_col = white_list[i] if i < len(white_list) else ""
            black_col = black_list[i] if i < len(black_list) else ""
            model_col = model_list[i] if i < len(model_list) else ""
            print(f"{white_col:<{white_width}}{black_col:<{black_width}}{model_col}")

        while True:
            choice = input("\nEnter choices for openings and models (e.g., '1a m1m2'): ")


            parts = choice.split()
            
            if len(parts) == 2:
                opening_choice, model_choice = parts[0], parts[1]
                if len(opening_choice) == 2 and len(model_choice) == 4:
                    white_opening_key, black_defense_key = opening_choice[0], opening_choice[1]
                    white_model_key, black_model_key = model_choice[:2], model_choice[2:]

                    if (white_opening_key in self.white_openings and
                        black_defense_key in self.black_defenses and
                        white_model_key in self.ai_models and
                        black_model_key in self.ai_models):
                        return white_opening_key, black_defense_key, white_model_key, black_model_key
            
            print("Invalid input. Please enter a valid string like '1a m1m2'.")

    def display_model_menu_and_get_choice(self):
        """Displays AI model options and gets the user's choice."""
        print("\n--- Choose AI Models for Practice ---")
        for key, value in self.ai_models.items():
            print(f"  {key}: {value}")

        while True:
            choice = input("\nEnter your choice for White and Black models (e.g., 'm1m2'): ").strip().lower()
            if len(choice) == 4 and choice.startswith('m') and choice[2] == 'm':
                white_model_key = choice[:2]
                black_model_key = choice[2:]
                if white_model_key in self.ai_models and black_model_key in self.ai_models:
                    return white_model_key, black_model_key
            
            print("Invalid input. Please enter a valid choice for both models (e.g., 'm1m2').")

    @staticmethod
    def display_main_menu():
        """Displays the main menu and gets the user's choice."""
        print("\n--- Main Menu ---")
        print("  1: Play a New AI vs AI Game")
        print("  2: Load a Saved Game")
        print("  3: Load a Practice Position")
        print("  4: Quit")
        while True:
            choice = input("Enter your choice (1-4): ").strip()
            if choice in ['1', '2', '3', '4']:
                return choice
            else:
                print("Invalid choice. Please enter a number from 1 to 4.")

    @staticmethod
    def display_game_menu_and_get_choice():
        """Displays the in-game menu and gets the user's choice."""
        print("\n--- Game Menu ---")
        print("  l: Load a saved game")
        print("  p: Load a practice position")
        print("  s: Swap AI Model")
        print("  c: Cancel and continue game")
        while True:
            choice = input("Enter your choice: ").strip().lower()
            if choice in ['l', 'p', 's', 'c']:
                return choice
            else:
                print("Invalid choice. Please enter 'l', 'p', 's', or 'c'.")

    # --- Game Setup & Loading Methods ---

    @staticmethod
    def parse_log_header(log_file):
        """Parses the first line of the log to get game settings."""
        try:
            with open(log_file, 'r') as f:
                first_line = f.readline()
                # Example: ... - New Game Started. White: openai/gpt-4o (Strategy: Play the Ruy Lopez.) | Black: deepseek/deepseek-chat-v3.1 (Strategy: Play the Sicilian Defense.)
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
        # Get user's choices for strategies and models
        white_opening_key, black_defense_key, white_model_key, black_model_key = \
            self.display_setup_menu_and_get_choices()

        white_model_name = self.ai_models[white_model_key]
        black_model_name = self.ai_models[black_model_key]
        ai_player1 = AIPlayer(model_name=white_model_name) # White
        ai_player2 = AIPlayer(model_name=black_model_name) # Black

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
                print("\n--- Continuing Previous Game ---")
                return game
        return None

    # --- In-Game Menu Handlers ---

    def handle_load_game_in_menu(self, game):
        """Handles the 'load game' option from the in-game menu."""
        saved_games = glob.glob('chess_game_*.log')
        if not saved_games:
            print("No saved games found.")
            return game, False # Return original game, don't skip turn

        print("\n--- Saved Games ---")
        for i, filename in enumerate(saved_games):
            print(f"  {i + 1}: {filename}")
        
        try:
            file_choice = int(input("Enter the number of the game to load: "))
            if 1 <= file_choice <= len(saved_games):
                chosen_file = saved_games[file_choice - 1]
                loaded_game = self.load_game_from_log(chosen_file)
                if loaded_game:
                    logging.shutdown()
                    shutil.copy(chosen_file, 'chess_game.log')
                    logging.basicConfig(filename='chess_game.log', level=logging.INFO, format='%(asctime)s - %(message)s', filemode='a')
                    logging.getLogger("httpx").setLevel(logging.WARNING)
                    print(f"Successfully loaded game from {chosen_file}.")
                    return loaded_game, True # Return new game, skip turn
                else:
                    print("Could not load game from log file.")
            else:
                print("Invalid number.")
        except ValueError:
            print("Invalid input.")
        return game, False # On failure, return original game

    @staticmethod
    def handle_practice_load_in_menu(game):
        """Handles the 'load practice position' option from the in-game menu."""
        try:
            with open('src/endgame_positions.json', 'r') as f:
                positions = json.load(f)
            
            print("\n--- Practice Checkmate Positions ---")
            for i, pos in enumerate(positions):
                print(f"  {i + 1}: {pos['name']}")
            
            pos_choice = int(input("Enter the number of the position to load: "))
            if 1 <= pos_choice <= len(positions):
                chosen_pos = positions[pos_choice - 1]
                if game.set_board_from_fen(chosen_pos['fen']):
                    print(f"Loaded position: {chosen_pos['name']}")
                    return True # Skip turn
                else:
                    print("Failed to load position.")
            else:
                print("Invalid number.")
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            print("Could not load practice positions file or invalid input.")
        return False # Don't skip turn

    def handle_swap_model_in_menu(self, game):
        """Handles the 'swap AI model' option from the in-game menu."""
        player_choice = input("Change model for (w)hite or (b)lack? ").strip().lower()
        if player_choice in ['w', 'b']:
            color_to_swap = chess.WHITE if player_choice == 'w' else chess.BLACK
            
            print("\n--- Available AI Models ---")
            for key, value in self.ai_models.items():
                print(f"  {key}: {value}")
            
            model_key = input("Enter the key of the new model (e.g., m1): ").strip().lower()
            if model_key in self.ai_models:
                new_model_name = self.ai_models[model_key]
                new_player = AIPlayer(model_name=new_model_name)
                game.swap_player_model(color_to_swap, new_player)
                print(f"Successfully swapped {'White' if color_to_swap == chess.WHITE else 'Black'}'s model to {new_model_name}.")
            else:
                print("Invalid model key.")
        else:
            print("Invalid selection. Please choose 'w' or 'b'.")

    def handle_in_game_menu(self, game):
        """Displays and handles the in-game menu options."""
        menu_choice = self.display_game_menu_and_get_choice()
        if menu_choice == 'l':
            return self.handle_load_game_in_menu(game)
        elif menu_choice == 'p':
            skip_turn = self.handle_practice_load_in_menu(game)
            return game, skip_turn
        elif menu_choice == 's':
            self.handle_swap_model_in_menu(game)
        # For 's' and 'c', we don't skip the turn and return the original game
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
                user_input = input(f"Press Enter for AI move, 'q' to quit, 'm' for menu, a number for auto-play, or enter a move for {turn_color} (e.g. e2e4): ")
                
                if user_input.lower() == 'q':
                    save_choice = input("Save game before quitting? (y/n): ").strip().lower()
                    if save_choice == 'y':
                        logging.shutdown()
                        try:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            new_filename = f"chess_game_{timestamp}.log"
                            os.rename('chess_game.log', new_filename)
                            print(f"Game saved as {new_filename}")
                        except FileNotFoundError:
                            print("Log file not found, could not save.")
                    print("Exiting game.")
                    break # Exit game loop
                
                elif user_input.lower() == 'm':
                    game, skip_turn = self.handle_in_game_menu(game)
                    if skip_turn:
                        continue # Restart loop to show new board
            
            if not is_manual_move:
                turn = game.board.turn
                strategy = game.strategies[turn]
                current_player = game.players[turn]
                player_name = "Player 1 (White)" if turn == chess.WHITE else "Player 2 (Black)"
                
                move_number = game.board.fullmove_number
                print(f"\n{BLUE}Move {move_number}:{ENDC} {player_name}'s turn ({current_player.model_name})...")
                if strategy and game.board.fullmove_number <= 3:
                    print(f"Strategy: {strategy}")
                
                move = current_player.compute_move(game.board, strategy_message=strategy)
                if move:
                    game.make_move(move, author="AI")
                else:
                    print("AI failed to provide a move. Ending game.")
                    break
            
        # Post-game summary, correctly indented within play_game method
        result = game.get_game_result()
        logging.info(f"Game Over. Result: {result}")
        print("\n--- Game Over ---")
        game.display_board()
        print(f"Result: {result}")
        print("Game history has been saved to chess_game.log")

    # --- Main Application Runner ---

    def run(self):
        """Main function to run the chess application."""
        while True:
            choice = self.display_main_menu()

            if choice == '1': # New Game
                logging.basicConfig(filename='chess_game.log', level=logging.INFO, format='%(asctime)s - %(message)s', filemode='w')
                logging.getLogger("httpx").setLevel(logging.WARNING)
                
                game = self.setup_new_game()
                start_message = f"New Game Started. White: {game.players[chess.WHITE].model_name} (Strategy: {game.strategies[chess.WHITE]}) | Black: {game.players[chess.BLACK].model_name} (Strategy: {game.strategies[chess.BLACK]})"
                logging.info(start_message)
                
                print("\n--- Starting AI vs AI Chess Game ---")
                print(f"Player 1 (White): {game.players[chess.WHITE].model_name} (Strategy: {game.strategies[chess.WHITE]})")
                print(f"Player 2 (Black): {game.players[chess.BLACK].model_name} (Strategy: {game.strategies[chess.BLACK]})")
                print("------------------------------------")
                self.play_game(game)

            elif choice == '2': # Load Saved Game
                saved_games = glob.glob('chess_game_*.log')
                if not saved_games:
                    print("No saved games found.")
                    continue
                
                print("\n--- Saved Games ---")
                for i, filename in enumerate(saved_games):
                    print(f"  {i + 1}: {filename}")
                
                try:
                    file_choice = int(input("Enter the number of the game to load: "))
                    if 1 <= file_choice <= len(saved_games):
                        chosen_file = saved_games[file_choice - 1]
                        shutil.copy(chosen_file, 'chess_game.log')
                        
                        logging.basicConfig(filename='chess_game.log', level=logging.INFO, format='%(asctime)s - %(message)s', filemode='a')
                        logging.getLogger("httpx").setLevel(logging.WARNING)
                        
                        game = self.load_game_from_log('chess_game.log')
                        if game:
                            self.play_game(game)
                        else:
                            print("Failed to load game.")
                    else:
                        print("Invalid number.")
                except ValueError:
                    print("Invalid input.")

            elif choice == '3': # Load Practice Position
                try:
                    with open('src/endgame_positions.json', 'r') as f:
                        positions = json.load(f)
                    
                    print("\n--- Practice Checkmate Positions ---")
                    for i, pos in enumerate(positions):
                        print(f"  {i + 1}: {pos['name']}")
                    
                    pos_choice = int(input("Enter the number of the position to load: "))
                    if 1 <= pos_choice <= len(positions):
                        white_model_key, black_model_key = self.display_model_menu_and_get_choice()
                        
                        logging.basicConfig(filename='chess_game.log', level=logging.INFO, format='%(asctime)s - %(message)s', filemode='w')
                        logging.getLogger("httpx").setLevel(logging.WARNING)

                        white_model_name = self.ai_models[white_model_key]
                        black_model_name = self.ai_models[black_model_key]
                        ai_player1 = AIPlayer(model_name=white_model_name)
                        ai_player2 = AIPlayer(model_name=black_model_name)

                        checkmate_strategy = "Play for a direct checkmate."
                        game = Game(ai_player1, ai_player2, white_strategy=checkmate_strategy, black_strategy=checkmate_strategy)

                        chosen_pos = positions[pos_choice - 1]
                        if game.set_board_from_fen(chosen_pos['fen']):
                            print(f"Loaded position: {chosen_pos['name']}")
                            print(f"Strategy for both players: {checkmate_strategy}")
                            self.play_game(game)
                        else:
                            print("Failed to load position.")
                    else:
                        print("Invalid number.")
                except (FileNotFoundError, json.JSONDecodeError, ValueError):
                    print("Could not load practice positions file or invalid input.")

            elif choice == '4': # Quit
                print("Thank you for playing!")
                sys.exit()


if __name__ == "__main__":
    app = ChessApp()
    app.run()