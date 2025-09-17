import json
from src.data_models import PlayerStats, stats_to_dict
from src.game import BLUE, CYAN, GREEN, YELLOW, RED, WHITE, ENDC, MAGENTA, BOLD  # <-- Import color constants

PLAYER_STATS_FILE = 'logs/player_stats.json'

class PlayerStatsManager:
    def __init__(self, ui, file_manager):
        self.ui = ui
        self.file_manager = file_manager
        self.player_stats = {}

    def load_player_stats(self):
        """Loads player statistics from a JSON file into PlayerStats objects."""
        try:
            with open(PLAYER_STATS_FILE, 'r') as f:
                stats_data = json.load(f)
                self.player_stats = {name: PlayerStats(**data) for name, data in stats_data.items()}
        except (FileNotFoundError, json.JSONDecodeError):
            self.player_stats = {}

    def save_player_stats(self):
        """Saves player statistics to a JSON file."""
        with open(PLAYER_STATS_FILE, 'w') as f:
            json.dump(stats_to_dict(self.player_stats), f, indent=4)

    def update_player_stats(self, game):
        """Updates player stats based on the game result."""
        import chess
        result = game.board.result()
        white_name = game.players[chess.WHITE].model_name
        black_name = game.players[chess.BLACK].model_name

        self.player_stats.setdefault(white_name, PlayerStats())
        self.player_stats.setdefault(black_name, PlayerStats())

        if result == "1-0":
            self.player_stats[white_name].wins += 1
            self.player_stats[black_name].losses += 1
        elif result == "0-1":
            self.player_stats[black_name].wins += 1
            self.player_stats[white_name].losses += 1
        else:
            self.player_stats[white_name].draws += 1
            self.player_stats[black_name].draws += 1
        self.save_player_stats()

    def view_player_stats(self):
        """Loads and displays player statistics."""
        self.load_player_stats()
        # Print section header before displaying stats, with color
        print(f"\n{CYAN}--- Player Statistics ---{ENDC}")
        # Convert PlayerStats objects to dicts for UI
        stats_dict = {name: v.__dict__ for name, v in self.player_stats.items()}
        self.ui.display_player_stats(stats_dict)
