import chess
import logging
import os
import re
from datetime import datetime
import glob
import shutil
from game import Game, BLUE, ENDC
from ai_player import AIPlayer

def display_menu_and_get_choice(white_openings, black_defenses):
    """Displays strategy options and gets the user's choice."""
    print("--- Choose Opening Strategies ---")
    print("\nWhite Openings:")
    for key, value in white_openings.items():
        print(f"  {key}: {value.replace('Play the ', '')}")

    print("\nBlack Defenses:")
    for key, value in black_defenses.items():
        print(f"  {key}: {value.replace('Play the ', '')}")

    while True:
        choice = input("\nEnter your choice (e.g., '1a', '3c'): ").strip().lower()
        if len(choice) == 2 and choice[0] in white_openings and choice[1] in black_defenses:
            return choice[0], choice[1]
        else:
            print("Invalid input. Please enter a valid number for White and a valid letter for Black (e.g., '1a').")

def display_model_menu_and_get_choice(ai_models):
    """Displays AI model options and gets the user's choice."""
    print("\n--- Choose AI Models ---")
    for key, value in ai_models.items():
        print(f"  {key}: {value}")

    while True:
        choice = input("\nEnter your choice for White and Black models (e.g., 'm1m5'): ").strip().lower()
        if len(choice) == 4 and choice.startswith('m') and choice[2] == 'm':
            white_model_key = choice[:2]
            black_model_key = choice[2:]
            if white_model_key in ai_models and black_model_key in ai_models:
                return white_model_key, black_model_key
        
        print("Invalid input. Please enter a valid choice for both models (e.g., 'm1m5').")

def display_game_menu_and_get_choice():
    """Displays the in-game menu and gets the user's choice."""
    print("\n--- Game Menu ---")
    print("  l: Load last position from log")
    print("  c: Cancel and continue game")
    while True:
        choice = input("Enter your choice: ").strip().lower()
        if choice in ['l', 'c']:
            return choice
        else:
            print("Invalid choice. Please enter 'l' or 'c'.")


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
    """Set up a new game with user-defined or default settings."""
    # Get user's choice for strategies
    white_key, black_key = display_menu_and_get_choice(white_openings, black_defenses)

    # Get user's choice for AI models
    white_model_key, black_model_key = display_model_menu_and_get_choice(ai_models)

    # Initialize the game and AI players with actual OpenRouter models.
    # You can choose any models from https://openrouter.ai/models
    # Using two different models to play against each other.
    white_model_name = ai_models[white_model_key]
    black_model_name = ai_models[black_model_key]
    ai_player1 = AIPlayer(model_name=white_model_name) # White
    ai_player2 = AIPlayer(model_name=black_model_name) # Black

    # Set strategies from the dictionaries based on user input
    white_strategy = white_openings[white_key]
    black_strategy = black_defenses[black_key]

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
        load_choice = input("Welcome back! I found some saved games. Would you like to load one? (y/n): ").strip().lower()
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

        # Determine whose turn it is
        turn = game.get_board_state().turn
        strategy = game.strategies[turn]

        if turn == chess.WHITE:
            current_player = game.players[chess.WHITE]
            player_name = "Player 1 (White)"
        else:
            current_player = game.players[chess.BLACK]
            player_name = "Player 2 (Black)"

        move_number = game.get_board_state().fullmove_number
        print(f"\n{BLUE}Move {move_number}:{ENDC} {player_name}'s turn ({current_player.model_name})...")
        if strategy and game.get_board_state().fullmove_number <= 3:
            print(f"Strategy: {strategy}")
        
        # AI computes and makes a move
        move = current_player.compute_move(game.get_board_state(), strategy_message=strategy)
        
        if move:
            game.make_move(move)
        else:
            # This might happen if the AI fails to return a valid move
            print("AI failed to provide a move. Ending game.")
            break
        
        # Wait for user input before the next turn, unless the game is over
        if not game.is_game_over():
            if auto_moves_remaining > 0:
                # If it's Black's turn, decrement after the full move is complete
                if game.get_board_state().turn == chess.WHITE:
                    auto_moves_remaining -= 1
            else:
                # Display the board after the move
                game.display_board()
                user_input = input("Press Enter to continue, 'q' to quit, 'm' for menu, or a number of moves to auto-play: ")
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

                    # If 'c', just continue the loop and prompt again
                    continue
                try:
                    num_moves = int(user_input)
                    # We subtract 1 because the current move has just completed a turn
                    auto_moves_remaining = max(0, num_moves - 1)
                except ValueError:
                    # User just pressed Enter
                    auto_moves_remaining = 0


    # Display the final board and result
    result = game.get_game_result()
    logging.info(f"Game Over. Result: {result}")
    print("\n--- Game Over ---")
    game.display_board()
    print(f"Result: {result}")
    print("Game history has been saved to chess_game.log")

if __name__ == "__main__":
    main()