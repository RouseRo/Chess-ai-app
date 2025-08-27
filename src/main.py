import chess
import logging
import os
import re
from datetime import datetime
import glob
import shutil
import json
from game import Game, BLUE, ENDC
from ai_player import AIPlayer

def display_setup_menu_and_get_choices(white_openings, black_defenses, ai_models):
    """Displays all setup menus in columns and gets the user's combined choice."""
    
    white_list = [f"  {k}: {v.replace('Play the ', '')}" for k, v in white_openings.items()]
    black_list = [f"  {k}: {v.replace('Play the ', '')}" for k, v in black_defenses.items()]
    model_list = [f"  {k}: {v}" for k, v in ai_models.items()]

    # Determine column widths for alignment
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
        choice = input("\nEnter choices for openings and models (e.g., '1a m1m2'): ").strip().lower()
        parts = choice.split()
        
        if len(parts) == 2:
            opening_choice, model_choice = parts[0], parts[1]
            if len(opening_choice) == 2 and len(model_choice) == 4:
                white_opening_key, black_defense_key = opening_choice[0], opening_choice[1]
                white_model_key, black_model_key = model_choice[:2], model_choice[2:]

                if (white_opening_key in white_openings and
                    black_defense_key in black_defenses and
                    white_model_key in ai_models and
                    black_model_key in ai_models):
                    return white_opening_key, black_defense_key, white_model_key, black_model_key
        
        print("Invalid input. Please enter a valid string like '1a m1m2'.")


def display_game_menu_and_get_choice():
    """Displays the in-game menu and gets the user's choice."""
    print("\n--- Game Menu ---")
    print("  l: Load a saved game")
    print("  p: Load a practice position")
    print("  c: Cancel and continue game")
    while True:
        choice = input("Enter your choice: ").strip().lower()
        if choice in ['l', 'p', 'c']:
            return choice
        else:
            print("Invalid choice. Please enter 'l', 'p', or 'c'.")


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

def setup_new_game(white_openings, black_defenses, ai_models):
    """Handles the user interaction for setting up a new game."""
    # Get user's choices for strategies and models
    white_opening_key, black_defense_key, white_model_key, black_model_key = \
        display_setup_menu_and_get_choices(white_openings, black_defenses, ai_models)

    white_model_name = ai_models[white_model_key]
    black_model_name = ai_models[black_model_key]
    ai_player1 = AIPlayer(model_name=white_model_name) # White
    ai_player2 = AIPlayer(model_name=black_model_name) # Black

    white_strategy = white_openings[white_opening_key]
    black_strategy = black_defenses[black_defense_key]

    return Game(ai_player1, ai_player2, white_strategy=white_strategy, black_strategy=black_strategy)

def load_game_from_log(log_file):
    """Loads game settings and board state from a log file."""
    settings = parse_log_header(log_file)
    if settings:
        white_model_name, white_strategy, black_model_name, black_strategy = settings
        ai_player1 = AIPlayer(model_name=white_model_name)
        ai_player2 = AIPlayer(model_name=black_model_name)
        game = Game(ai_player1, ai_player2, white_strategy=white_strategy, black_strategy=black_strategy)
        
        if game.load_last_position_from_log(log_file):
            print("\n--- Continuing Previous Game ---")
            return game
    return None

def main():
    game = None
    file_mode = 'w' # Default to overwrite log

    # Check for saved games at startup
    saved_games = glob.glob('chess_game_*.log')
    if saved_games:
        
        welcome_message = "WELCOME BACK, CHESS MASTER!"
        found_message = f"I found {len(saved_games)} saved game(s) for you."
        box_width = 55

        print(f"\n{BLUE}")
        print("*" * box_width)
        print("*" + " " * (box_width - 2) + "*")
        print("*" + welcome_message.center(box_width - 2) + "*")
        print("*" + found_message.center(box_width - 2) + "*")
        print("*" + " " * (box_width - 2) + "*")
        print("*" * box_width)
        print(f"{ENDC}")
        
        load_choice = input("Would you like to load one? (y/n): ").strip().lower()
        if load_choice == 'y':
            print("\n--- Saved Games ---")
            for i, filename in enumerate(saved_games):
                print(f"  {i + 1}: {filename}")
            
            try:
                file_choice = int(input("Enter the number of the game to load: "))
                if 1 <= file_choice <= len(saved_games):
                    chosen_file = saved_games[file_choice - 1]
                    # Copy the chosen saved game to the active log file
                    shutil.copy(chosen_file, 'chess_game.log')
                    file_mode = 'a' # Set logger to append
                    game = load_game_from_log('chess_game.log')
                    if not game:
                        print("Failed to load game. Starting a new game instead.")
                        file_mode = 'w' # Revert to overwrite for new game
                else:
                    print("Invalid number. Starting a new game.")
            except ValueError:
                print("Invalid input. Starting a new game.")

    # Set up logging
    logging.basicConfig(filename='chess_game.log', level=logging.INFO, 
                        format='%(asctime)s - %(message)s', filemode=file_mode)

    # Silence the HTTP logger from the openai library to keep the log clean
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Dictionaries for opening strategies
    white_openings = {
        '1': "Play the Ruy Lopez.",
        '2': "Play the Italian Game.",
        '3': "Play the Queen's Gambit.",
        '4': "Play the London System.",
        '5': "Play the King's Gambit."
    }

    black_defenses = {
        'a': "Play the Sicilian Defense.",
        'b': "Play the French Defense.",
        'c': "Play the Caro-Kann Defense."
    }

    # Dictionary for AI models
    ai_models = {
        'm1': "openai/gpt-4o",
        'm2': "deepseek/deepseek-chat-v3.1",
        'm3': "google/gemini-1.5-pro",
        'm4': "anthropic/claude-3-opus",
        'm5': "meta-llama/llama-3-70b-instruct"
    }

    # Set up a new game if one wasn't loaded
    if not game:
        game = setup_new_game(white_openings, black_defenses, ai_models)
        # Log the start of the new game
        start_message = f"New Game Started. White: {game.players[chess.WHITE].model_name} (Strategy: {game.strategies[chess.WHITE]}) | Black: {game.players[chess.BLACK].model_name} (Strategy: {game.strategies[chess.BLACK]})"
        logging.info(start_message)

    white_player = game.players[chess.WHITE]
    black_player = game.players[chess.BLACK]
    white_strategy = game.strategies[chess.WHITE]
    black_strategy = game.strategies[chess.BLACK]

    print("\n--- Starting AI vs AI Chess Game ---")
    print(f"Player 1 (White): {white_player.model_name} (Strategy: {white_strategy})")
    print(f"Player 2 (Black): {black_player.model_name} (Strategy: {black_strategy})")
    print("------------------------------------")

    # Game loop
    auto_moves_remaining = 0
    while not game.is_game_over():
        game.display_board()

        is_manual_move = False # Flag to skip AI move if user enters one

        # Wait for user input before proceeding with the move
        if auto_moves_remaining > 0:
            # If it's Black's turn, decrement after the full move is complete
            if game.get_board_state().turn == chess.WHITE:
                auto_moves_remaining -= 1
        else:
            turn_color = "White" if game.get_board_state().turn == chess.WHITE else "Black"
            user_input = input(f"Press Enter for AI move, 'q' to quit, 'm' for menu, a number for auto-play, or enter a move for {turn_color} (e.g. e2e4): ")
            if user_input.lower() == 'q':
                save_choice = input("Save game before quitting? (y/n): ").strip().lower()
                if save_choice == 'y':
                    # Close the logger to release the file handle
                    logging.shutdown()
                    try:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        new_filename = f"chess_game_{timestamp}.log"
                        os.rename('chess_game.log', new_filename)
                        print(f"Game saved as {new_filename}")
                    except FileNotFoundError:
                        print("Log file not found, could not save.")
                print("Exiting game.")
                break
            elif user_input.lower() == 'm':
                menu_choice = display_game_menu_and_get_choice()
                if menu_choice == 'l':
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
                            # We will load the board state from the chosen file.
                            # The current AI models and strategies will be replaced.
                            loaded_game = load_game_from_log(chosen_file)
                            if loaded_game:
                                game = loaded_game
                                # Copy the loaded game to be the active game log and set to append
                                logging.shutdown()
                                shutil.copy(chosen_file, 'chess_game.log')
                                logging.basicConfig(filename='chess_game.log', level=logging.INFO, 
                                                    format='%(asctime)s - %(message)s', filemode='a')
                                logging.getLogger("httpx").setLevel(logging.WARNING)

                                print(f"Successfully loaded game from {chosen_file}.")
                                auto_moves_remaining = 0 # Reset auto-play
                            else:
                                print("Could not load game from log file.")
                        else:
                            print("Invalid number.")
                    except ValueError:
                        print("Invalid input.")
                elif menu_choice == 'p':
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
                                auto_moves_remaining = 0 # Reset auto-play
                            else:
                                print("Failed to load position.")
                        else:
                            print("Invalid number.")
                    except (FileNotFoundError, json.JSONDecodeError, ValueError):
                        print("Could not load practice positions file or invalid input.")

                # If 'c' or after loading, just continue the loop to redisplay the board
                continue
            try:
                num_moves = int(user_input)
                # We subtract 1 because the current move is about to be played
                auto_moves_remaining = max(0, num_moves - 1)
            except ValueError:
                # Not a number, so it's either Enter or a move string
                if user_input == '':
                    # User pressed Enter, let AI play
                    pass
                else:
                    # Assume it's a manual move
                    move_uci = user_input.strip().lower()
                    if game.make_move(move_uci, author="User"):
                        is_manual_move = True # Signal that AI should not move
                    else:
                        print("Invalid or illegal move. Please try again.")
                        continue # Re-prompt user

        # Determine whose turn it is
        turn = game.get_board_state().turn
        strategy = game.strategies[turn]

        if turn == chess.WHITE:
            current_player = game.players[chess.WHITE]
            player_name = "Player 1 (White)"
        else:
            current_player = game.players[chess.BLACK]
            player_name = "Player 2 (Black)"

        # Only compute AI move if a manual move was not made
        if not is_manual_move:
            move_number = game.get_board_state().fullmove_number
            print(f"\n{BLUE}Move {move_number}:{ENDC} {player_name}'s turn ({current_player.model_name})...")
            if strategy and game.get_board_state().fullmove_number <= 3:
                print(f"Strategy: {strategy}")
            
            # AI computes and makes a move
            move = current_player.compute_move(game.get_board_state(), strategy_message=strategy)
            
            if move:
                game.make_move(move, author="AI")
            else:
                # This might happen if the AI fails to return a valid move
                print("AI failed to provide a move. Ending game.")
                break
        
    # Display the final board and result
    result = game.get_game_result()
    logging.info(f"Game Over. Result: {result}")
    print("\n--- Game Over ---")
    game.display_board()
    print(f"Result: {result}")
    print("Game history has been saved to chess_game.log")


if __name__ == "__main__":
    main()