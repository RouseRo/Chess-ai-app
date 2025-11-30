import chess
from src.chess_game import ChessGame

class GameService:
    def __init__(self):
        self.games = {}  # game_id -> ChessGame

    def create_game(self, white_player, black_player, fen=None):
        game = ChessGame(white_player, black_player)
        game.initialize_game(fen)
        game_id = str(id(game))
        self.games[game_id] = game
        return game_id

    def make_move(self, game_id, move_uci):
        game = self.games.get(game_id)
        if not game:
            return None, "Game not found"
        board = game.board
        try:
            move = chess.Move.from_uci(move_uci)
            if move in board.legal_moves:
                board.push(move)
                return board.fen(), "Move accepted"
            else:
                return board.fen(), "Illegal move"
        except Exception as e:
            return board.fen(), f"Error: {e}"

    def get_game_state(self, game_id):
        game = self.games.get(game_id)
        if not game:
            return None
        return {
            "fen": game.board.fen(),
            "is_over": game.is_over(),
            "result": game.board.result() if game.is_over() else None
        }