import chess
from src.game import BLUE, CYAN, GREEN, YELLOW, RED, WHITE, ENDC, MAGENTA, BOLD

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
        result = input(f"{YELLOW}{prompt}{ENDC}").strip()
        return result

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
        print(f"\n  {WHITE}q:{ENDC} {CYAN}Quit Application{ENDC}")
        print(f"  {WHITE}m:{ENDC} {CYAN}Return to Main Menu{ENDC}")
        print(f"  {WHITE}Enter:{ENDC} {CYAN}Return to Load a Practice Position{ENDC}")
        choice = self.get_user_input("Enter choice for White and Black players (e.g., 'm1s2'), or press Enter to return: ")
        if choice == "":
            # treat Enter (empty input) as "return to Load a Practice Position" by returning two None values
            return None, None
        if choice.lower() == "q":
            # treat 'q' as quit application
            return "q", "q"
        if choice.lower() == "m":
            # treat 'm' as return to main menu
            return "m", "m"
        parts = choice.replace(" ", "")
        if len(parts) >= 4:
            return parts[:2], parts[2:4]
        return None, None

    def display_setup_menu_and_get_choices(self, white_openings, black_defenses, ai_models, stockfish_configs):
        title = self._color_title("--- Setup New Game ---")
        print(title)
        
        # First, select AI models for White and Black
        print(f"{CYAN}Choose player models for White and Black:{ENDC}")
        white_key, black_key = self.display_model_menu_and_get_choice(ai_models, stockfish_configs)
        if not white_key or not black_key:
            return None
        
        # Default values for openings/defenses - empty string means "No Classic opening or defense"
        white_opening = ""
        black_defense = ""
        
        # --- Prompt for opening/defense as a single input with color ---
        opening_defense_prompt = (
            f"{WHITE}White openings:{ENDC}\n"
            f"{YELLOW}  0:{ENDC} No Classic Chess Opening\n"
            f"{YELLOW}  1:{ENDC} Play the Ruy Lopez.\n"
            f"{YELLOW}  2:{ENDC} Play the Italian Game.\n"
            f"{YELLOW}  3:{ENDC} Play the Queen's Gambit.\n"
            f"{YELLOW}  4:{ENDC} Play the London System.\n"
            f"{YELLOW}  5:{ENDC} Play the King's Gambit.\n"
            f"{WHITE}Black defenses:{ENDC}\n"
            f"{MAGENTA}  a:{ENDC} Play the Sicilian Defense.\n"
            f"{MAGENTA}  b:{ENDC} Play the French Defense.\n"
            f"{MAGENTA}  c:{ENDC} Play the Caro-Kann Defense.\n"
            f"{MAGENTA}  z:{ENDC} No Classic Chess Defense\n"
            f"{CYAN}Enter white opening and black defense as a single input (e.g., '{YELLOW}1{ENDC}{MAGENTA}a{ENDC}'){CYAN},{ENDC}\n"
            f"{GREEN}or press Enter to use defaults:{ENDC} "
        )
        opening_defense = self.get_user_input(opening_defense_prompt).strip().lower()

        # Parse input like "1a"
        if opening_defense and len(opening_defense) >= 2:
            white_opening = opening_defense[0]
            black_defense = opening_defense[1]
        else:
            white_opening = ""
            black_defense = ""

        return white_opening, black_defense, white_key, black_key

    def display_player_stats(self, stats):
        print(f"{BOLD}{'Player':<33} | {GREEN}Wins{ENDC:^6} | {RED}Losses{ENDC:^5}| {YELLOW}Draws{ENDC:^7}{ENDC}", flush=True)
        print(f"{'-'*33} | {'-'*6} | {'-'*6} | {'-'*7}", flush=True)
        for name, stat in stats.items():
            print(f"{name:<33} | {GREEN}{stat['wins']:^6}{ENDC} | {RED}{stat['losses']:^6}{ENDC} | {YELLOW}{stat['draws']:^7}{ENDC}")
        # Remove the "Press Enter to return to the main menu." prompt
        # print(f"{YELLOW}Press Enter to return to the main menu.{ENDC}", flush=True)

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
        move = self.get_user_input(prompt)

        # Handle special commands 'q' and 'm'
        if move.lower() == 'q':
            return 'q'
        if move.lower() == 'm':
            return 'm'
        return move

    def display_board_from_fen(self, fen):
        """Display a chess board for a given FEN string."""
        board = chess.Board(fen)
        self.display_board(board)

    def display_board_with_description(self, fen, description):
        board = chess.Board(fen)
        board_lines = str(board).split('\n')
        desc_lines = description.split('\n')
        max_lines = max(len(board_lines), len(desc_lines))
        board_pad = 22  # Adjust for your board width

        print()
        for i in range(max_lines):
            board_part = board_lines[i] if i < len(board_lines) else ' ' * board_pad
            desc_part = desc_lines[i] if i < len(desc_lines) else ''
            print(f"{board_part:<{board_pad}}   {desc_part}")
        print()