from dataclasses import dataclass, asdict
from typing import Optional
from enum import Enum, auto

@dataclass
class PlayerStats:
    """Represents the win/loss/draw statistics for a player."""
    wins: int = 0
    losses: int = 0
    draws: int = 0

@dataclass
class GameHeader:
    """Represents the metadata parsed from a game log file."""
    white_name: str
    black_name: str
    white_key: str
    black_key: str
    white_strategy: Optional[str] = None
    black_strategy: Optional[str] = None
    result: Optional[str] = None
    termination: Optional[str] = None
    date: Optional[str] = None

def stats_to_dict(stats_data):
    """Converts a dictionary of PlayerStats objects to a JSON-serializable dictionary."""
    return {name: asdict(stats) for name, stats in stats_data.items()}

class GameLoopAction:
    CONTINUE = "continue"
    SKIP_TURN = "skip_turn"
    QUIT_APPLICATION = "quit_application"
    RETURN_TO_MENU = "return_to_menu"
    IN_GAME_MENU = "in_game_menu"