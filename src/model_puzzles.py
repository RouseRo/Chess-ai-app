import chess
from src.game import Game
from src.stockfish_player import StockfishPlayer
from src.ai_player import AIPlayer

class ModelPuzzles:
    """
    A class to manage the process of testing chess models against predefined puzzles.
    """
    def __init__(self, player_factory, file_manager, ui):
        self.player_factory = player_factory
        self.file_manager = file_manager
        self.ui = ui

    def solve_puzzle(self, puzzle, model_key, puzzle_timeout=10):
        """
        Attempts to solve a given puzzle with a player created from the model_key.
        Returns a dict with status, reason, and attempted move (if any).
        """
        try:
            game = self._create_game_for_puzzle(puzzle)
            player = self._get_player_for_puzzle(model_key)
            if not player:
                return {"status": "ERROR", "reason": f"Could not create player for key: {model_key}"}

            result = self._evaluate_puzzle_move(game, player, puzzle, puzzle_timeout)
            return result
        except Exception as e:
            return {"status": "ERROR", "reason": f"Exception: {e}"}

    def _create_game_for_puzzle(self, puzzle):
        """Creates a Game object from a puzzle FEN."""
        dummy = self.player_factory.create_player('hu', name_override="Defender")
        game = Game(dummy, dummy)
        game.set_board_from_fen(puzzle['fen'])
        return game

    def _get_player_for_puzzle(self, model_key):
        return self.player_factory.create_player(model_key)

    def _invoke_compute_move(self, player, board, timeout):
        """
        Calls player's compute_move using whatever signature it supports.
        Tries (timeout=), then (think_time=), then no keyword.
        Ensures we return a chess.Move (first element if tuple/list returned).
        """
        # Prefer Stockfish think_time if it's a StockfishPlayer
        if isinstance(player, StockfishPlayer):
            try:
                mv = player.compute_move(board, think_time=timeout)
            except TypeError:
                mv = player.compute_move(board)
        else:
            # Try timeout=
            tried = False
            try:
                mv = player.compute_move(board, timeout=timeout)
                tried = True
            except TypeError:
                pass
            if not tried:
                # Try think_time=
                try:
                    mv = player.compute_move(board, think_time=timeout)
                except TypeError:
                    # Last resort: no keyword
                    mv = player.compute_move(board)

        # Some implementations may return (move, score, pv) or similar
        if isinstance(mv, (list, tuple)) and mv:
            first = mv[0]
            if isinstance(first, chess.Move):
                return first
        return mv

    def _normalize_solution_set(self, solutions):
        """
        Normalize solution moves:
          - Lowercase
          - Remove trailing promotion piece if absent in one side (treat a7a8 and a7a8q as same if puzzle list uses either)
        """
        norm = set()
        for s in solutions:
            u = s.strip().lower()
            if len(u) == 5 and u[-1] in "qrbn":
                norm.add(u)           # full promotion
                norm.add(u[:4])       # base move without promotion
            else:
                norm.add(u)
        return norm

    def _evaluate_puzzle_move(self, game, player, puzzle, timeout):
        """
        Compute a move and compare to puzzle solution.
        Handles different player interfaces and avoids passing unsupported keywords
        (e.g., strategy_message) to AIPlayer / StockfishPlayer.
        """
        try:
            move = self._invoke_compute_move(player, game.board, timeout)
            if move is None or not isinstance(move, chess.Move):
                return {
                    "status": "FAIL",
                    "reason": "Player returned no valid move",
                    "attempted": None
                }

            attempted_uci = move.uci().lower()
            solution_set = self._normalize_solution_set(puzzle.get('solution', []))

            if attempted_uci in solution_set:
                return {
                    "status": "PASS",
                    "reason": f"Correct move: {attempted_uci}",
                    "attempted": attempted_uci
                }
            else:
                return {
                    "status": "FAIL",
                    "reason": f"Incorrect move: {attempted_uci}. Expected one of: {sorted(solution_set)}",
                    "attempted": attempted_uci
                }

        except TypeError as te:
            # Typical for unexpected kwargs in underlying player
            return {
                "status": "ERROR",
                "reason": f"TypeError during move computation: {te}",
                "attempted": None
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "reason": f"Exception during move computation: {e}",
                "attempted": None
            }