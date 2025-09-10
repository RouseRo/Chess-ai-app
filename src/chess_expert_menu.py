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
        self.display_chess_expert_menu()
        choice = input().strip().lower()
        if choice == '1':
            self.expert_service.analyze_position()
        elif choice == '2':
            self.expert_service.opening_advice()
        elif choice == '3':
            self.expert_service.tactical_puzzle()
        elif choice == '4':
            self.show_fun_chess_fact()
        elif choice == 'b':
            return
        else:
            print("Invalid choice. Please try again.", flush=True)

    def show_fun_chess_fact(self):
        # Example implementation, replace with your actual logic
        print("\nDid you know? The longest chess game theoretically possible is 5,949 moves!", flush=True)