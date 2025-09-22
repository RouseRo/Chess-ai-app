import chess
from stockfish import Stockfish

class StockfishPlayer:
    """Represents a player using the Stockfish chess engine."""

    def __init__(self, stockfish_path, parameters=None, name="Stockfish"):
        """
        Initializes the Stockfish player.
        :param stockfish_path: Path to the Stockfish executable.
        :param parameters: A dictionary of Stockfish UCI parameters.
        :param name: The name of the player.
        """
        self.stockfish_path = stockfish_path
        self.parameters = parameters or {}
        print(f"DEBUG: Attempting to launch Stockfish at: {self.stockfish_path}")  # Add this before the Stockfish() call
        self.stockfish = Stockfish(path=self.stockfish_path, parameters=self.parameters)
        self.name = name

        skill_level = self.stockfish.get_parameters().get("Skill Level", "N/A")
        self.model_name = f"Stockfish (Skill: {skill_level})"

    def compute_move(self, board, **kwargs):
        """
        Computes the best move using the Stockfish engine.
        Ignores any extra keyword arguments like 'strategy'.
        """
        self.stockfish.set_fen_position(board.fen())
        best_move_uci = self.stockfish.get_best_move()
        if best_move_uci:
            return chess.Move.from_uci(best_move_uci)
        return None

    def ask_question(self, question, system_prompt):
        """Stockfish cannot answer questions."""
        return "The Stockfish player is a chess engine and cannot answer questions."
    
    def get_move(self, game):
        """Get the best move from Stockfish for the current board position."""
        import chess.engine
        import chess

        board = game.board
        with chess.engine.SimpleEngine.popen_uci(self.stockfish_path) as engine:
            result = engine.play(board, chess.engine.Limit(time=0.1))  # Adjust time limit as needed
            move = result.move
            if move:
                return move.uci()
            else:
                return None

    def __str__(self):
        return self.name