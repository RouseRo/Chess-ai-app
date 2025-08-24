import chess # pyright: ignore[reportMissingImports]
from game import Game
from ai_player import AIPlayer

def main():
    # Initialize the game and AI players with actual OpenRouter models.
    # You can choose any models from https://openrouter.ai/models
    # Using two different models to play against each other.
    ai_player1 = AIPlayer(model_name="openai/gpt-4o") # White
    ai_player2 = AIPlayer(model_name="deepseek/deepseek-chat-v3.1") # Black

    game = Game()
    board = chess.Board()

    print("--- Starting AI vs AI Chess Game ---")
    print(f"Player 1 (White): {ai_player1.model_name}")
    print(f"Player 2 (Black): {ai_player2.model_name}")
    print("------------------------------------")

    # Game loop
    while True:
        game.display_board()

        # Determine whose turn it is
        if game.get_board_state().turn == chess.WHITE:
            current_player = ai_player1
            player_name = "Player 1 (White)"
        else:
            current_player = ai_player2
            player_name = "Player 2 (Black)"

        print(f"\n{player_name}'s turn ({current_player.model_name})...")
        
        # AI computes and makes a move
        move = current_player.compute_move(game.get_board_state())
        
        if move:
            game.make_move(move)
        else:
            # This might happen if the AI fails to return a valid move
            print("AI failed to provide a move. Ending game.")
            break
        
        # Wait for user input before the next turn, unless the game is over
        if not game.is_game_over():
            # Display the board after the move
            game.display_board()
            input("Press Enter to continue...")

    # Display the final board and result
    print("\n--- Game Over ---")
    game.display_board()
    print(f"Result: {game.get_game_result()}")

if __name__ == "__main__":
    main()