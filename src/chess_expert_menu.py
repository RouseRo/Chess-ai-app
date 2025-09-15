class ChessExpertMenu:
    def __init__(self, ui, expert_service):
        self.ui = ui
        self.expert_service = expert_service

    def display_chess_expert_menu(self):
        print("\n--- Ask the Chessmaster ---", flush=True)
        print("  1: Analyze a position", flush=True)
        print("  2: Ask for opening advice", flush=True)
        print("  3: Get a tactical puzzle", flush=True)
        print("  4: Tell me a fun chess fact", flush=True)
        print("  b: Back to main menu", flush=True)
        print("Enter your choice: ", end="", flush=True)

    def handle_chess_expert_menu(self):
        while True:
            self.ui.display_message(
                "--- Ask the Chessmaster ---\n"
                "  1: Analyze a position\n"
                "  2: Ask a chess question\n"
                "  3: Get a tactical puzzle\n"
                "  4: Tell me a fun chess fact\n"
                "  b: Back to main menu"
            )
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
                # Implement or call your tactical puzzle method here
                pass
            elif choice == '4':
                self.expert_service.get_fun_fact()
            elif choice == 'b':
                break
            else:
                self.ui.display_message("Invalid choice. Please try again.")

    def show_fun_chess_fact(self):
        # Example implementation, replace with your actual logic
        print("\nDid you know? The longest chess game theoretically possible is 5,949 moves!", flush=True)