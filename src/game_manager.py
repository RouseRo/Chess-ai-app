import chess
from src.game import Game, GameLoopAction, RED, ENDC
from src.human_player import HumanPlayer
import logging  # Import logging module
import inspect
import sys
from src.game import WHITE, CYAN, YELLOW, GREEN, MAGENTA, ENDC

class GameManager:
    def __init__(self, ui, player_factory, ai_models, stockfish_configs, file_manager):
        self.ui = ui
        self.player_factory = player_factory
        self.ai_models = ai_models
        self.stockfish_configs = stockfish_configs
        self.file_manager = file_manager  # <-- Add this line

    def setup_new_game(self, white_openings, black_defenses):
        """Create and return a new Game from UI choices. Returns None if the user cancels."""
        # Only call the UI to get all choices, including opening/defense as a single input
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

        # Map keys to string values (since your dict maps keys to strings)
        white_opening_obj = white_openings.get(white_opening_key)
        black_defense_obj = black_defenses.get(black_defense_key)

        game = Game(
            white_player, black_player,
            white_player_key=white_key,
            black_player_key=black_key
        )

        # Set the strategies on the game object
        game.white_strategy = white_opening_obj
        game.black_strategy = black_defense_obj

        game.initialize_game()
        # --- Return the actual objects, not the keys ---
        return game, white_opening_obj, black_defense_obj

    def play_turn(self, game):
        self.ui.display_board(game.board)
        current_player = game.get_current_player()

        turn_color = "White" if game.board.turn else "Black"
        move_number = game.board.fullmove_number
        prompt = (
            f"{WHITE}Move {move_number}{ENDC} "
            f"{CYAN}({getattr(current_player, 'model_name', str(current_player))}{ENDC} "
            f"{YELLOW}as {turn_color}{ENDC}{CYAN}){ENDC}: "
            f"{GREEN}'ENTER'{ENDC} to let player move, "
            f"{WHITE}a{ENDC}{YELLOW} #{ENDC} for auto-play, "
            f"{GREEN}'q'{ENDC} to quit, or "
            f"{MAGENTA}'m'{ENDC} for menu: "
        )

        if hasattr(self, "observer_auto_moves") and self.observer_auto_moves > 0:
            self.observer_auto_moves -= 1
            move = ""
        else:
            move = self.ui.get_user_input(prompt)

        if move.isdigit():
            self.observer_auto_moves = int(move) - 1
            move = ""

        if move == 'q':
            quit_choice = self.ui.get_human_quit_choice()
            if quit_choice == 'r':
                game.resign_current_player()
                self.ui.display_game_over_message(game)
                return game, GameLoopAction.RETURN_TO_MENU
            elif quit_choice == 's':
                self.file_manager.save_game_log()
                self.ui.display_message("Game saved. Exiting to main menu.")
                return game, GameLoopAction.QUIT_APPLICATION  # <-- Change this line
            elif quit_choice == 'q':
                self.ui.display_message("Exiting game without saving.")
                return game, GameLoopAction.QUIT_APPLICATION
            elif quit_choice == 'c':
                return game, GameLoopAction.CONTINUE
        elif move == 'm':
            return game, GameLoopAction.IN_GAME_MENU
        elif move.strip():
            try:
                game.make_manual_move(move)
            except Exception as e:
                self.ui.display_message(f"{RED}Invalid move: {e}{ENDC}")
        else:
            self.ui.display_turn_message(game)
            try:
                game.play_turn()
            except Exception as e:
                self.ui.display_message(f"{RED}AI move error: {e}{ENDC}")

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

    def play_game(self, game):
        move_number = 1
        while not game.is_over():
            self.ui.display_board(game.board)
            current_player = game.current_player()
            color = "White" if game.turn == "w" else "Black"
            player_name = current_player.name
            skill_str = f" (Skill: {current_player.skill})" if hasattr(current_player, "skill") and current_player.skill else ""
            prompt = f"Move {move_number} ({color}): {player_name}{skill_str}"

            self.ui.display_message(f"{prompt}")
            move = self.ui.get_user_input("Enter your move (or press Enter to let the player move): ")

            if move.strip():
                try:
                    game.make_manual_move(move)
                except Exception as e:
                    self.ui.display_message(f"{RED}Invalid move: {e}{ENDC}")
            else:
                self.ui.display_message(f"{prompt} is thinking...")
                try:
                    move = current_player.get_move(game)
                    game.make_manual_move(move)
                except Exception as e:
                    self.ui.display_message(f"{RED}AI move error: {e}{ENDC}")

            if game.turn == "b":
                move_number += 1

        # ...existing code...
