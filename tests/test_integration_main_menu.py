import sys
import pytest
import pexpect
from pexpect.popen_spawn import PopenSpawn
import re
import time

# Command to run the application as a module, with unbuffered output (-u)
PY_CMD = [sys.executable, "-u", "-m", "src.main"]

# Regex to strip ANSI color codes from the output for easier matching
ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def clean_output(text: str) -> str:
    """Removes ANSI color codes from a string."""
    return ANSI_ESCAPE_RE.sub('', text)

def expect_with_debug(child, pattern, timeout=None):
    """Helper function to expect a pattern with debug output on failure"""
    try:
        return child.expect(pattern, timeout=timeout)
    except pexpect.TIMEOUT:
        # Print the actual buffer content to help debug what's being received
        print(f"\nTIMEOUT waiting for: {pattern}")
        print(f"Current buffer content:\n{child.before}")
        raise

@pytest.mark.integration
def test_main_menu_loads_and_quits():
    """
    Tests if the application starts, displays the main menu, and quits successfully.
    """
    # On Windows, use PopenSpawn which is more reliable
    child = PopenSpawn(PY_CMD, encoding='utf-8', timeout=15)  # Increased timeout

    try:
        # Wait for the main menu to appear - this pattern is more lenient
        expect_with_debug(child, r"--- Main Menu ---")
        
        # Wait for prompt, without checking specific menu items
        expect_with_debug(child, r"Enter your choice")
        
        # Send the 'q' command to quit
        child.sendline('q')
        
        # Expect the exit message
        expect_with_debug(child, r"Exiting application")
        
        # Wait for the process to terminate (up to 5 seconds)
        for _ in range(50):  # 50 * 0.1 = 5 seconds
            if child.proc.poll() is not None:
                break
            time.sleep(0.1)
        
        # Check that the process has terminated
        assert child.proc.poll() is not None, "Child process should have terminated."

    finally:
        # Clean up if the process is still running
        if child.proc.poll() is None:
            child.proc.terminate()

@pytest.mark.integration
def test_main_menu_player_stats_flow():
    """
    Tests the flow of selecting 'View Player Stats' and returning to the menu.
    """
    child = PopenSpawn(PY_CMD, encoding='utf-8', timeout=15)  # Increased timeout

    try:
        # Wait for the main menu
        expect_with_debug(child, r"--- Main Menu ---")
        expect_with_debug(child, r"Enter your choice")
        
        # Select option '4' for player stats
        child.sendline('4')
        
        # Wait for the stats screen to appear
        expect_with_debug(child, r"--- Player Statistics ---")
        expect_with_debug(child, r"Player\s+\|\s+Wins\s+\|\s+Losses\s+\|\s+Draws")  # Added child parameter
        expect_with_debug(child, r"-+")  # Added child parameter
        expect_with_debug(child, r"Human Player")  # Added child parameter
        expect_with_debug(child, r"Press Enter to return to the main menu")  # Added child parameter
        
        # Press Enter to go back
        child.sendline('')
        
        # Expect to be back at the main menu
        expect_with_debug(child, r"--- Main Menu ---")
        expect_with_debug(child, r"Enter your choice")
        
        # Clean up by quitting
        child.sendline('q')
        expect_with_debug(child, r"Exiting application")

    finally:
        if child.proc.poll() is None:
            child.proc.terminate()

@pytest.mark.integration
def test_main_menu_chess_expert_flow():
    """
    Tests the flow of selecting 'Ask a Chess Expert' and verifying the submenu appears.
    """
    child = PopenSpawn(PY_CMD, encoding='utf-8', timeout=15)

    try:
        # Wait for the main menu
        expect_with_debug(child, r"--- Main Menu ---")
        expect_with_debug(child, r"Enter your choice")
        
        # Select option '?' for Ask a Chess Expert
        child.sendline('?')
        
        # Verify that the Chessmaster menu appears
        expect_with_debug(child, r"--- Ask the Chessmaster ---")
        
        # Go back to the main menu
        child.sendline('b')
        
        # Expect to be back at the main menu
        expect_with_debug(child, r"--- Main Menu ---")
        expect_with_debug(child, r"Enter your choice")
        
        # Clean up by quitting
        child.sendline('q')
        expect_with_debug(child, r"Exiting application")

    finally:
        if child.proc.poll() is None:
            child.proc.terminate()

@pytest.mark.integration
def test_main_menu_new_game_flow():
    """
    Tests the flow of selecting 'Play a New Game', setting up players, making moves,
    and saving the game.
    """
    child = PopenSpawn(PY_CMD, encoding='utf-8', timeout=20)  # Longer timeout for game setup and AI moves

    try:
        # Wait for the main menu
        expect_with_debug(child, r"--- Main Menu ---")
        expect_with_debug(child, r"Enter your choice")
        
        # Select option '1' for new game
        child.sendline('1')
        
        # Verify the setup menu appears
        expect_with_debug(child, r"--- Setup New Game ---")
        expect_with_debug(child, r"Choose player models for White and Black")
        
        # Verify the player model selection menu appears
        expect_with_debug(child, r"--- Choose Player Models ---")
        expect_with_debug(child, r"Available AI models")
        expect_with_debug(child, r"Available Stockfish configs")
        expect_with_debug(child, r"Enter choice for White and Black players")
        
        # Select "Human vs Stockfish (Balanced)"
        child.sendline('hus2')
        
        # Verify human player message
        expect_with_debug(child, r"Human player selected for White - no opening strategy will be used")
        
        # Verify the black defense options
        expect_with_debug(child, r"Choose black defense")
        
        # Select "Sicilian Defense"
        child.sendline('a')
        
        # Verify name prompt and skip by pressing Enter
        expect_with_debug(child, r"Enter name for White player")
        child.sendline('')
        
        # Verify game starts
        expect_with_debug(child, r"--- Game Started ---")
        expect_with_debug(child, r"White: Human")
        expect_with_debug(child, r"Black: Stockfish")
        
        # Verify initial board is displayed
        expect_with_debug(child, r"8\| r n b q k b n r \|8")
        
        # Verify move prompt
        expect_with_debug(child, r"Move 1 \(Human .* as White\): Enter your move")
        
        # Make first move: e2e4
        child.sendline('e2e4')
        
        # Wait for Stockfish to respond with a move
        expect_with_debug(child, r"Move 1 \(Black\): Stockfish .* is thinking")
        
        # Verify the updated board after both moves
        expect_with_debug(child, r"Move 2 \(Human .* as White\): Enter your move")
        
        # Enter 'm' to access the in-game menu
        child.sendline('m')
        
        # Verify the in-game menu appears
        expect_with_debug(child, r"--- In-Game Menu ---")
        
        # Select 'q' to quit
        child.sendline('q')
        
        # Verify the quit options menu
        expect_with_debug(child, r"--- Quit Options ---")
        
        # Choose 's' to save and quit
        child.sendline('s')
        
        # Verify the game was saved
        expect_with_debug(child, r"Game saved as")
        expect_with_debug(child, r"Game saved. Exiting application")
        
        # Wait for the process to terminate (up to 5 seconds)
        for _ in range(50):  # 50 * 0.1 = 5 seconds
            if child.proc.poll() is not None:
                break
            time.sleep(0.1)
        
        # Check that the process has terminated
        assert child.proc.poll() is not None, "Child process should have terminated."

    finally:
        if child.proc.poll() is None:
            child.proc.terminate()