import chess
from src.game import Game, GameLoopAction, RED, ENDC
from src.human_player import HumanPlayer
import logging  # Import logging module
import inspect
import sys

class GameManager:
    def __init__(self, ui, player_factory, ai_models, stockfish_configs):
        self.ui = ui
        self.player_factory = player_factory
        self.ai_models = ai_models
        self.stockfish_configs = stockfish_configs

    def setup_new_game(self, white_openings, black_defenses):
        """Create and return a new Game from UI choices. Returns None if the user cancels."""
        choices = self.ui.display_setup_menu_and_get_choices(
            white_openings,
            black_defenses,
            self.ai_models,
            self.stockfish_configs
        )
        if not choices:
            return None

        white_opening, black_defense, white_key, black_key = choices

        white_player = self.player_factory.create_player(white_key, color_label="White")
        black_player = self.player_factory.create_player(black_key, color_label="Black")

        game = Game(white_player, black_player, white_player_key=white_key, black_player_key=black_key)
        try:
            if white_opening:
                game.set_opening(white_opening)
            if black_defense:
                game.set_defense(black_defense)
        except Exception:
            pass

        game.initialize_game()
        return game

    def play_turn(self, game):
        """Plays a single turn of the game, returning the game object and an action."""
        self.ui.display_board(game.board)
        current_player = game.get_current_player()

        try:
            if isinstance(current_player, HumanPlayer):
                turn_color = "White" if game.board.turn else "Black"
                move_number = game.board.fullmove_number
                prompt = f"Move {move_number} ({current_player.model_name} as {turn_color}): Enter your move (e.g. e2e4), 'q' to quit, or 'm' for menu: "
                move = self.ui.get_user_input(prompt)
                
                if move == 'q':
                    quit_choice = self.ui.get_human_quit_choice()
                    if quit_choice == 'r':
                        game.resign_current_player()
                        self.ui.display_game_over_message(game)
                        return game, GameLoopAction.RETURN_TO_MENU
                    elif quit_choice == 's':
                        game.save_game()
                        self.ui.display_message("Game saved. Exiting to main menu.")
                        return game, GameLoopAction.RETURN_TO_MENU
                    elif quit_choice == 'q':
                        self.ui.display_message("Exiting game without saving.")
                        return game, GameLoopAction.RETURN_TO_MENU
                    elif quit_choice == 'c':
                        # Cancel quit, return to game
                        return game, GameLoopAction.CONTINUE
                elif move == 'm':
                    return game, GameLoopAction.IN_GAME_MENU
                else:
                    game.make_manual_move(move)
            else:
                self.ui.display_turn_message(game)
                game.play_turn()
        except ValueError as e:
            self.ui.display_message(f"{RED}Invalid move: {e}{ENDC}")
        except Exception as e:
            self.ui.display_message(f"{RED}Unexpected error: {e}{ENDC}")
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

    def run(self):
        """Main game loop, managing turns and game state."""
        game = None

        while True:
            if game is None:
                game = self.setup_new_game()
                if game is None:
                    break  # User canceled game setup

            game, action = self.play_turn(game)  # <-- Unpack both values!
            if action == GameLoopAction.QUIT_APPLICATION:
                break  # Exit the loop and quit the application
            elif action == GameLoopAction.IN_GAME_MENU:
                self.ui.display_message("In-game menu is not yet implemented.")
            elif action == GameLoopAction.CONTINUE:
                result = self.determine_game_result(game)
                if result:
                    self.ui.display_message(f"Game over! Result: {result}")
                    game = None  # Reset game after it ends
            else:
                self.ui.display_message(f"Unknown action: {action}")
