import chess
from stockfish import Stockfish

class StockfishPlayer:
    """Represents a player using the Stockfish chess engine."""

    def __init__(self, path, parameters=None):
        """
        Initializes the Stockfish player.
        :param path: Path to the Stockfish executable.
        :param parameters: A dictionary of Stockfish UCI parameters.
        """
        self.stockfish = Stockfish(path=path, parameters=parameters or {})

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