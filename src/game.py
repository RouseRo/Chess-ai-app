import chess
import logging
from datetime import datetime
import re

# ANSI escape codes for colors
BLUE = '\033[94m'
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
ENDC = '\033[0m'

class Game:
    """Represents a single game of chess, including board state and players."""

    def __init__(self, player1, player2, white_strategy=None, black_strategy=None, white_player_key=None, black_player_key=None):
        self.players = {chess.WHITE: player1, chess.BLACK: player2}
        self.board = chess.Board()
        self.white_strategy = white_strategy
        self.black_strategy = black_strategy
        self.strategies = {
            chess.WHITE: white_strategy,
            chess.BLACK: black_strategy
        }
        self.white_player_key = white_player_key
        self.black_player_key = black_player_key

    def initialize_game(self):
        """Logs the initial game state and player info."""
        logging.info("New Game Started")
        logging.info(f"White: {self.players[chess.WHITE].model_name}")
        logging.info(f"Black: {self.players[chess.BLACK].model_name}")
        logging.info(f"White Player Key: {self.white_player_key}")
        logging.info(f"Black Player Key: {self.black_player_key}")
        
        white_strat_msg = self.white_strategy if self.white_strategy else "No Classic Chess Opening"
        black_strat_msg = self.black_strategy if self.black_strategy else "No Classic Chess Opening"
        logging.info(f"White Strategy: {white_strat_msg}")
        logging.info(f"Black Strategy: {black_strat_msg}")
        
        logging.info(f"Initial FEN: {self.board.fen()}")

    def set_opening_strategy(self, color, strategy_message):
        """Sets an opening strategy message for the given player color."""
        if color in self.strategies:
            self.strategies[color] = strategy_message
            print(f"Opening strategy for {'White' if color == chess.WHITE else 'Black'} set to: {strategy_message}")
        else:
            print("Invalid color specified for strategy.")

    def display_board(self):
        """Prints a text representation of the board, highlighting the last move."""
        last_move = None
        if self.board.move_stack:
            last_move = self.board.move_stack[-1]

        print()
        print("  a b c d e f g h")
        print(" -----------------")
        for rank in range(7, -1, -1):
            line = f"{rank + 1}|"
            for file in range(8):
                square = chess.square(file, rank)
                piece = self.board.piece_at(square)
                
                symbol = "." if piece is None else piece.symbol()
                
                # Highlight the 'to' and 'from' squares of the last move
                if last_move and (square == last_move.to_square or square == last_move.from_square):
                    line += f"{BLUE}{symbol}{ENDC} "
                else:
                    line += f"{symbol} "
            print(line + f"|{rank + 1}")
        print(" -----------------")
        print("  a b c d e f g h")

    def play_turn(self):
        """
        Computes and makes a move for the current player.
        Logs the move and its author.
        """
        player = self.get_current_player()
        author = player.model_name
        
        # Prepare arguments for the AI model
        kwargs = {}
        if self.board.turn == chess.WHITE and self.white_strategy:
            kwargs['strategy'] = self.white_strategy
        elif self.board.turn == chess.BLACK and self.black_strategy:
            kwargs['strategy'] = self.black_strategy

        move = player.compute_move(self.board, **kwargs)
        
        if move is None:
            # This can happen if the AI fails or if it's a human player's turn
            # in a context where manual input is expected.
            return

        self.board.push(move)
        self._log_move(move, author)

    def make_move(self, uci_move, author="System"):
        """
        Attempts to make a move on the board using UCI notation.
        Logs the move with its author ('AI' or 'User').
        Returns True if the move is legal, False otherwise.
        """
        try:
            move = chess.Move.from_uci(uci_move)
            if move in self.board.legal_moves:
                self.board.push(move)
                self._log_move(move, author)
                return True
            else:
                return False
        except ValueError:
            return False

    def make_manual_move(self, uci_move):
        """
        Makes a move on the board from a user-provided UCI string.
        Logs the move with the player's name as the author.
        Raises ValueError if the move is invalid.
        """
        try:
            move = chess.Move.from_uci(uci_move)
            if move in self.board.legal_moves:
                author = self.get_current_player().model_name
                self.board.push(move)
                self._log_move(move, author)
            else:
                raise ValueError("Illegal move.")
        except (ValueError, TypeError):
            raise ValueError("Invalid move format. Use UCI notation (e.g., e2e4).")

    def _log_move(self, move, author):
        """Logs the move details to the logging file."""
        turn_number = self.board.fullmove_number
        color = "White" if self.board.turn != chess.WHITE else "Black" # Color of player who just moved
        logging.info(f"Turn {turn_number} ({color}): Move: {move.uci()} by {author}, FEN: {self.board.fen()}")

    def get_current_player(self):
        """Returns the player object for the current turn."""
        return self.players[self.board.turn]

    def load_last_position_from_log(self, filename='chess_game.log'):
        """
        Finds the last FEN string in the specified log file and loads it into the board.
        Returns True on success, False on failure.
        """
        last_fen = None
        try:
            with open(filename, 'r') as f:
                for line in f:
                    if "FEN:" in line:
                        # Extract the FEN string from the line
                        match = re.search(r'FEN: (.*)', line)
                        if match:
                            last_fen = match.group(1).strip()
            
            if last_fen:
                self.board.set_fen(last_fen)
                return True
        except (FileNotFoundError, IndexError):
            return False
        return False

    def set_board_from_fen(self, fen_string):
        """Sets the board state from a FEN string."""
        try:
            self.board.set_fen(fen_string)
            # Clear the move stack to reflect the new position
            self.board.move_stack.clear()
            logging.info(f"Board position loaded from FEN: {fen_string}")
            return True
        except ValueError:
            print("Invalid FEN string provided.")
            return False

    def is_game_over(self):
        """Checks if the game is over."""
        return self.board.is_game_over(claim_draw=True)

    def get_game_result(self):
        """Returns the result of the game as a string."""
        num_moves = len(self.board.move_stack)
        moves_str = f" ({num_moves} moves)"

        if self.board.is_checkmate():
            winner = "Black" if self.board.turn == chess.WHITE else "White"
            return f"\a{GREEN}Checkmate! {winner} wins.{moves_str}{ENDC}"
        if self.board.is_stalemate():
            return f"{YELLOW}Stalemate! The game is a draw.{moves_str}{ENDC}"
        if self.board.is_insufficient_material():
            return f"{YELLOW}Insufficient material! The game is a draw.{moves_str}{ENDC}"
        if self.board.is_seventyfive_moves():
            return f"{YELLOW}75-move rule! The game is a draw.{moves_str}{ENDC}"
        if self.board.is_fivefold_repetition():
            return f"{YELLOW}Fivefold repetition! The game is a draw.{moves_str}{ENDC}"
        return f"Game over.{moves_str}"

    def swap_player_model(self, color, new_player):
        """Swaps the AI player for the given color."""
        self.players[color] = new_player
        self.strategies[color] = "Play for a direct checkmate." # Reset strategy
        logging.info(f"Player model for {'White' if color == chess.WHITE else 'Black'} swapped to {new_player.model_name}")