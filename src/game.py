import chess
import logging
from datetime import datetime

# ANSI escape codes for colors
BLUE = '\033[94m'
RED = '\033[91m'
GREEN = '\033[92m'
ENDC = '\033[0m'

class Game:
    def __init__(self, player1, player2, white_strategy=None, black_strategy=None):
        """Initializes the chessboard and players."""
        self.board = chess.Board()
        self.players = {chess.WHITE: player1, chess.BLACK: player2}
        self.strategies = {chess.WHITE: white_strategy, chess.BLACK: black_strategy}
        
        # Log initial setup
        initial_fen = self.board.fen()
        logging.info("New Game Started")
        # This part of logging might need adjustment if player keys are needed here
        logging.info(f"White: {player1.model_name}")
        logging.info(f"Black: {player2.model_name}")
        logging.info(f"White Strategy: {white_strategy or 'None'}")
        logging.info(f"Black Strategy: {black_strategy or 'None'}")
        logging.info(f"Initial FEN: {initial_fen}")

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
        """Gets a move from the current player and applies it to the board."""
        current_player = self.players[self.board.turn]
        strategy = self.strategies[self.board.turn]
        
        move_uci = current_player.compute_move(self.board, strategy_message=strategy)
        
        if move_uci:
            self.make_move(move_uci, author=current_player.model_name)
        else:
            logging.error(f"Player {current_player.model_name} failed to compute a move.")

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
                logging.info(f"Move: {uci_move}, Author: {author}, FEN: {self.board.fen()}")
                return True
            else:
                return False
        except ValueError:
            return False

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
        if self.board.is_checkmate():
            winner = "Black" if self.board.turn == chess.WHITE else "White"
            return f"\a{GREEN}Checkmate! {winner} wins.{ENDC}"
        if self.board.is_stalemate():
            return "Stalemate! The game is a draw."
        if self.board.is_insufficient_material():
            return "Insufficient material! The game is a draw."
        if self.board.is_seventyfive_moves():
            return "75-move rule! The game is a draw."
        if self.board.is_fivefold_repetition():
            return "Fivefold repetition! The game is a draw."
        return "Game over."

    def swap_player_model(self, color, new_player):
        """Swaps the AI player for the given color."""
        self.players[color] = new_player
        self.strategies[color] = "Play for a direct checkmate." # Reset strategy
        logging.info(f"Player model for {'White' if color == chess.WHITE else 'Black'} swapped to {new_player.model_name}")