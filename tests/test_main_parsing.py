import pytest
from src.data_models import GameHeader

# The 'app_instance' fixture is now automatically provided by conftest.py

def test_parse_log_header_success(app_instance):
    """Tests that a valid log header is parsed correctly into a GameHeader."""
    log_lines = [
        '[White "Player 1"]',
        '[Black "Player 2"]',
        '[White_Key "hu"]',
        '[Black_Key "s1"]',
        '[Result "1-0"]'
    ]
    all_keys = ['hu', 's1', 'm1']
    
    header, error = app_instance.parse_log_header(log_lines, all_keys)
    
    assert error is None
    assert isinstance(header, GameHeader)
    assert header.white_name == "Player 1"
    assert header.black_key == "s1"
    assert header.result == "1-0"

def test_parse_log_header_missing_key(app_instance):
    """Tests that parsing fails if a required key is missing."""
    log_lines = [
        '[White "Player 1"]',
        # Black key is missing
        '[White_Key "hu"]',
    ]
    all_keys = ['hu', 's1']
    
    header, error = app_instance.parse_log_header(log_lines, all_keys)
    
    assert header is None
    assert "missing required tags" in error

def test_parse_log_header_invalid_player_key(app_instance):
    """Tests that parsing fails if a player key is not in the allowed list."""
    log_lines = [
        '[White "Player 1"]',
        '[Black "Player 2"]',
        '[White_Key "hu"]',
        '[Black_Key "s99"]', # s99 is not a valid key
    ]
    all_keys = ['hu', 's1', 'm1']
    
    header, error = app_instance.parse_log_header(log_lines, all_keys)
    
    assert header is None
    assert "Player key in log is not in current config" in error