import chess
from src.game import BLUE, CYAN, GREEN, YELLOW, RED, WHITE, ENDC

class UIManager:
    """Simple console UI helper. Menu titles and option text are shown in color."""

    @staticmethod
    def _color_title(title: str) -> str:
        return f"{BLUE}{title}{ENDC}"

    @staticmethod
    def display_message(msg: str = "", color: str | None = None) -> None:
        """Print a message optionally wrapped in an ANSI color."""
        if color:
            print(f"{color}{msg}{ENDC}")
        else:
            print(msg)

    @staticmethod
    def get_user_input(prompt: str = "") -> str:
        try:
            # prompt in yellow to draw attention
            return input(f"{YELLOW}{prompt}{ENDC}").strip()
        except (KeyboardInterrupt, EOFError):
            return ""

    def get_human_player_name(self, color_str: str = "Human") -> str:
        """Prompt for a human player's name. Returns a non-empty name (defaults to 'Human')."""
        prompt = f"Enter name for {color_str} player (leave blank for 'Human'): "
        name = self.get_user_input(prompt)
        return name if name else "Human"

    def display_main_menu(self) -> str:
        title = self._color_title("--- Main Menu ---")
        print(title)
        # selection number/letter in white, option text in cyan
        print(f"  {WHITE}1:{ENDC} {CYAN}Play a New Game{ENDC}")
        print(f"  {WHITE}2:{ENDC} {CYAN}Load a Saved Game{ENDC}")
        print(f"  {WHITE}3:{ENDC} {CYAN}Load a Practice Position{ENDC}")
        print(f"  {WHITE}4:{ENDC} {CYAN}View Player Stats{ENDC}")
        print(f"  {WHITE}?:{ENDC} {CYAN}Ask a Chess Expert{ENDC}")
        print(f"  {WHITE}q:{ENDC} {CYAN}Quit{ENDC}")
        return self.get_user_input("Enter your choice: ")

    def display_in_game_menu(self) -> str:
        title = self._color_title("--- In-Game Menu ---")
        print(title)
        print(f"  {WHITE}l:{ENDC} {CYAN}Load Saved Game{ENDC}")
        print(f"  {WHITE}p:{ENDC} {CYAN}Load Practice Position{ENDC}")
        print(f"  {WHITE}s:{ENDC} {CYAN}Save Game{ENDC}")
        print(f"  {WHITE}r:{ENDC} {CYAN}Return to Game{ENDC}")
        print(f"  {WHITE}q:{ENDC} {CYAN}Quit Application{ENDC}")
        print(f"  {WHITE}?:{ENDC} {CYAN}?<question>: Ask Chess Expert (prefix with '?'){ENDC}")
        return self.get_user_input("Enter choice: ")

    def display_saved_games_and_get_choice(self, game_summaries):
        """Displays a formatted list of saved games and prompts the user for a choice."""
        title = self._color_title("--- Load a Saved Game ---")
        print(title)
        if not game_summaries:
            print("No saved games found.")
            self.get_user_input("Press Enter to return to the main menu.")
            return None

        for i, summary in enumerate(game_summaries):
            white = summary.get('white', 'N/A')
            black = summary.get('black', 'N/A')
            result = summary.get('result', '*') # Use '*' for in-progress games
            
            # Prioritize the date from the filename, fallback to the date in the log content
            date = summary.get('file_date', summary.get('date', 'Unknown Date'))

            # Truncate long names to keep the display clean
            white_name = (white[:20] + '..') if len(white) > 22 else white
            black_name = (black[:20] + '..') if len(black) > 22 else black

            print(f"  {WHITE}{i+1}:{ENDC} {CYAN}{white_name}{ENDC} vs {CYAN}{black_name}{ENDC}")
            print(f"     {YELLOW}Result: {result}, Date: {date}{ENDC}")

        print(f"\n  {WHITE}m:{ENDC} Return to Main Menu")
        
        while True:
            choice = self.get_user_input("Enter the number of the game to load, or 'm' to return: ")
            if choice.lower() == 'm':
                return 'm'
            
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(game_summaries):
                    return game_summaries[choice_idx] # Return the whole summary dict
                else:
                    print(f"{RED}Invalid number. Please enter a number between 1 and {len(game_summaries)}.{ENDC}")
            except ValueError:
                print(f"{RED}Invalid input. Please enter a number or 'm'.{ENDC}")

    def display_practice_positions_and_get_choice(self, positions):
        title = self._color_title("--- Practice Positions ---")
        print(title)
        for i, p in enumerate(positions, start=1):
            print(f"  {WHITE}{i}:{ENDC} {CYAN}{p.get('name','Unknown')}  ({p.get('fen','')}){ENDC}")
        print(f"  {WHITE}m:{ENDC} {CYAN}Return to Main Menu{ENDC}")
        print(f"  {WHITE}q:{ENDC} {CYAN}Quit Application{ENDC}")
        print(f"  {WHITE}?:{ENDC} {CYAN}?<question>: Ask Chess Expert{ENDC}")
        choice = self.get_user_input("Enter the number of the position to load, or a letter for other options: ")
        if choice.lower().startswith('?'):
            return choice
        if choice.lower() in ['m', 'q']:
            return choice.lower()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(positions):
                return positions[idx]
        except Exception:
            pass
        return None

    def display_model_menu_and_get_choice(self, ai_models, stockfish_configs):
        title = self._color_title("--- Choose Player Models ---")
        print(title)
        print(f"{CYAN}Available AI models:{ENDC}")
        for k, v in ai_models.items():
            print(f"  {WHITE}{k}:{ENDC} {CYAN}{v}{ENDC}")
        print(f"{CYAN}Available Stockfish configs:{ENDC}")
        for k, v in stockfish_configs.items():
            print(f"  {WHITE}{k}:{ENDC} {CYAN}Stockfish - {v.get('name')}{ENDC}")
        print(f"  {WHITE}hu:{ENDC} {CYAN}Human Player{ENDC}")
        choice = self.get_user_input("Enter choice for White and Black players (e.g., 'm1s2'), or press Enter to return: ")
        if choice == "":
            # treat Enter (empty input) as "return to main menu" by returning two None values
            return None, None
        parts = choice.replace(" ", "")
        if len(parts) >= 4:
            return parts[:2], parts[2:4]
        return None, None

    def display_setup_menu_and_get_choices(self, white_openings, black_defenses, ai_models, stockfish_configs):
        title = self._color_title("--- Setup New Game ---")
        print(title)
        print(f"{CYAN}Choose white opening (enter key or leave blank for default):{ENDC}")
        for k, v in white_openings.items():
            print(f"  {WHITE}{k}:{ENDC} {CYAN}{v}{ENDC}")
        white_opening = self.get_user_input("White opening key: ") or (list(white_openings.keys())[0] if white_openings else "")
        print(f"{CYAN}Choose black defense (enter key or leave blank for default):{ENDC}")
        for k, v in black_defenses.items():
            print(f"  {WHITE}{k}:{ENDC} {CYAN}{v}{ENDC}")
        black_defense = self.get_user_input("Black defense key: ") or (list(black_defenses.keys())[0] if black_defenses else "")
        white_key, black_key = self.display_model_menu_and_get_choice(ai_models, stockfish_configs)
        if not white_key or not black_key:
            return None
        return white_opening, black_defense, white_key, black_key

    def display_player_stats(self, stats):
        title = self._color_title("--- Player Statistics ---")
        print(title)
        print(f"{'Player':30} | {'Wins':>4} | {'Losses':>6} | {'Draws':>5}")
        print("-" * 57)
        for name, v in sorted(stats.items(), key=lambda x: (-x[1].get('wins',0), x[0])):
            wins = v.get('wins', 0)
            losses = v.get('losses', 0)
            draws = v.get('draws', 0)
            print(f"{name:30} | {wins:4} | {losses:6} | {draws:5}")

    def display_game_start_message(self, game):
        title = self._color_title("--- Game Started ---")
        print(title)
        white = game.players[chess.WHITE].model_name
        black = game.players[chess.BLACK].model_name
        print(f"White: {white}")
        print(f"Black: {black}")
        print(f"Initial FEN: {game.board.fen()}")

    def display_board(self, board: chess.Board, highlight_last_move: bool = True):
        """
        Print the board with ranks 8..1. If highlight_last_move is True, color:
          - The destination square piece (last move) in GREEN
          - The origin square (now usually empty) in YELLOW
        """
        last_from = last_to = None
        if highlight_last_move and board.move_stack:
            try:
                last_move = board.peek()
                last_from = last_move.from_square
                last_to = last_move.to_square
            except Exception:
                last_from = last_to = None

        print()
        print("   a b c d e f g h")
        print(" ---------------------")
        for rank in range(8, 0, -1):
            row_cells = []
            for file in range(1, 9):
                square = chess.square(file - 1, rank - 1)
                piece = board.piece_at(square)
                text = piece.symbol() if piece else '.'

                if square == last_to and piece:
                    # Moved piece destination
                    text = f"{GREEN}{text}{ENDC}"
                elif square == last_from:
                    # Origin square (now empty or captured-from)
                    # Keep '.' but color it; if a piece somehow still there, color anyway
                    text = f"{YELLOW}{text}{ENDC}"

                row_cells.append(text)
            row = " ".join(row_cells)
            print(f"{rank}| {row} |{rank}")
        print(" ---------------------")
        print("   a b c d e f g h")
        print()

    def display_turn_message(self, game):
        cur = game.get_current_player()
        turn_color = "White" if game.board.turn else "Black"
        msg = f"Move {game.board.fullmove_number} ({turn_color}): {cur.model_name} is thinking..."
        # show turn message as cyan title to stand out
        print(f"{CYAN}{msg}{ENDC}")

    def display_game_over_message(self, game):
        result = game.get_game_result()
        title = self._color_title("--- Game Over ---")
        print(title)
        print(f"Result: {result}")
        self.display_board(game.board)

    def display_ask_expert_menu(self):
        """Show the Ask the Chessmaster menu with a colored title and return the user's choice."""
        title = self._color_title("--- Ask the Chessmaster ---")
        print(title)
        print(f"  {WHITE}1:{ENDC} {CYAN}Ask a chess question{ENDC}")
        print(f"  {WHITE}2:{ENDC} {CYAN}Tell me a chess joke{ENDC}")
        print(f"  {WHITE}3:{ENDC} {CYAN}Tell me some chess news{ENDC}")
        print(f"  {WHITE}m:{ENDC} {CYAN}Return to previous menu{ENDC}")
        return self.get_user_input("Enter choice: ")

    def get_human_quit_choice(self) -> str:
        """Ask a human player how they want to quit: resign, save & quit, quit without saving, or cancel."""
        title = self._color_title("--- Quit Options ---")
        print(title)
        print(f"  {WHITE}r:{ENDC} {CYAN}Resign the game{ENDC}")
        print(f"  {WHITE}s:{ENDC} {CYAN}Save and quit{ENDC}")
        print(f"  {WHITE}q:{ENDC} {CYAN}Quit without saving{ENDC}")
        print(f"  {WHITE}c:{ENDC} {CYAN}Cancel and return to game{ENDC}")
        return self.get_user_input("Enter your choice [r/s/q/c]: ").strip().lower()

    def prompt_for_move(self, game) -> str:
        """
        Display a colored move prompt and return the user's input.
        Sections (colored):
          1) "Move X (Name as Side):"            -> WHITE
          2) " Enter your move (e.g. e2e4),"     -> CYAN
          3) " 'q' to quit, or 'm' for menu: "   -> YELLOW
        """
        board = game.board
        player = game.get_current_player()
        side = "White" if board.turn else "Black"
        section1 = f"Move {board.fullmove_number} ({player.model_name} as {side}):"
        section2 = " Enter your move (e.g. e2e4),"
        section3 = " 'q' to quit, or 'm' for menu: "
        prompt = f"{WHITE}{section1}{ENDC}{CYAN}{section2}{ENDC}{YELLOW}{section3}{ENDC}"
        return self.get_user_input(prompt)