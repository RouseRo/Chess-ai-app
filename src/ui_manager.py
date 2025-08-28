import chess
from game import BLUE, ENDC

class UIManager:
    """Handles all user interface interactions for the console."""

    @staticmethod
    def get_user_input(prompt):
        """Gets stripped user input from the console."""
        return input(prompt).strip()

    @staticmethod
    def display_message(message, end="\n"):
        """Prints a message to the console."""
        print(message, end=end)

    @staticmethod
    def display_main_menu():
        """Displays the main menu and gets the user's choice."""
        UIManager.display_message("\n--- Main Menu ---")
        UIManager.display_message("  1: Play a New AI vs AI Game")
        UIManager.display_message("  2: Load a Saved Game")
        UIManager.display_message("  3: Load a Practice Position")
        UIManager.display_message("  4: Quit")
        while True:
            choice = UIManager.get_user_input("Enter your choice (1-4): ")
            if choice in ['1', '2', '3', '4']:
                return choice
            else:
                UIManager.display_message("Invalid choice. Please enter a number from 1 to 4.")

    @staticmethod
    def display_game_menu_and_get_choice():
        """Displays the in-game menu and gets the user's choice."""
        UIManager.display_message("\n--- Game Menu ---")
        UIManager.display_message("  l: Load a saved game")
        UIManager.display_message("  p: Load a practice position")
        UIManager.display_message("  s: Swap AI Model")
        UIManager.display_message("  c: Cancel and continue game")
        while True:
            choice = UIManager.get_user_input("Enter your choice: ").lower()
            if choice in ['l', 'p', 's', 'c']:
                return choice
            else:
                UIManager.display_message("Invalid choice. Please enter 'l', 'p', 's', or 'c'.")

    @staticmethod
    def display_setup_menu_and_get_choices(white_openings, black_defenses, ai_models):
        """Displays all setup menus in columns and gets the user's combined choice."""
        white_list = [f"  {k}: {v.replace('Play the ', '')}" for k, v in white_openings.items()]
        black_list = [f"  {k}: {v.replace('Play the ', '')}" for k, v in black_defenses.items()]
        model_list = [f"  {k}: {v}" for k, v in ai_models.items()]

        white_width = max(len(s) for s in white_list) + 4
        black_width = max(len(s) for s in black_list) + 4

        UIManager.display_message(f"\n{'--- White Openings ---':<{white_width}}{'--- Black Defenses ---':<{black_width}}{'--- AI Models ---'}")
        
        num_rows = max(len(white_list), len(black_list), len(model_list))
        for i in range(num_rows):
            white_col = white_list[i] if i < len(white_list) else ""
            black_col = black_list[i] if i < len(black_list) else ""
            model_col = model_list[i] if i < len(model_list) else ""
            UIManager.display_message(f"{white_col:<{white_width}}{black_col:<{black_width}}{model_col}")

        while True:
            choice = UIManager.get_user_input("\nEnter choices for openings and models (e.g., '1a m1m2'): ").lower()
            parts = choice.split()
            
            if len(parts) == 2:
                opening_choice, model_choice = parts[0], parts[1]
                if len(opening_choice) == 2 and len(model_choice) == 4:
                    white_opening_key, black_defense_key = opening_choice[0], opening_choice[1]
                    white_model_key, black_model_key = model_choice[:2], model_choice[2:]

                    if (white_opening_key in white_openings and
                        black_defense_key in black_defenses and
                        white_model_key in ai_models and
                        black_model_key in ai_models):
                        return white_opening_key, black_defense_key, white_model_key, black_model_key
            
            UIManager.display_message("Invalid input. Please enter a valid string like '1a m1m2'.")

    @staticmethod
    def display_model_menu_and_get_choice(ai_models):
        """Displays AI model options and gets the user's choice."""
        UIManager.display_message("\n--- Choose AI Models for Practice ---")
        for key, value in ai_models.items():
            UIManager.display_message(f"  {key}: {value}")

        while True:
            choice = UIManager.get_user_input("\nEnter your choice for White and Black models (e.g., 'm1m2'): ").lower()
            if len(choice) == 4 and choice.startswith('m') and choice[2] == 'm':
                white_model_key = choice[:2]
                black_model_key = choice[2:]
                if white_model_key in ai_models and black_model_key in ai_models:
                    return white_model_key, black_model_key
            
            UIManager.display_message("Invalid input. Please enter a valid choice for both models (e.g., 'm1m2').")

    @staticmethod
    def display_saved_games_and_get_choice(saved_games):
        """Displays a list of saved games and prompts for a choice."""
        UIManager.display_message("\n--- Saved Games ---")
        for i, filename in enumerate(saved_games):
            UIManager.display_message(f"  {i + 1}: {filename}")
        
        try:
            choice = int(UIManager.get_user_input("Enter the number of the game to load: "))
            if 1 <= choice <= len(saved_games):
                return saved_games[choice - 1]
            else:
                UIManager.display_message("Invalid number.")
        except ValueError:
            UIManager.display_message("Invalid input.")
        return None

    @staticmethod
    def display_practice_positions_and_get_choice(positions):
        """Displays a list of practice positions and prompts for a choice."""
        UIManager.display_message("\n--- Practice Checkmate Positions ---")
        for i, pos in enumerate(positions):
            UIManager.display_message(f"  {i + 1}: {pos['name']}")
        
        try:
            choice = int(UIManager.get_user_input("Enter the number of the position to load: "))
            if 1 <= choice <= len(positions):
                return positions[choice - 1]
            else:
                UIManager.display_message("Invalid number.")
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            UIManager.display_message("Could not load practice positions file or invalid input.")
        return None

    @staticmethod
    def display_game_start_message(game):
        """Displays the initial message when a game starts."""
        UIManager.display_message("\n--- Starting AI vs AI Chess Game ---")
        UIManager.display_message(f"Player 1 (White): {game.players[chess.WHITE].model_name} (Strategy: {game.strategies[chess.WHITE]})")
        UIManager.display_message(f"Player 2 (Black): {game.players[chess.BLACK].model_name} (Strategy: {game.strategies[chess.BLACK]})")
        UIManager.display_message("------------------------------------")

    @staticmethod
    def display_turn_message(game):
        """Displays the message indicating whose turn it is."""
        turn = game.board.turn
        current_player = game.players[turn]
        player_name = "Player 1 (White)" if turn == chess.WHITE else "Player 2 (Black)"
        move_number = game.board.fullmove_number
        strategy = game.strategies[turn]

        UIManager.display_message(f"\n{BLUE}Move {move_number}:{ENDC} {player_name}'s turn ({current_player.model_name})...")
        if strategy and game.board.fullmove_number <= 3:
            UIManager.display_message(f"Strategy: {strategy}")

    @staticmethod
    def display_game_over_message(game):
        """Displays the final board and result."""
        result = game.get_game_result()
        UIManager.display_message("\n--- Game Over ---")
        game.display_board()
        UIManager.display_message(f"Result: {result}")
        UIManager.display_message("Game history has been saved to chess_game.log")