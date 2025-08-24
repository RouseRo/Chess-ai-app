import chess

class Game:
    def __init__(self, white_player, black_player, white_strategy=None, black_strategy=None):
        """Initializes the chessboard and players."""
        self.board = chess.Board()
        self.players = {chess.WHITE: white_player, chess.BLACK: black_player}
        self.strategies = {chess.WHITE: white_strategy, chess.BLACK: black_strategy}

    def set_opening_strategy(self, color, strategy_message):
        """Sets an opening strategy message for the given player color."""
        if color in self.strategies:
            self.strategies[color] = strategy_message
            print(f"Opening strategy for {'White' if color == chess.WHITE else 'Black'} set to: {strategy_message}")
        else:
            print("Invalid color specified for strategy.")

    def display_board(self):
        """Prints a simple text representation of the board."""
        print("\n" + str(self.board))
        print("-----------------")

    def make_move(self, uci_move):
        """
        Makes a move on the board using UCI notation.
        """
        try:
            move = chess.Move.from_uci(uci_move)
            if move in self.board.legal_moves:
                self.board.push(move)
            else:
                print(f"Warning: Attempted illegal move {uci_move}")
        except ValueError:
            print(f"Error: Invalid move format: {uci_move}")

    def is_game_over(self):
        """Checks if the game is over (checkmate, stalemate, etc.)."""
        return self.board.is_game_over()

    def get_board_state(self):
        """Returns the current board object."""
        return self.board

    def get_game_result(self):
        """Returns the result of the game."""
        return self.board.result()

    def play(self):
        """
        Starts and manages the chess game loop.
        """
        while not self.is_game_over():
            self.display_board()
            
            turn = self.board.turn
            current_player = self.players[turn]
            player_name = f"Player ({'White' if turn == chess.WHITE else 'Black'})"
            
            print(f"\n{player_name}'s turn ({current_player.model_name})...")

            # Pass strategy to AI player, e.g., for the first 3 moves
            strategy = None
            if self.board.fullmove_number <= 3:
                strategy = self.strategies[turn]

            move = current_player.compute_move(self.get_board_state(), strategy_message=strategy)
            
            if move:
                self.make_move(move)
            else:
                print("AI failed to provide a move. Ending game.")
                break
            
            if not self.is_game_over():
                input("Press Enter to continue...")

        print("\n--- Game Over ---")
        self.display_board()
        print(f"Result: {self.get_game_result()}")