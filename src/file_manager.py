import os
import glob
import shutil
import json
import re
import logging
from datetime import datetime
from game import RED, ENDC

PLAYER_STATS_FILE = 'logs/player_stats.json'

class FileManager:
    """Handles all file operations: saving/loading games and player stats."""

    def __init__(self, ui_manager):
        self.ui = ui_manager

    def get_saved_game_summaries(self):
        """Parses all saved game logs to create a list of summaries."""
        summaries = []
        saved_games = sorted(glob.glob('chess_game_*.log'), reverse=True)

        for log_file in saved_games:
            summary = {'filename': log_file, 'white': 'N/A', 'black': 'N/A', 'date': 'N/A', 'status': 'In Progress'}
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                
                match = re.search(r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})', log_file)
                if match:
                    summary['date'] = f"{match.group(1)}-{match.group(2)}-{match.group(3)} {match.group(4)}:{match.group(5)}"

                move_count = 0
                status = "In Progress"
                for line in lines:
                    if "White:" in line:
                        summary['white'] = line.split("White:", 1)[1].strip()
                    elif "Black:" in line:
                        summary['black'] = line.split("Black:", 1)[1].strip()
                    elif "Game Over" in line or "resigned" in line:
                        status = 'Finished'
                    
                    if "Move:" in line:
                        move_count += 1
                
                summary['status'] = f"{status} ({move_count})"
                summaries.append(summary)
            except Exception as e:
                self.ui.display_message(f"\n{RED}Warning: Could not parse '{log_file}'. Error: {e}{ENDC}")
                continue
        return summaries

    def save_game_log(self):
        """Saves the current game log to a timestamped file."""
        try:
            for handler in logging.getLogger().handlers:
                handler.flush()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f'chess_game_{timestamp}.log'
            shutil.copy('chess_game.log', save_path)
            self.ui.display_message(f"\nGame saved as {save_path}")
        except FileNotFoundError:
            self.ui.display_message("Log file not found, could not save.")
        except Exception as e:
            self.ui.display_message(f"An error occurred while saving: {e}")

    def load_player_stats(self):
        """Loads player statistics from the JSON file."""
        if not os.path.exists(PLAYER_STATS_FILE):
            return {}
        try:
            with open(PLAYER_STATS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def save_player_stats(self, stats):
        """Saves player statistics to the JSON file."""
        os.makedirs(os.path.dirname(PLAYER_STATS_FILE), exist_ok=True)
        with open(PLAYER_STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)