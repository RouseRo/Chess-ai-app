import chess
import json
from game import BLUE, ENDC

class UIManager:
    """Handles all console input and output for the application."""

    # --- Private Helper Methods for Refactoring ---

    @staticmethod
    def _get_menu_choice(title, options, prompt):
        """A generic helper to display a menu and get a valid choice."""
        UIManager.display_message(f"\n{title}")
        valid_choices = []
        for key, desc in options.items():
            UIManager.display_message(f"  {key}: {desc}")
            valid_choices.append(str(key))
        
        while True:
            choice = UIManager.get_user_input(prompt).lower()
            if choice in valid_choices:
                return choice
            else:
                UIManager.display_message("Invalid choice. Please enter a valid option.")

    @staticmethod
    def _get_numbered_choice(title, items, prompt, extra_options=None):
        """A generic helper for numbered lists."""
        UIManager.display_message(f"\n{title}")
        for i, item in enumerate(items):
            UIManager.display_message(f"  {i + 1}: {item}")
        
        if extra_options:
            for key, desc in extra_options.items():
                UIManager.display_message(f"  {key}: {desc}")

        while True:
            choice = UIManager.get_user_input(prompt)
            if extra_options and choice in extra_options:
                return choice
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(items):
                    return items[choice_num - 1]
                else:
                    UIManager.display_message("Invalid number.")
            except ValueError:
                UIManager.display_message("Invalid input. Please enter a valid number or option.")

    @staticmethod
    def _display_setup_columns(white_openings, black_defenses, ai_models, stockfish_configs):
        """Handles the multi-column display for the new game setup."""
        white_list = [f"  {k}: {v.replace('Play the ', '')}" for k, v in white_openings.items()]
        black_list = [f"  {k}: {v.replace('Play the ', '')}" for k, v in black_defenses.items()]
        player_list = UIManager._display_player_options(ai_models, stockfish_configs)

        white_width = max(len(s) for s in white_list) + 4
        black_width = max(len(s) for s in black_list) + 4

        UIManager.display_message(f"\n{'--- White Openings ---':<{white_width}}{'--- Black Defenses ---':<{black_width}}{'--- Player Models ---'}")
        
        num_rows = max(len(white_list), len(black_list), len(player_list))
        for i in range(num_rows):
            white_col = white_list[i] if i < len(white_list) else ""
            black_col = black_list[i] if i < len(black_list) else ""
            player_col = player_list[i] if i < len(player_list) else ""
            UIManager.display_message(f"{white_col:<{white_width}}{black_col:<{black_width}}{player_col}")

    @staticmethod
    def _parse_setup_input(choice, white_openings, black_defenses, ai_models, stockfish_configs):
        """Parses and validates the complex input string for game setup."""
        parts = choice.lower().split()
        if len(parts) != 2: return None

        opening_choice, player_choice = parts[0], parts[1]
        if len(opening_choice) != 2 or len(player_choice) != 4: return None

        white_opening_key, black_defense_key = opening_choice[0], opening_choice[1]
        white_player_key, black_player_key = player_choice[:2], player_choice[2:]

        if (white_opening_key in white_openings and
            black_defense_key in black_defenses and
            UIManager._validate_player_keys(white_player_key, black_player_key, ai_models, stockfish_configs)):
            return white_opening_key, black_defense_key, white_player_key, black_player_key
        
        return None

    @staticmethod
    def _display_player_options(ai_models, stockfish_configs):
        """Displays a formatted list of AI and Stockfish player options."""
        player_list = [f"  {k}: {v}" for k, v in ai_models.items()]
        player_list += [f"  {k}: Stockfish - {v['name']}" for k, v in stockfish_configs.items()]
        return player_list

    @staticmethod
    def _validate_player_keys(white_key, black_key, ai_models, stockfish_configs):
        """Validates if the given player keys are legitimate choices."""
        is_white_valid = white_key in ai_models or white_key in stockfish_configs
        is_black_valid = black_key in ai_models or black_key in stockfish_configs
        return is_white_valid and is_black_valid

    # --- Public Methods ---

    @staticmethod
    def display_message(message):
        """Prints a message to the console."""
        print(message)

    @staticmethod
    def get_user_input(prompt):
        """Gets input from the user with a given prompt."""
        return input(prompt)

    @staticmethod
    def display_main_menu():
        """Displays the main menu and gets the user's choice."""
        options = {
            '1': "Play a New Game",
            '2': "Load a Saved Game",
            '3': "Load a Practice Position",
            '4': "View Player Stats",
            '?': "Ask a Chess Expert",
            'q': "Quit"
        }
        return UIManager._get_menu_choice("--- Main Menu ---", options, "Enter your choice: ")

    @staticmethod
    def display_game_menu_and_get_choice():
        """Displays the in-game menu and gets the user's choice."""
        options = {
            'l': "Load Another Game",
            'p': "Load Practice Position",
            's': "Save Game",
            'c': "Change AI Model",
            '?': "Ask a Chess Expert",
            'r': "Return to Game",
            'q': "Quit Application"
        }
        return UIManager._get_menu_choice("--- Game Menu ---", options, "Enter your choice: ")

    @staticmethod
    def display_player_stats(stats):
        """Displays player statistics in a formatted table."""
        UIManager.display_message("\n--- Player Statistics ---")
        if not stats:
            UIManager.display_message("No player statistics found.")
            return

        # Sort players by wins (descending)
        sorted_players = sorted(stats.items(), key=lambda item: item[1]['wins'], reverse=True)

        # Find max name length for formatting
        max_name_len = max(len(name) for name, _ in sorted_players) if sorted_players else 20

        # Header
        header = f"{'Player':<{max_name_len}} | {'Wins':>5} | {'Losses':>7} | {'Draws':>5}"
        UIManager.display_message(header)
        UIManager.display_message('-' * len(header))

        # Rows
        for player_name, data in sorted_players:
            wins = data.get('wins', 0)
            losses = data.get('losses', 0)
            draws = data.get('draws', 0)
            row = f"{player_name:<{max_name_len}} | {wins:>5} | {losses:>7} | {draws:>5}"
            UIManager.display_message(row)

    @staticmethod
    def display_setup_menu_and_get_choices(white_openings, black_defenses, ai_models, stockfish_configs):
        """Displays the new game setup menu and gets user choices."""
        UIManager._display_setup_columns(white_openings, black_defenses, ai_models, stockfish_configs)

        while True:
            choice = UIManager.get_user_input("\nEnter choices for openings and players (e.g., '1a m1s2'): ")
            parsed_keys = UIManager._parse_setup_input(choice, white_openings, black_defenses, ai_models, stockfish_configs)
            if parsed_keys:
                return parsed_keys
            
            UIManager.display_message("Invalid input. Please enter a valid string like '1a m1s2' or '1a s1m3'.")

    @staticmethod
    def display_model_menu_and_get_choice(ai_models, stockfish_configs):
        """Displays AI model and Stockfish options and gets the user's choice."""
        UIManager.display_message("\n--- Choose Players for Practice ---")
        player_list = UIManager._display_player_options(ai_models, stockfish_configs)
        for player in player_list:
            UIManager.display_message(player)

        while True:
            choice = UIManager.get_user_input("\nEnter your choice for White and Black players (e.g., 'm1s2'): ").lower()
            if len(choice) == 4:
                white_player_key = choice[:2]
                black_player_key = choice[2:]
                if UIManager._validate_player_keys(white_player_key, black_player_key, ai_models, stockfish_configs):
                    return white_player_key, black_player_key
            
            UIManager.display_message("Invalid input. Please enter a valid choice for both players (e.g., 'm1s2').")

    @staticmethod
    def display_saved_games_and_get_choice(saved_games):
        """Displays a list of saved games and prompts for a choice."""
        return UIManager._get_numbered_choice(
            "--- Saved Games ---",
            saved_games,
            "Enter the number of the game to load: "
        )

    @staticmethod
    def display_practice_positions_and_get_choice(positions):
        """Displays a list of practice positions and prompts for a choice."""
        position_names = [p['name'] for p in positions]
        extra_opts = {'?': "Ask a question about chess"}
        
        choice = UIManager._get_numbered_choice(
            "--- Practice Checkmate Positions ---",
            position_names,
            "Enter the number of the position to load, or '?' to ask a question: ",
            extra_options=extra_opts
        )

        if choice == '?':
            return '?'
        
        # Find the full position dictionary that matches the chosen name
        for pos in positions:
            if pos['name'] == choice:
                return pos
        return None # Should not happen if logic is correct

    @staticmethod
    def get_chess_question():
        """Prompts the user to enter their chess question."""
        return UIManager.get_user_input("What is your question for the Grandmaster? ")

    @staticmethod
    def display_game_start_message(game):
        """Displays the initial message when a game starts."""
        UIManager.display_message(f"\nNew game started. White: {game.players[chess.WHITE].model_name}, Black: {game.players[chess.BLACK].model_name}")

    @staticmethod
    def display_board(board):
        """Displays the chess board with rank/file labels and highlights the last move."""
        last_move = board.peek() if board.move_stack else None
        from_square = last_move.from_square if last_move else None
        to_square = last_move.to_square if last_move else None

        board_str = "\n"
        board_str += "  a b c d e f g h\n"
        board_str += " -----------------\n"

        for rank in range(7, -1, -1):
            line = f"{rank + 1}|"
            for file in range(8):
                square = chess.square(file, rank)
                piece = board.piece_at(square)
                
                symbol = "."
                if piece:
                    symbol = piece.symbol()

                if square == to_square:
                    line += f" {BLUE}{symbol}{ENDC}"
                elif square == from_square:
                    # Highlight the origin square with a blue dot
                    line += f" {BLUE}.{ENDC}"
                else:
                    line += f" {symbol}"
            
            line += f" |{rank + 1}\n"
            board_str += line

        board_str += " -----------------\n"
        board_str += "  a b c d e f g h\n"
        
        UIManager.display_message(board_str)

    @staticmethod
    def display_turn_message(game):
        """Displays whose turn it is, including the move number."""
        move_number = game.board.fullmove_number
        turn_color = "White" if game.board.turn else "Black"
        player = game.players[game.board.turn]
        UIManager.display_message(f"\nMove {move_number} ({turn_color}): {player.model_name} is thinking...")

    @staticmethod
    def display_game_over_message(game):
        """Displays the game over message."""
        result = game.get_game_result()
        UIManager.display_message("\n--- Game Over ---")
        UIManager.display_message(f"Result: {result}")
        UIManager.display_board(game.board)