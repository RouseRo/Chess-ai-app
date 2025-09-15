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
        print("  m: Back to main menu", flush=True)
        print("Enter your choice: ", end="", flush=True)

    def handle_chess_expert_menu(self, direct_question=None):
        """
        Display the Chessmaster menu and handle user choices.
        If direct_question is provided, treat it as a chess question.
        """
        while True:
            self.ui.display_message(
                "--- Ask the Chessmaster ---\n"
                "  1: Analyze a position\n"
                "  2: Ask a chess question\n"
                "  3: Get a tactical puzzle\n"
                "  4: Tell me a fun chess fact\n"
                "  5: Tell me a chess joke\n"
                "  m: Back to main menu"
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
            elif choice == 'm':
                break
            else:
                # Treat any other input as a chess question
                self.expert_service.ask_chess_question(choice)
                break

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