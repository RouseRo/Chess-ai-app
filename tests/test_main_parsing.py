import pytest
from src.data_models import GameHeader

# The 'app_instance' fixture is now automatically provided by conftest.py

def test_parse_log_header_success(app_instance):
    """Tests that a valid log header is parsed correctly into a GameHeader."""
    log_lines = [
        '2025-09-08 10:11:58,535 - White: Player 1',
        '2025-09-08 10:11:58,535 - Black: Player 2',
        '2025-09-08 10:11:58,536 - White Player Key: hu',  # Updated format
        '2025-09-08 10:11:58,536 - Black Player Key: s1',  # Updated format
        '2025-09-08 10:11:58,536 - Result: 1-0'
    ]
    all_keys = ['hu', 's1', 'm1']

    header, error = app_instance.parse_log_header(log_lines, all_keys)

    assert error is None
    assert header is not None
    assert header.white_name == "Player 1"
    assert header.black_name == "Player 2"
    assert header.white_key == "hu"
    assert header.black_key == "s1"
    assert header.result == "1-0"

def test_parse_log_header_invalid_player_key(app_instance):
    """Tests that parsing fails if a player key is not in the allowed list."""
    log_lines = [
        '2025-09-08 10:11:58,535 - White: Player 1',
        '2025-09-08 10:11:58,535 - Black: Player 2',
        '2025-09-08 10:11:58,536 - White Player Key: hu',
        '2025-09-08 10:11:58,536 - Black Player Key: s99',  # s99 is not a valid key
    ]
    all_keys = ['hu', 's1', 'm1']

    header, error = app_instance.parse_log_header(log_lines, all_keys)

    assert header is None
    assert "Player key in log is not in current config" in error