from game import BLUE, GREEN, RED, ENDC
import chess
import textwrap

class UIManager:
    """Simple console UI helper. Menu titles are shown in color."""

    @staticmethod
    def _color_title(title: str) -> str:
        return f"{BLUE}{title}{ENDC}"

    @staticmethod
    def display_message(msg: str = "") -> None:
        print(msg)

    @staticmethod
    def get_user_input(prompt: str = "") -> str:
        try:
            return input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            return ""

    def display_main_menu(self) -> str:
        title = self._color_title("--- Main Menu ---")
        print(title)
        print("  1: Play a New Game")
        print("  2: Load a Saved Game")
        print("  3: Load a Practice Position")
        print("  4: View Player Stats")
        print("  5: Fun Chess Fact from the Chessmaster")
        print("  ?: Ask a Chess Expert")
        print("  q: Quit")
        return self.get_user_input("Enter your choice: ")

    def display_in_game_menu(self) -> str:
        title = self._color_title("--- In-Game Menu ---")
        print(title)
        print("  l: Load Saved Game")
        print("  p: Load Practice Position")
        print("  s: Save Game")
        print("  r: Return to Game")
        print("  q: Quit Application")
        print("  ?<question>: Ask Chess Expert (prefix with '?')")
        return self.get_user_input("Enter choice: ")

    def display_saved_games_and_get_choice(self, summaries):
        title = self._color_title("--- Saved Games ---")
        print(title)
        if not summaries:
            print("  (none)")
            return 'm'

        # Be tolerant of multiple summary formats (dicts with different keys, or simple strings)
        for i, s in enumerate(summaries, start=1):
            display = None
            if isinstance(s, dict):
                # common explicit display keys
                display = s.get('display') or s.get('summary') or s.get('title') or s.get('name')

                if not display:
                    # try to compose a useful line from available fields
                    filename = s.get('filename') or s.get('file') or ''
                    date = s.get('date') or s.get('timestamp') or s.get('created') or ''
                    white = s.get('white') or s.get('white_name') or s.get('white_player') or ''
                    black = s.get('black') or s.get('black_name') or s.get('black_player') or ''
                    status = s.get('status') or s.get('last_move') or s.get('status_text') or ''
                    parts = [p for p in (date, white and f"White: {white}", black and f"Black: {black}", status) if p]
                    if parts:
                        display = " | ".join(parts)
                    else:
                        display = filename or str(s)
            else:
                # fallback for non-dict summary entries
                display = str(s)

            print(f"  {i}: {display}")

        print("  m: Return to Main Menu")
        print("  q: Quit Application")
        choice = self.get_user_input("Enter the number of the game to load, or a letter for other options: ")
        if choice.lower() in ['m', 'q']:
            return choice.lower()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(summaries):
                return
        except Exception:
            pass
        return None

    def display_practice_positions_and_get_choice(self, positions):
        title = self._color_title("--- Practice Positions ---")
        print(title)
        for i, p in enumerate(positions, start=1):
            print(f"  {i}: {p.get('name','Unknown')}  ({p.get('fen','')})")
        print("  m: Return to Main Menu")
        print("  q: Quit Application")
        print("  ?<question>: Ask Chess Expert")
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
        print("Available AI models:")
        for k, v in ai_models.items():
            print(f"  {k}: {v}")
        print("Available Stockfish configs:")
        for k, v in stockfish_configs.items():
            print(f"  {k}: Stockfish - {v.get('name')}")
        print("  hu: Human Player")
        choice = self.get_user_input("Enter choice for White and Black players (e.g., 'm1s2'): ")
        # accept combined like 'm1s2' or 'm1 s2'
        parts = choice.replace(" ", "")
        if len(parts) >= 4:
            return parts[:2], parts[2:4]
        return None, None

    def display_setup_menu_and_get_choices(self, white_openings, black_defenses, ai_models, stockfish_configs):
        title = self._color_title("--- Setup New Game ---")
        print(title)
        # Simplified setup flow
        print("Choose white opening (enter key or leave blank for default):")
        for k, v in white_openings.items():
            print(f"  {k}: {v}")
        white_opening = self.get_user_input("White opening key: ") or list(white_openings.keys())[0] if white_openings else ""
        print("Choose black defense (enter key or leave blank for default):")
        for k, v in black_defenses.items():
            print(f"  {k}: {v}")
        black_defense = self.get_user_input("Black defense key: ") or list(black_defenses.keys())[0] if black_defenses else ""
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

    def display_board(self, board: chess.Board):
        # Minimal ascii board
        ranks = []
        for r in range(8, 0, -1):
            row = []
            for f in range(1, 9):
                square = chess.square(f-1, r-1)
                piece = board.piece_at(square)
                row.append(piece.symbol() if piece else '.')
            ranks.append(" ".join(row))
        print()
        print("  a b c d e f g h")
        print(" -----------------")
        for i, row in enumerate(ranks, start=8):
            print(f"{9-i}| {row} |{9-i}")
        print(" -----------------")
        print("  a b c d e f g h")
        print()

    def display_turn_message(self, game):
        cur = game.get_current_player()
        turn_color = "White" if game.board.turn else "Black"
        msg = f"{turn_color}'s turn ({cur.model_name}), move {game.board.fullmove_number}."
        if game.is_game_over():
            result = game.get_game_result()
            msg += f" Game over: {result}"
        self.display_message(msg)

    def display_game_over_message(self, game):
        result = game.get_game_result()
        title = self._color_title("--- Game Over ---")
        print(title)
        print(f"Result: {result}")
        self.display_board(game.board)