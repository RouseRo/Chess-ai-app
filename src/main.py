import chess
import logging
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


def main():
    # Set up logging
    logging.basicConfig(filename='chess_game.log', level=logging.INFO, 
                        format='%(asctime)s - %(message)s', filemode='w')

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

    game = Game(ai_player1, ai_player2, white_strategy=white_strategy, black_strategy=black_strategy)

    start_message = f"New Game Started. White: {ai_player1.model_name} (Strategy: {white_strategy}) | Black: {ai_player2.model_name} (Strategy: {black_strategy})"
    logging.info(start_message)
    print("\n--- Starting AI vs AI Chess Game ---")
    print(f"Player 1 (White): {ai_player1.model_name} (Strategy: {white_strategy})")
    print(f"Player 2 (Black): {ai_player2.model_name} (Strategy: {black_strategy})")
    print("------------------------------------")

    # Game loop
    auto_moves_remaining = 0
    while not game.is_game_over():
        game.display_board()

        # Determine whose turn it is
        turn = game.get_board_state().turn
        strategy = game.strategies[turn]

        if turn == chess.WHITE:
            current_player = ai_player1
            player_name = "Player 1 (White)"
        else:
            current_player = ai_player2
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
                user_input = input("Press Enter to continue, 'q' to quit, or a number of moves to auto-play: ")
                if user_input.lower() == 'q':
                    print("Exiting game.")
                    break
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