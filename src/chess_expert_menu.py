# Define color variables
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
ENDC = "\033[0m"

class ChessExpertMenu:
    def __init__(self, ui, expert_service):
        self.ui = ui
        self.expert_service = expert_service

    def display_chess_expert_menu(self):
        print("\n--- Ask the Chessmaster ---", flush=True)
        print("  1: Analyze a position", flush=True)
        print("  2: Ask a chess question", flush=True)
        print("  3: Get a tactical puzzle", flush=True)
        print("  4: Tell me a fun chess fact", flush=True)
        print("  5: Tell me a chess joke", flush=True)
        print("  6: Tell the latest chess news", flush=True)
        print("  m: Back to main menu", flush=True)
        print("Enter your choice: ", end="", flush=True)

    def handle_chess_expert_menu(self, direct_question=None):
        """
        Display the Chessmaster menu and handle user choices.
        If direct_question is provided, treat it as a chess question.
        """
        while True:
            self.ui.display_message(
                f"{CYAN}--- Ask the Chessmaster ---{ENDC}\n"
                f"  {GREEN}1{ENDC}: Analyze a position\n"
                f"  {GREEN}2{ENDC}: Ask a chess question\n"
                f"  {GREEN}3{ENDC}: Get a tactical puzzle\n"
                f"  {YELLOW}4{ENDC}: Tell me a fun chess fact\n"
                f"  {CYAN}5{ENDC}: Tell me a chess joke\n"
                f"  {GREEN}6{ENDC}: Tell the latest chess news\n"
                f"  {RED}m{ENDC}: Back to main menu"
            )

            # If a direct question was passed, treat it as a chess question (menu item 2)
            if direct_question:
                self.expert_service.ask_chess_question(direct_question)
                break

            choice = self.ui.get_user_input("Enter your choice: ").strip().lower()

            if choice == '1':
                fen = self.ui.get_user_input("Enter the FEN of the position to analyze: ").strip()
                if fen:
                    self.expert_service.analyze_position(fen)
                else:
                    self.ui.display_message("No FEN provided. Returning to menu.")
            elif choice == '2':
                self.expert_service.ask_chess_question()
            elif choice == '3':
                self.expert_service.get_tactical_puzzle()
            elif choice == '4':
                self.expert_service.get_fun_fact()
            elif choice == '5':
                joke_prompt = (
                    "Tell me a short chess joke. "
                    "Do not repeat jokes about pizza or feeding a family. "
                    "If possible, give a joke that hasn't been told before."
                )
                self.expert_service.ask_expert(joke_prompt)
            elif choice == '6':
                self.expert_service.get_latest_chess_news()
            elif choice == 'm':  # Changed back to 'm'
                break
            else:
                self.ui.display_message("Invalid choice. Please try again.")

    def show_fun_chess_fact(self):
        # Example implementation, replace with your actual logic
        print("\nDid you know? The longest chess game theoretically possible is 5,949 moves!", flush=True)

# The following code should be in your main application file (not in this module):
# from src.chess_expert_menu import ChessExpertMenu
# ui = ...  # Initialize your UIManager or equivalent
# expert_service = ...  # Initialize your ExpertService
# chess_expert_menu = ChessExpertMenu(ui, expert_service)
# user_input = input("Enter your choice: ").strip()
# if user_input.startswith('?'):
#     question = user_input[1:].strip()
#     chess_expert_menu.handle_chess_expert_menu(direct_question=question)
# else:
#     # ...existing menu handling...