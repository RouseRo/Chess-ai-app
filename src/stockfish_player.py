from stockfish import Stockfish

class StockfishPlayer:
    """A player class that uses the Stockfish chess engine to compute moves."""
    def __init__(self, path, parameters=None):
        """
        Initializes the Stockfish engine.
        :param path: Path to the Stockfish executable.
        :param parameters: A dictionary of UCI parameters for Stockfish.
        """
        try:
            self.stockfish = Stockfish(path=path, parameters=parameters or {})
            self.model_name = f"Stockfish (Skill: {self.stockfish.get_parameters()['Skill Level']})"
        except (FileNotFoundError, PermissionError) as e:
            raise RuntimeError(f"Failed to initialize Stockfish. Check the path in your config.json. Error: {e}")

    def compute_move(self, board, strategy_message=None):
        """
        Computes the best move for the current board state using Stockfish.
        The strategy_message is ignored as Stockfish uses its internal logic.
        """
        self.stockfish.set_fen_position(board.fen())
        best_move = self.stockfish.get_best_move()
        return best_move

    def ask_question(self, question, system_prompt):
        """Stockfish cannot answer questions."""
        return "The Stockfish player is a chess engine and cannot answer questions."