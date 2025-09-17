"""
Integration tests for main menu flows in the Chess AI application.

Tested flows:
- Loading and quitting from the main menu
- Viewing player statistics and returning to the menu
- Accessing the Chess Expert submenu and returning
- Starting a new game and quitting
- Loading a practice position and quitting
- Loading a saved game and quitting

Test utilities:
- Uses pexpect to interact with the CLI application.
- Uses regex matching for output verification.
- Cleans up child processes after each test.

Environment:
- Sets CHESS_APP_TEST_MODE=1 for deterministic test behavior.
"""

import sys
import pytest
import pexpect
from pexpect.popen_spawn import PopenSpawn
import re
import time
import os
import shutil  # Add this import

# Command to run the application as a module, with unbuffered output (-u)
PY_CMD = [sys.executable, "-u", "-m", "src.main"]

# Regex to strip ANSI color codes from the output for easier matching
ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def clean_output(text: str) -> str:
    """Removes ANSI color codes from a string."""
    return ANSI_ESCAPE_RE.sub('', text)

def expect_with_debug(child, pattern, timeout=15):
    """Helper function to expect a pattern with debug output on failure"""
    try:
        return child.expect(pattern, timeout=timeout)
    except Exception as e:
        print(f"Error waiting for pattern: {pattern}")
        print(repr(child.before))
        raise

def _read_buffered_output(child, size=1000, timeout=2):
    """Read any buffered output to ensure we don't miss anything"""
    try:
        output = child.read_nonblocking(size=size, timeout=timeout)
        return output
    except:
        return None

def _terminate_process(child):
    """Ensure the process is terminated"""
    if child.proc.poll() is None:
        # Try graceful termination first
        try:
            child.sendintr()  # Send Ctrl+C
            time.sleep(0.5)
        except:
            pass
        
        # Force terminate if still running
        if child.proc.poll() is None:
            child.proc.terminate()
            time.sleep(0.5)
            if child.proc.poll() is None:
                child.proc.kill()

# Set up test environment
TEST_ENV = os.environ.copy()
TEST_ENV["CHESS_APP_TEST_MODE"] = "1"

@pytest.mark.integration
def test_main_menu_loads_and_quits():
    """
    Tests if the application starts, displays the main menu, and quits successfully.
    """
    # On Windows, use PopenSpawn which is more reliable
    child = PopenSpawn(PY_CMD, encoding='utf-8', timeout=15, env=TEST_ENV)  # Increased timeout

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
    child = PopenSpawn(PY_CMD, encoding='utf-8', timeout=15, env=TEST_ENV)  # Increased timeout

    try:
        # Wait for the main menu
        expect_with_debug(child, r"--- Main Menu ---")
        expect_with_debug(child, r"Enter your choice")
        
        # Select option '4' for player stats
        child.sendline('4')
        
        # Wait for the stats screen to appear
        expect_with_debug(child, r"--- Player Statistics ---")
        
        # No need to send Enter, it always returns to the main menu
        
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
    child = PopenSpawn(PY_CMD, encoding='utf-8', timeout=15, env=TEST_ENV)

    try:
        # 1. Wait for the main menu
        expect_with_debug(child, r"--- Main Menu ---")
        expect_with_debug(child, r"Enter your choice")

        # 2. Select option '?' for Ask a Chess Expert
        child.sendline('?')

        # 3. Verify that the Chessmaster menu appears
        expect_with_debug(child, r"--- Ask the Chessmaster ---")
        expect_with_debug(child, r"Enter your choice")

        # 4. Go back to the main menu by selecting 'm'
        child.sendline('m')

        # 5. Verify that the main menu reappears
        expect_with_debug(child, r"--- Main Menu ---")
        expect_with_debug(child, r"Enter your choice")

        # 6. Quit the application
        child.sendline('q')
        expect_with_debug(child, r"Exiting application")
    finally:
        # Ensure the process is terminated
        _terminate_process(child)

@pytest.mark.integration
def test_main_menu_new_game_flow():
    """Test the flow of starting a new game from the main menu

    This test verifies:
    1. Main menu loads correctly
    2. New game setup shows the appropriate options
    3. Player models are selected, and the game setup progresses
    4. Player can quit the game
    """
    child = PopenSpawn(PY_CMD, encoding='utf-8', timeout=30, env=TEST_ENV)
    child.delayafterread = 0.1

    try:
        # 1. Navigate through main menu
        expect_with_debug(child, r"--- Main Menu ---", timeout=10)
        expect_with_debug(child, r"Enter your choice", timeout=5)
        child.sendline('1')

        # 2. Setup new game
        expect_with_debug(child, r"--- Setup New Game ---", timeout=10)
        expect_with_debug(child, r"Choose player models for White and Black", timeout=5)
        expect_with_debug(child, r"--- Choose Player Models ---", timeout=5)
        expect_with_debug(child, r"Available AI models", timeout=5)
        expect_with_debug(child, r"Available Stockfish configs", timeout=5)
        expect_with_debug(child, r"Enter choice for White and Black players.*", timeout=5)

        # 3. Select AI models for White and Black (e.g., m1m2 for GPT-4o as White, Gemini as Black)
        child.sendline('m1m2')

        # 4. Expect opening/defense menu and send opening/defense selection (e.g., 1a)
        expect_with_debug(child, r"White openings:", timeout=5)
        expect_with_debug(child, r"Black defenses:", timeout=5)
        expect_with_debug(child, r"Enter white opening and black defense as a single input", timeout=5)
        child.sendline('1a')

        # 5. Expect game start (increase timeout here)
        expect_with_debug(child, r"--- Game Started ---", timeout=30)
        expect_with_debug(child, r"White: ", timeout=5)
        expect_with_debug(child, r"Black: ", timeout=5)
        expect_with_debug(child, r"Initial FEN:", timeout=5)

        # 6. Expect board display (optional, but helps sync)
        expect_with_debug(child, r"a b c d e f g h", timeout=5)
        expect_with_debug(child, r"---------------------", timeout=5)

        # 7. Wait for move prompt (either White or Black)
        expect_with_debug(child, r"Move \d+.*:.*", timeout=10)
        child.sendline('q')
        expect_with_debug(child, r"--- Quit Options ---", timeout=5)
        child.sendline('q')
        expect_with_debug(child, r"Exiting game without saving.", timeout=10)
    finally:
        _terminate_process(child)

@pytest.mark.integration
def test_load_practice_position_menu_sequence():
    """
    Integration test for the 'Load a Practice Position' menu sequence.
    Steps:
    - Start app
    - Select '3' for Load a Practice Position
    - Select '1' for King and Queen vs. King
    - Verify board and description are displayed
    - Quit from player model menu
    """
    child = PopenSpawn(PY_CMD, encoding='utf-8', timeout=15, env=TEST_ENV)
    try:
        child.expect(r"--- Main Menu ---")
        child.expect(r"Enter your choice")
        child.sendline('3')

        child.expect(r"--- Practice Positions ---")
        child.expect(r"Enter the number of the position to load, or a letter for other options")
        child.sendline('1')

        # Expect board display
        child.expect(r"a b c d e f g h")
        child.expect(r"---------------------")
        child.expect(r"1\| . . . . . . . Q \|1")
        child.expect(r"---------------------")
        child.expect(r"a b c d e f g h")

        # Expect position number and description
        child.expect(r"Position 1:.*fundamental checkmate.*queen.*box in.*king.*deliver the final mate")

        # Expect player model menu
        child.expect(r"--- Choose Player Models ---")
        child.expect(r"Enter choice for White and Black players.*")
        child.sendline('q')

        # Expect exit message
        child.expect(r"Exiting application.")
    finally:
        if child.proc.poll() is None:
            child.proc.terminate()

@pytest.mark.integration
def test_main_menu_load_saved_game(tmp_path):
    """
    Integration test: Load a Saved Game from the main menu.
    - Starts the app
    - Selects '2' to load a saved game
    - Selects the first available saved game
    - Verifies the game loads and the board is displayed
    """
    child = PopenSpawn(PY_CMD, encoding='utf-8', timeout=30, env=TEST_ENV)
    child.delayafterread = 0.1

    try:
        # Main menu
        expect_with_debug(child, r"--- Main Menu ---", timeout=10)
        expect_with_debug(child, r"Enter your choice", timeout=5)
        child.sendline('2')

        # Load a Saved Game menu
        expect_with_debug(child, r"--- Load a Saved Game ---", timeout=10)
        expect_with_debug(child, r"Enter the number of the game to load, or 'm' to return:", timeout=5)
        child.sendline('1')

        # Should load the game and display the board
        expect_with_debug(child, r"a b c d e f g h", timeout=10)
        expect_with_debug(child, r"---------------------", timeout=5)
        expect_with_debug(child, r"Move \d+.*:.*", timeout=10)

        # Quit the loaded game
        child.sendline('q')
        expect_with_debug(child, r"--- Quit Options ---", timeout=10)
        child.sendline('q')
        expect_with_debug(child, r"Exiting game without saving.", timeout=10)
    finally:
        _terminate_process(child)

@pytest.mark.integration
def test_practice_position_play_and_quit():
    """
    Integration test for selecting a practice position, choosing AI models, and quitting.
    Steps:
    - Start app
    - Select '3' for Load a Practice Position
    - Select '1' for King and Queen vs. King
    - Verify board and description are displayed
    - Choose AI models for White and Black (e.g., m1m2)
    - Verify game loads and board is displayed
    - Quit the game
    """
    child = PopenSpawn(PY_CMD, encoding='utf-8', timeout=30, env=TEST_ENV)
    child.delayafterread = 0.1

    try:
        expect_with_debug(child, r"--- Main Menu ---", timeout=10)
        expect_with_debug(child, r"Enter your choice", timeout=5)
        child.sendline('3')

        expect_with_debug(child, r"--- Practice Positions ---", timeout=10)
        expect_with_debug(child, r"Enter the number of the position to load, or a letter for other options", timeout=5)
        child.sendline('1')

        expect_with_debug(child, r"a b c d e f g h", timeout=5)
        expect_with_debug(child, r"---------------------", timeout=5)
        expect_with_debug(child, r"Position 1:.*fundamental checkmate.*queen.*box in.*king.*deliver the final mate", timeout=10)

        expect_with_debug(child, r"--- Choose Player Models ---", timeout=5)
        expect_with_debug(child, r"Enter choice for White and Black players.*", timeout=5)
        child.sendline('m1m2')

        expect_with_debug(child, r"Loaded practice position: King and Queen vs. King", timeout=10)
        expect_with_debug(child, r"--- Game Started ---", timeout=10)
        expect_with_debug(child, r"White: openai/gpt-4o", timeout=5)
        expect_with_debug(child, r"Black: deepseek/deepseek-chat-v3.1", timeout=5)
        expect_with_debug(child, r"Initial FEN: 8/k7/8/8/8/8/K7/7Q w - - 0 1", timeout=5)
        expect_with_debug(child, r"a b c d e f g h", timeout=5)
        expect_with_debug(child, r"---------------------", timeout=5)

        # expect_cleaned_prompt(child, r"quit", timeout=20)
        child.sendline('q')
        # expect_with_debug(child, r"--- Quit Options ---", timeout=5)
        child.sendline('q')
        # expect_with_debug(child, r"Exiting game without saving.", timeout=10)
    finally:
        _terminate_process(child)

def expect_cleaned_line(child, pattern, timeout=15):
    import time, re
    deadline = time.time() + timeout
    regex = re.compile(pattern)
    while time.time() < deadline:
        line = child.readline()
        if not line:
            continue
        cleaned = clean_output(line)
        if regex.search(cleaned):
            return True
    raise AssertionError(f"Pattern not found: {pattern}")

def expect_cleaned_pattern(child, pattern, timeout=15):
    """
    Expects a regex pattern in the child's output, cleaning ANSI codes.
    """
    import time, re
    regex = re.compile(pattern)
    deadline = time.time() + timeout
    while time.time() < deadline:
        # Read all available output (non-blocking)
        try:
            output = child.read_nonblocking(size=4096, timeout=1)
        except Exception:
            output = b""
        if output:
            text = clean_output(output.decode('utf-8', errors='ignore'))
            if regex.search(text):
                return True
        # Also check the current buffer
        text = clean_output(child.before)
        if regex.search(text):
            return True
        time.sleep(0.1)
    raise AssertionError(f"Pattern not found: {pattern}")

def expect_cleaned_prompt(child, pattern, timeout=15):
    import time, re
    regex = re.compile(pattern)
    deadline = time.time() + timeout
    while time.time() < deadline:
        cleaned = clean_output(child.before)
        if regex.search(cleaned):
            return True
        try:
            output = child.read_nonblocking(size=4096, timeout=1)
            cleaned = clean_output(output)
            if regex.search(cleaned):
                return True
        except Exception:
            pass
        time.sleep(0.1)
    raise AssertionError(f"Pattern not found: {pattern}")