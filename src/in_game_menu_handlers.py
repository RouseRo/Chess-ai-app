import sys
import json
import shutil
import logging
import chess
from src.constants import GameLoopAction
from src.human_player import HumanPlayer

class InGameMenuHandlers:
    def __init__(self, ui, file_manager, player_factory, ai_models, stockfish_configs, expert_service, game_runner):
        self.ui = ui
        self.file_manager = file_manager
        self.player_factory = player_factory
        self.ai_models = ai_models
        self.stockfish_configs = stockfish_configs
        self.expert_service = expert_service
        self.game_runner = game_runner  # <-- Add this line

    def handle_load_game_in_menu(self, game):
        game_summaries = self.file_manager.get_saved_game_summaries()
        if not game_summaries:
            self.ui.display_message("No saved games found.")
            return game, GameLoopAction.CONTINUE

        chosen_summary = self.ui.display_saved_games_and_get_choice(game_summaries)
        if chosen_summary == 'm':
            return game, GameLoopAction.RETURN_TO_MENU
        elif chosen_summary == 'q':
            self.ui.display_message("Exiting application.")
            sys.exit()
        elif chosen_summary:
            chosen_file = chosen_summary['filename']
            loaded_game = self.file_manager.load_game_from_log(chosen_file)
            if loaded_game:
                logging.shutdown()
                shutil.copy(chosen_file, 'chess_game.log')
                logging.basicConfig(filename='chess_game.log', level=logging.INFO, format='%(asctime)s - %(message)s', filemode='a')
                logging.getLogger("httpx").setLevel(logging.WARNING)
                self.ui.display_message(f"Successfully loaded game from {chosen_file}.")
                return loaded_game, GameLoopAction.SKIP_TURN
        return game, GameLoopAction.CONTINUE

    def handle_practice_load_in_menu(self, game):
        DEBUG = False  # Set to True to enable diagnostics
        GREEN = "\033[92m"
        ENDC = "\033[0m"
        while True:
            with open('src/puzzles.json', 'r') as f:
                positions = json.load(f)
            position = self.ui.display_practice_positions_and_get_choice(positions)
            if position and position not in ['?', 'm', 'q']:
                # Display the board
                if 'fen' in position:
                    self.ui.display_board_from_fen(position['fen'])
                # Diagnostic: print the position dict
                if DEBUG:
                    print(f"[DEBUG] Selected position: {position}")
                # Display the number and description before player selection
                number = position.get('number', '')
                description = position.get('description', '')
                name = position.get('name', '')
                # Show name if description is missing
                if number or description or name:
                    desc_text = f"Position {number}: {GREEN}{description}{ENDC}" if description else f"{name}"
                    self.ui.display_message(f"{desc_text}\n")
                # Now ask for player choices
                result = self.ui.display_model_menu_and_get_choice(self.ai_models, self.stockfish_configs)
                # Handle menu and quit choices BEFORE creating players
                if not result or result in ['', None]:
                    continue
                white_player_key, black_player_key = result
                if white_player_key == "m" or black_player_key == "m":
                    return game, GameLoopAction.RETURN_TO_MENU
                if white_player_key == "q" or black_player_key == "q":
                    self.ui.display_message("Exiting application.")
                    sys.exit()
                if not white_player_key or not black_player_key:
                    continue
                player1 = self.player_factory.create_player(white_player_key, color_label="White")
                player2 = self.player_factory.create_player(black_player_key, color_label="Black")
                new_game = Game(player1, player2, white_player_key=white_player_key, black_player_key=black_player_key)
                new_game.set_board_from_fen(position['fen'])
                new_game.initialize_game()
                self.ui.display_message(f"Loaded practice position: {position['name']}")
                # Diagnostic: Log object details before returning
                logging.info(f"[DIAG] Returning new_game: {new_game}")
                logging.info(f"[DIAG] GameLoopAction.SKIP_TURN: {GameLoopAction.SKIP_TURN}")
                # Do not call run_game_loop; just return the new_game to let the main loop handle it
                return new_game, GameLoopAction.SKIP_TURN
            elif position and position.startswith('?'):
                question = position[1:].strip()
                self.expert_service.ask_expert(question)
            elif position == 'm':
                return game, GameLoopAction.RETURN_TO_MENU
            elif position == 'q':
                self.ui.display_message("Exiting application.")
                sys.exit()
            else:
                continue
        return game, GameLoopAction.CONTINUE

    def handle_in_game_menu(self, game):
        menu_choice = self.ui.display_in_game_menu()
        if menu_choice == 'l': # Load Game
            return self.handle_load_game_in_menu(game)
        elif menu_choice == 'p': # Load Practice
            return self.handle_practice_load_in_menu(game)
        elif menu_choice == 's': # Save
            self.file_manager.save_game_log()
            return game, GameLoopAction.CONTINUE
        elif menu_choice.startswith('?'): # Ask Expert
            question = menu_choice[1:].strip()
            self.expert_service.ask_expert(question)
            return game, GameLoopAction.CONTINUE
        elif menu_choice == 'r': # Return to Game
            return game, GameLoopAction.CONTINUE
        elif menu_choice == 'q': # Quit
            return game, GameLoopAction.QUIT_APPLICATION
        return game, GameLoopAction.CONTINUE

    def handle_quit_request(self, game):
        current_player = game.get_current_player()
        if isinstance(current_player, HumanPlayer):
            quit_choice = self.ui.get_human_quit_choice()
            if quit_choice == 'r':
                self.handle_resignation(game)
            elif quit_choice == 's':
                self.file_manager.save_game_log()
                self.ui.display_message("Game saved. Exiting application.")
                sys.exit()
            elif quit_choice == 'q':
                self.ui.display_message("Exiting without saving.")
                sys.exit()
            else:  # 'c' to cancel
                return True
        else:
            self.handle_resignation(game)
        return False

    def handle_resignation(self, game):
        resigning_color = "White" if game.board.turn == chess.WHITE else "Black"
        resigning_player = game.get_current_player().model_name
        self.ui.display_message(f"\n{resigning_player} ({resigning_color}) has resigned.")
        result = "0-1" if resigning_color == "White" else "1-0"
        # You may need to update player stats here using your stats manager
        save_choice = self.ui.get_user_input("Save final game log? (y/N): ").lower()
        if save_choice == 'y':
            self.file_manager.save_game_log()
        self.ui.display_message("Exiting application.")
        sys.exit()