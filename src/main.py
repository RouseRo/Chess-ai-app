import chess # pyright: ignore[reportMissingImports]
from game import Game
from ai_player import AIPlayer

def main():
    # Initialize the game and AI players with actual OpenRouter models.
    # You can choose any models from https://openrouter.ai/models
    # Using two different models to play against each other.
    ai_player1 = AIPlayer(model_name="openai/gpt-4o") # White
    ai_player2 = AIPlayer(model_name="deepseek/deepseek-chat-v3.1") # Black

    game = Game(ai_player1, ai_player2, white_strategy="Play the Ruy Lopez.", black_strategy="Play the Sicilian Defense.")

    print("--- Starting AI vs AI Chess Game ---")
    print(f"Player 1 (White): {ai_player1.model_name} (Strategy: Ruy Lopez)")
    print(f"Player 2 (Black): {ai_player2.model_name} (Strategy: Sicilian Defense)")
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

        print(f"\n{player_name}'s turn ({current_player.model_name})...")
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
    print("\n--- Game Over ---")
    game.display_board()
    print(f"Result: {game.get_game_result()}")

if __name__ == "__main__":
    main()