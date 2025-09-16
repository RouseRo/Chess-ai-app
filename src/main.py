import os
import sys
import json
import logging
from datetime import datetime, timezone

import chess

from src.game import Game, RED, ENDC
from src.ui_manager import UIManager
from src.file_manager import FileManager
from src.expert_service import ExpertService
from src.player_factory import PlayerFactory
from src.user_manager import UserManager
from src.auth_ui import AuthUI
from src.game_log_manager import GameLogManager
from src.player_stats_manager import PlayerStatsManager
from src.game_manager import GameManager
from src.in_game_menu_handlers import InGameMenuHandlers
from src.chess_expert_menu import ChessExpertMenu
from src.menu_handlers import MenuHandlers
from src.game import GameLoopAction


LOG_FILE = 'chess_game.log'
PLAYER_STATS_FILE = 'logs/player_stats.json'

class ChessApp:
    """The main application class that orchestrates the game."""

    def __init__(self):
        """Initializes the application, loading configurations."""
        self.ui = UIManager()
        self.file_manager = FileManager(self.ui)
        self.white_openings = {}
        self.black_defenses = {}
        self.ai_models = {}
        self.stockfish_path = None
        self.stockfish_configs = {}
        self.chess_expert_model = ""

        # Add user management components
        self.user_manager = UserManager(data_dir="user_data", dev_mode=True)  # Set dev_mode=True
        self.auth_ui = AuthUI()
        self.session_token = None
        self.current_user = None

        self._load_config()
        # Initialize services and factories after config is loaded
        self.expert_service = ExpertService(self.ui, self.chess_expert_model)
        self.player_factory = PlayerFactory(
            self.ui, self.ai_models, self.stockfish_configs, self.stockfish_path
        )
        self.game_log_manager = GameLogManager(self.ui, self.player_factory, self.ai_models, self.stockfish_configs)
        self.player_stats_manager = PlayerStatsManager(self.ui, self.file_manager)
        # Pass file_manager to GameManager here:
        self.game_manager = GameManager(self.ui, self.player_factory, self.ai_models, self.stockfish_configs, self.file_manager)
        self.in_game_menu_handlers = InGameMenuHandlers(
            self.ui,
            self.file_manager,
            self.player_factory,
            self.ai_models,
            self.stockfish_configs,
            self.expert_service,
            self  # <-- Pass self as game_runner, assuming ChessApp has run_game_loop
        )
        self.chess_expert_menu = ChessExpertMenu(self.ui, self.expert_service)
        self.menu_handlers = MenuHandlers(self.ui, self.chess_expert_menu)

        # Try to load session from file if it exists
        self._load_session()

    def _load_config(self):
        """Loads configuration from config.json."""
        try:
            with open('src/config.json', 'r') as f:
                config = json.load(f)
                self.white_openings = config.get("white_openings", {})
                self.black_defenses = config.get("black_defenses", {})
                self.ai_models = config.get("ai_models", {})
                # Use environment variable if set, else config value, else default "stockfish"
                self.stockfish_path = os.environ.get("STOCKFISH_EXECUTABLE", config.get("stockfish_path", "stockfish"))
                self.stockfish_configs = config.get("stockfish_configs", {})
                self.chess_expert_model = config.get('chess_expert_model', 'google/gemini-2.5-pro')
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.ui.display_message(f"{RED}Fatal Error: Could not load or parse 'src/config.json'.{ENDC}")
            self.ui.display_message(f"Reason: {e}")
            self.ui.display_message("Please ensure the file exists and is a valid JSON.")
            sys.exit(1)

    def _load_session(self):
        """Attempt to load a saved session if it exists."""
        session_file = os.path.join("user_data", "current_session.txt")
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r') as f:
                    saved_token = f.read().strip()

                # Validate the token
                user_data = self.user_manager.get_current_user(saved_token)
                if user_data:
                    self.session_token = saved_token
                    self.current_user = user_data
                    print(f"Welcome back, {user_data['username']}!")
            except Exception as e:
                print(f"Error loading saved session: {e}")

    def _handle_authentication(self):
        """Handle user authentication flow. Return True if authenticated."""
        # If already authenticated, return True immediately
        if self.current_user:
            return True

        while not self.current_user:
            choice = self.auth_ui.display_auth_menu()

            if choice == '1':  # Login
                username_or_email, password = self.auth_ui.get_login_credentials()
                success, message, token = self.user_manager.login(username_or_email, password)

                self.auth_ui.display_message(message)
                if success:
                    self.session_token = token
                    self.current_user = self.user_manager.get_current_user(token)
                    self._save_session()
                    return True

            elif choice == '2':  # Register
                registration_info = self.auth_ui.get_registration_info()
                if registration_info:
                    username, email, password = registration_info
                    success, message = self.user_manager.register_user(username, email, password)

                    self.auth_ui.display_message(message)
                    if success:
                        if self.user_manager.dev_mode:
                            # In dev mode, show a special message about verification
                            print("In development mode, verification tokens are displayed in the console.")
                            print("You can use the token shown above to verify your account.")

                        # Ask for verification token
                        verify_now = input("Would you like to enter your verification code now? (y/n): ").lower() == 'y'
                        if verify_now:
                            token = self.auth_ui.get_verification_token()
                            success, msg = self.user_manager.verify_email(token)
                            self.auth_ui.display_message(msg)

                            # If verification was successful, try to auto-login
                            if success:
                                print("Attempting automatic login after verification...")
                                success, message, token = self.user_manager.login(username, password)
                                if success:
                                    self.session_token = token
                                    self.current_user = self.user_manager.get_current_user(token)
                                    self._save_session()
                                    return True

            elif choice == 'q':  # Quit
                return False

        return True  # Already authenticated

    def _save_session(self):
        """Save the current session token to a file."""
        if self.session_token:
            os.makedirs("user_data", exist_ok=True)
            session_file = os.path.join("user_data", "current_session.txt")

            with open(session_file, 'w') as f:
                f.write(self.session_token)

    def get_password(prompt="Password: "):
        """Get password with or without masking based on environment"""
        # Check if we're in test mode
        if os.environ.get("CHESS_APP_TEST_MODE") == "1":
            # In test mode, accept password input directly without masking
            return input(prompt)
        else:
            # In normal mode, use getpass for secure password input
            import getpass
            return getpass.getpass(prompt)

    def run(self):
        """Main function to run the chess application."""
        # Handle authentication first
        if not self._handle_authentication():
            print("Exiting application.")
            return

        game = None
        while True:
            if game:
                # Handle game over
                if game.board.is_game_over():
                    self.ui.display_game_over_message(game)
                    result = self.game_manager.determine_game_result(game)
                    self.player_stats_manager.update_player_stats(game)
                    save_choice = self.ui.get_user_input("\nSave final game log? (y/N): ").lower()
                    if save_choice == 'y':
                        self.file_manager.save_game_log()
                    self.ui.get_user_input("Press Enter to return to the main menu.")
                    game = None
                    continue

                # Play a turn and process the returned action
                game, action = self.game_manager.play_turn(game)
                if action == GameLoopAction.QUIT_APPLICATION:
                    sys.exit(0)
                elif action == GameLoopAction.RETURN_TO_MENU:
                    game = None
                    continue
                elif action in [GameLoopAction.CONTINUE, GameLoopAction.SKIP_TURN]:
                    continue
                elif action == GameLoopAction.IN_GAME_MENU:
                    logging.info(f"[DIAG] Handling IN_GAME_MENU")
                    game, action = self.in_game_menu_handlers.handle_in_game_menu(game)
                    logging.info(f"[DIAG] After in-game menu, action: {action}")
                    if action == GameLoopAction.QUIT_APPLICATION:
                        logging.info(f"[DIAG] Quitting application from in-game menu")
                        sys.exit(0)
                    elif action == GameLoopAction.RETURN_TO_MENU:
                        logging.info(f"[DIAG] Returning to main menu from in-game menu")
                        game = None
                        continue
                    continue
                else:
                    print("[DIAG] action did NOT match any known GameLoopAction", flush=True)
            else:
                # Main menu loop
                choice = self.menu_handlers.display_main_menu()
                if choice is None:
                    # If choice is None, skip processing and return to the main menu
                    continue

                if choice.startswith('?'):
                    question = choice[1:].strip()
                    self.chess_expert_menu.handle_chess_expert_menu(direct_question=question)
                else:
                    try:
                        if choice == '1':
                            self.game_log_manager.initialize_new_game_log()
                            game, white_opening_obj, black_defense_obj = self.game_manager.setup_new_game(self.white_openings, self.black_defenses)
                            if not game:
                                self.ui.display_message("New game cancelled.")
                                continue
                            self.game_log_manager.log_new_game_header(game, white_opening_obj, black_defense_obj)
                            self.ui.display_game_start_message(game)
                        elif choice == '2':
                            game_summaries = self.file_manager.get_saved_game_summaries()
                            if not game_summaries:
                                self.ui.display_message("No saved games found.")
                                continue
                            chosen_summary = self.ui.display_saved_games_and_get_choice(game_summaries)
                            if chosen_summary and chosen_summary not in ['m', 'q']:
                                game = self.game_log_manager.load_game_from_log(chosen_summary['filename'])
                        elif choice == '3':
                            new_game, action = self.in_game_menu_handlers.handle_practice_load_in_menu(game)
                            if new_game:
                                game = new_game
                                self.ui.display_game_start_message(game)
                        elif choice == '4':
                            self.player_stats_manager.view_player_stats()
                        elif choice == 'q':
                            self.ui.display_message("Exiting application.")
                            sys.exit(0)
                    except Exception as e:
                        self.ui.display_message(f"\n{RED}An unexpected error occurred: {e}{ENDC}")
                        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
                        self.ui.get_user_input("Press Enter to acknowledge and return to the main menu.")

    def parse_log_header(self, lines, all_player_keys, debug=False):
        return self.game_log_manager.parse_log_header(lines, all_player_keys, debug)

def main():
    try:
        if os.environ.get("CHESS_APP_TEST_MODE") == "1":
            app = ChessApp()
            app.current_user = {"username": "TestUser"}
            app.run()
        else:
            app = ChessApp()
            app.run()
    except (KeyboardInterrupt):
        print("\n[INFO] Application interrupted or exited. Exiting gracefully.")
        sys.exit(0)

if __name__ == "__main__":
    main()