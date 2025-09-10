RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
ENDC = "\033[0m"

class MenuHandlers:
    def __init__(self, ui):
        self.ui = ui

    def display_main_menu(self):
        print(f"\n{CYAN}--- Main Menu ---{ENDC}", flush=True)
        print(f"  {GREEN}1{ENDC}: Play a New Game", flush=True)
        print(f"  {GREEN}2{ENDC}: Load a Saved Game", flush=True)
        print(f"  {GREEN}3{ENDC}: Load a Practice Position", flush=True)
        print(f"  {YELLOW}4{ENDC}: View Player Stats", flush=True)
        print(f"  {CYAN}?{ENDC}: Ask a Chess Expert", flush=True)
        print(f"  {RED}q{ENDC}: Quit", flush=True)
        print(f"{YELLOW}Enter your choice:{ENDC} ", end="", flush=True)
        return input().strip().lower()