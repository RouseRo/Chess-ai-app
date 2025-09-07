# tests/test_basic.py
import pytest
import sys
from pexpect.popen_spawn import PopenSpawn
import re
import time

# Command to run the application as a module
PY_CMD = [sys.executable, "-u", "-m", "src.main"]

def test_basic_functionality():
    """A simple test to verify pytest is working correctly."""
    assert True

@pytest.mark.unit
def test_with_unit_marker():
    """A test with the 'unit' marker to demonstrate marker usage."""
    assert 1 + 1 == 2

@pytest.mark.integration
def test_main_menu_new_game_flow():
    """Test the flow of starting a new game from the main menu"""
    # On Windows, use PopenSpawn which is more reliable
    child = PopenSpawn(PY_CMD, encoding='utf-8', timeout=30)

    try:
        # Wait for the main menu
        child.expect(r"--- Main Menu ---")
        child.expect(r"Enter your choice")
        
        # Select option '1' for new game
        child.sendline('1')
        
        # Verify the setup menu appears
        child.expect(r"--- Setup New Game ---")
        child.expect(r"Choose player models for White and Black")
        
        # Verify the player model selection menu appears
        child.expect(r"--- Choose Player Models ---")
        child.expect(r"Available AI models")
        child.expect(r"Available Stockfish configs")
        child.expect(r"Enter choice for White and Black players")
        
        # Select "Human vs Stockfish (Balanced)"
        child.sendline('hus2')
        
        # Verify human player message
        child.expect(r"Human player selected for White - no opening strategy will be used")
        
        # Verify the black defense options
        child.expect(r"Choose black defense")
        
        # Select "Sicilian Defense"
        child.sendline('a')
        
        # Verify name prompt and skip by pressing Enter
        child.expect(r"Enter name for White player")
        child.sendline('')

        # Wait for the game to start and display the initial board
        child.expect(r"--- Game Started ---")
        child.expect(r"White: Human")
        child.expect(r"Black: Stockfish")
        child.expect(r"8\| r n b q k b n r \|8")
        
        # Updated pattern to match the full prompt including additional instructions
        child.expect(r"Move 1 \(Human .* as White\): Enter your move.*")
        
        # Quit the game
        child.sendline('q')
        child.expect(r"--- Quit Options ---")
        child.sendline('q')
        
    except Exception as e:
        print(f"\nError: {e}")
        print(f"Last output: {child.before}")
        assert False, f"Test failed: {e}"
        
    finally:
        # Clean up if the process is still running
        if child.proc.poll() is None:
            child.proc.terminate()