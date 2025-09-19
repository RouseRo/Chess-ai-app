import chess
import logging
import inspect
import sys

from src.human_player import HumanPlayer
from src.game_log_manager import GameLogManager
from src.ui_manager import UIManager
from src.colors import WHITE, CYAN, YELLOW, GREEN, MAGENTA, RED, BLUE, ENDC
from src.constants import GameLoopAction

logger = logging.getLogger(__name__)

class GameManager:
    def __init__(self, ui, player_factory, ai_models, stockfish_configs, file_manager, game_log_manager):
        self.ui = ui
        self.player_factory = player_factory
        self.ai_models = ai_models
        self.stockfish_configs = stockfish_configs
        self.file_manager = file_manager
        self.game_log_manager = game_log_manager

    def setup_new_game(self, white_openings, black_defenses, fen=None):
        logger.info("Setting up new game")
        logger.debug(f"White openings: {white_openings}, Black defenses: {black_defenses}, FEN: {fen}")
        """Create and return a new Game from UI choices. Returns None if the user cancels."""
        choices = self.ui.display_setup_menu_and_get_choices(
            white_openings,
            black_defenses,
            self.ai_models,
            self.stockfish_configs
        )
        if not choices:
            return None, None, None

        white_opening_key, black_defense_key, white_key, black_key = choices

        white_player = self.player_factory.create_player(white_key, color_label="White")
        black_player = self.player_factory.create_player(black_key, color_label="Black")

        white_opening_obj = white_openings.get(white_opening_key)
        black_defense_obj = black_defenses.get(black_defense_key)

        game = ChessGame(
            white_player, black_player,
            white_player_key=white_key,
            black_player_key=black_key
        )

        game.white_strategy = white_opening_obj
        game.black_strategy = black_defense_obj

        game.initialize_game(fen)  # Pass the FEN if provided (for practice positions)
        return game, white_opening_obj, black_defense_obj

    def play_turn(self, game):
        self.ui.display_board(game.board)
        board = game.board
        print(f"DEBUG: Board fen at start of turn: {board.fen()}")
        current_player = game.get_current_player() if hasattr(game, "get_current_player") else None
        turn_color = "White" if board.turn else "Black"
        move_number = board.fullmove_number

        prompt = (
            f"{WHITE}Move {move_number}{ENDC} "
            f"{CYAN}({getattr(current_player, 'model_name', str(current_player))}{ENDC} "
            f"{YELLOW}as {turn_color}{ENDC}{CYAN}){ENDC}:\n"
            f"  Enter your move in UCI format (e.g., e2e4, h1c1)\n"
            f"  {GREEN}'ENTER'{ENDC} to let player move, "
            f"{WHITE}a{ENDC}{YELLOW} #{ENDC} for auto-play, "
            f"{GREEN}'q'{ENDC} to quit, or "
            f"{MAGENTA}'m'{ENDC} for menu:\n"
        )

        print(prompt, flush=True)
        move = input().strip()

        if move == 'q':
            quit_choice = self.ui.get_human_quit_choice()
            if quit_choice == 's':
                self.file_manager.save_game_log()
                self.ui.display_message("Game saved. Exiting.")
                return game, GameLoopAction.QUIT_APPLICATION
            elif quit_choice == 'q':
                self.ui.display_message("Exiting without saving.")
                return game, GameLoopAction.QUIT_APPLICATION
            else:
                self.ui.display_message("Returning to game.")
                return game, GameLoopAction.CONTINUE
        elif move == 'm':
            return game, GameLoopAction.IN_GAME_MENU
        elif move == '':
            # Let the player (AI or human) make a move automatically
            try:
                move = current_player.get_move(game)
                if move:
                    chess_move = chess.Move.from_uci(move)
                    if chess_move in board.legal_moves:
                        move_san = board.san(chess_move)  # Generate SAN before pushing
                        board.push(chess_move)
                        self.game_log_manager.log_move(board.fullmove_number, getattr(current_player, 'name', str(current_player)), move_san, move, board.fen())
            except Exception as e:
                self.ui.display_message(f"{RED}AI move error: {e}{ENDC}")
        else:
            try:
                chess_move = chess.Move.from_uci(move)
                if chess_move in board.legal_moves:
                    move_san = board.san(chess_move)  # Generate SAN before pushing
                    board.push(chess_move)
                    self.game_log_manager.log_move(board.fullmove_number, getattr(current_player, 'name', str(current_player)), move_san, move, board.fen())
                else:
                    self.ui.display_message(f"{RED}Illegal move: {move}{ENDC}")
            except Exception as e:
                self.ui.display_message(f"{RED}Invalid move: {e}{ENDC}")

        print(f"DEBUG: Board fen at end of turn: {board.fen()}")
        return game, GameLoopAction.CONTINUE

    def determine_game_result(self, game):
        """Return canonical result string ('1-0', '0-1', '1/2-1/2') based on board state."""
        board = game.board
        if board.is_checkmate():
            winner = not board.turn
            return "1-0" if winner == chess.WHITE else "0-1"
        if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_threefold_repetition() or board.can_claim_fifty_moves():
            return "1/2-1/2"
        try:
            return board.result()
        except Exception:
            return "1/2-1/2"

    def run(self, game=None):
        """Main game loop, managing turns and game state."""
        print(f"DEBUG: Game is None: {game is None}")
        if game is None:
            print("DEBUG: Calling setup_new_game")
            game, _, _ = self.setup_new_game()
            if game is None:
                return  # User canceled game setup
        else:
            print(f"DEBUG: Game fen: {game.board.fen()}")

        while True:
            game, action = self.play_turn(game)
            if action == GameLoopAction.QUIT_APPLICATION:
                break
            elif action == GameLoopAction.IN_GAME_MENU:
                self.ui.display_message("In-game menu is not yet implemented.")
            elif action == GameLoopAction.CONTINUE:
                result = self.determine_game_result(game)
                if result:
                    self.ui.display_message(f"Game over! Result: {result}")
                    game = None
                    break  # Exit the loop after game over
            else:
                self.ui.display_message(f"Unknown action: {action}")

class ChessGame:
    def __init__(self, white_player, black_player, white_player_key=None, black_player_key=None):
        self.white_player = white_player
        self.black_player = black_player
        self.white_player_key = white_player_key
        self.black_player_key = black_player_key
        self.board = chess.Board()
        self.white_strategy = None
        self.black_strategy = None

    def initialize_game(self, fen=None):
        print(f"DEBUG: Initializing game with fen: {fen}")
        if fen:
            print(f"DEBUG: Setting fen: {fen}")
            self.board.set_fen(fen)
        else:
            print("DEBUG: Resetting board")
            self.board.reset()

    def get_current_player(self):
        return self.white_player if self.board.turn == chess.WHITE else self.black_player

    def is_over(self):
        return self.board.is_game_over()

    def set_board_from_fen(self, fen):
        """Set the board position from a FEN string."""
        self.board.set_fen(fen)

    @property
    def players(self):
        import chess
        return {
            chess.WHITE: self.white_player,
            chess.BLACK: self.black_player
        }
