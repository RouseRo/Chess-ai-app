import chess

class ChessGame:
    def __init__(self, white_player, black_player, white_player_key=None, black_player_key=None, white_strategy=None, black_strategy=None):
        self.white_player = white_player
        self.black_player = black_player
        self.white_player_key = white_player_key
        self.black_player_key = black_player_key
        self.white_strategy = white_strategy
        self.black_strategy = black_strategy
        self.board = chess.Board()

    def initialize_game(self, fen=None):
        if fen:
            self.board.set_fen(fen)
        else:
            self.board.reset()

    def get_current_player(self):
        return self.white_player if self.board.turn == chess.WHITE else self.black_player

    def is_over(self):
        return self.board.is_game_over()

    def set_board_from_fen(self, fen):
        self.board.set_fen(fen)

    @property
    def players(self):
        return {
            chess.WHITE: self.white_player,
            chess.BLACK: self.black_player
        }