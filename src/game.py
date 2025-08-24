import chess

class Game:
    def __init__(self):
        """Initializes the chessboard using the python-chess library."""
        self.board = chess.Board()

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