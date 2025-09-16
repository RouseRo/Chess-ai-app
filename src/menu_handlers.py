RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
ENDC = "\033[0m"

class MenuHandlers:
    def __init__(self, ui, chess_expert_menu):
        self.ui = ui
        self.chess_expert_menu = chess_expert_menu

    def display_main_menu(self):
        print(f"\n{CYAN}--- Main Menu ---{ENDC}", flush=True)
        print(f"  {GREEN}1{ENDC}: Play a New Game", flush=True)
        print(f"  {GREEN}2{ENDC}: Load a Saved Game", flush=True)
        print(f"  {GREEN}3{ENDC}: Load a Practice Position", flush=True)
        print(f"  {YELLOW}4{ENDC}: View Player Stats", flush=True)
        print(f"  {CYAN}?{ENDC}: Ask a Chess Expert", flush=True)
        print(f"  {RED}q{ENDC}: Quit", flush=True)
        user_input = input(f"{YELLOW}Enter your choice: {ENDC}").strip()
        if user_input.startswith('?'):
            question = user_input[1:].strip()
            self.chess_expert_menu.handle_chess_expert_menu(direct_question=question)
        else:
            return user_input.lower()