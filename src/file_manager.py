import os
import json
import logging
import re
import shutil
from datetime import datetime, timezone

from src.game import RED, ENDC

class FileManager:
    """Handles file operations like saving/loading games and stats."""

    def __init__(self, ui):
        self.ui = ui
        self.logs_dir = "logs"
        self.games_dir = os.path.join(self.logs_dir, "games")
        os.makedirs(self.games_dir, exist_ok=True)

    def get_saved_game_summaries(self):
        """
        Scans the saved games directory and returns a list of summaries.
        Each summary is a dictionary containing filename and header info.
        """
        summaries = []
        for filename in os.listdir(self.games_dir):
            if filename.endswith(".log"):
                filepath = os.path.join(self.games_dir, filename)
                header_info = self._parse_log_header_for_summary(filepath)
                if header_info:
                    header_info['filename'] = filepath
                    summaries.append(header_info)
        
        # Sort by date, most recent first
        summaries.sort(key=lambda x: x.get('date', '0'), reverse=True)
        return summaries

    def _parse_log_header_for_summary(self, filepath):
        """
        A flexible parser to extract key info from a log file header.
        It handles two formats:
        1. PGN-style: [TagName "Value"]
        2. Simple: TagName: Value
        """
        header_data = {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for _ in range(15): # Read the first few lines
                    line = f.readline()
                    if not line:
                        break

                    # Try PGN-style format first: [White "Player"]
                    match = re.search(r"\[(\w+)\s+\"(.+?)\"\]", line)
                    if match:
                        key, value = match.groups()
                        header_data[key.lower()] = value
                        continue

                    # If not PGN, try simple format: White: Player
                    match = re.search(r"(\w+):\s+(.+)", line)
                    if match:
                        key, value = match.groups()
                        # Standardize keys to lowercase (e.g., "White Player Key" -> "white_player_key")
                        key = key.replace(' ', '_').lower()
                        header_data[key] = value

        except Exception:
            return None
        
        # Standardize player names from different possible keys
        if 'white' not in header_data and 'white_player' in header_data:
            header_data['white'] = header_data['white_player']
        if 'black' not in header_data and 'black_player' in header_data:
            header_data['black'] = header_data['black_player']

        if 'white' in header_data and 'black' in header_data:
            return header_data
        return None

    def save_game_log(self):
        """Saves the current game log to a timestamped file in the games directory."""
        if not os.path.exists('chess_game.log'):
            self.ui.display_message("No active game log to save.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_filename = f"chess_game_{timestamp}.log"
        dest_path = os.path.join(self.games_dir, dest_filename)

        try:
            # Ensure all buffered log messages are written to the file before copying
            logging.getLogger().handlers[0].flush()
            shutil.copy('chess_game.log', dest_path)
            self.ui.display_message(f"Game saved as {dest_path}")
        except Exception as e:
            self.ui.display_message(f"{RED}Failed to save game: {e}{ENDC}")