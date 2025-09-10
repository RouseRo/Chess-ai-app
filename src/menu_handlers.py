class MenuHandlers:
    def __init__(self, ui):
        self.ui = ui

    def display_main_menu(self):
        print("\n--- Main Menu ---", flush=True)
        print("  1: Play a New Game", flush=True)
        print("  2: Load a Saved Game", flush=True)
        print("  3: Load a Practice Position", flush=True)
        print("  4: View Player Stats", flush=True)
        print("  ?: Ask a Chess Expert", flush=True)
        print("  q: Quit", flush=True)
        print("Enter your choice: ", end="", flush=True)
        return input().strip().lower()