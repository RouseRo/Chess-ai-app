# tests/test_basic.py
import pytest
import sys
import pexpect
from pexpect.popen_spawn import PopenSpawn
import re
import time

# Command to run the application as a module
PY_CMD = [sys.executable, "-u", "-m", "src.main"]

def expect_with_debug(child, pattern, timeout=None, searchwindowsize=None, verbose=False):
    """Helper function to expect a pattern with better debugging
    
    Args:
        child: The pexpect child process
        pattern: The regex pattern to match
        timeout: Timeout in seconds (None uses default)
        searchwindowsize: Window size for searching
        verbose: If True, prints detailed debug info
    
    Returns:
        The result from child.expect
    """
    try:
        if verbose:
            print(f"\nLooking for pattern: {pattern}")
            print(f"Current buffer before matching:\n{child.before}")
        
        result = child.expect(pattern, timeout=timeout, searchwindowsize=searchwindowsize)
        
        if verbose:
            print(f"Successfully matched pattern: {pattern}")
        return result
    except pexpect.TIMEOUT:
        print(f"\nTIMEOUT after {timeout}s waiting for: {pattern}")
        print(f"Buffer content at timeout:\n{child.before}")
        raise
    except Exception as e:
        print(f"\nError while waiting for {pattern}: {str(e)}")
        print(f"Buffer content at error:\n{child.before}")
        raise

def test_basic_functionality():
    """A simple test to verify pytest is working correctly."""
    assert True

@pytest.mark.unit
def test_with_unit_marker():
    """A test with the 'unit' marker to demonstrate marker usage."""
    assert 1 + 1 == 2

@pytest.mark.skip(reason="Skipping integration test for now")
@pytest.mark.integration
def test_main_menu_new_game_flow():
    """Test the flow of starting a new game from the main menu"""
    child = PopenSpawn(PY_CMD, encoding='utf-8', timeout=30)
    child.delayafterread = 0.1

    try:
        # Wait for the main menu
        expect_with_debug(child, r"--- Main Menu ---", timeout=10)
        expect_with_debug(child, r"Enter your choice", timeout=5)

        # Select option '1' for new game
        child.sendline('1')

        # Verify the setup menu appears
        expect_with_debug(child, r"--- Setup New Game ---", timeout=10)
        expect_with_debug(child, r"Choose player models for White and Black", timeout=5)
        expect_with_debug(child, r"--- Choose Player Models ---", timeout=5)
        expect_with_debug(child, r"Available AI models:", timeout=5)
        expect_with_debug(child, r"Available Stockfish configs:", timeout=5)
        expect_with_debug(child, r"Enter choice for White and Black players", timeout=5)

        # Select "Human vs Stockfish (Strong, Powerful)"
        child.sendline('hus3')

        # Verify human player message
        expect_with_debug(child, r"Human player selected for White", timeout=10)

        # Verify the black defense options
        expect_with_debug(child, r"Choose black defense", timeout=5)
        expect_with_debug(child, r"Black defense key:", timeout=5)

        # Select "No Classic Chess Defense"
        child.sendline('z')

        # Verify name prompt and skip by pressing Enter
        expect_with_debug(child, r"Enter name for White player \(leave blank for 'Human'\):", timeout=10)
        child.sendline('')

        # Wait for the game to start and display the initial board
        expect_with_debug(child, r"--- Game Started ---", timeout=10)
        expect_with_debug(child, r"White: Human", timeout=5)
        expect_with_debug(child, r"Black: Stockfish", timeout=5)
        expect_with_debug(child, r"Initial FEN:", timeout=5)
        expect_with_debug(child, r"8\|", timeout=10)

        # Wait for move prompt
        expect_with_debug(child, r"Move 1.*Enter your move", timeout=10)

        # Quit the game
        child.sendline('q')

        # Verify quit options appear
        expect_with_debug(child, r"--- Quit Options ---", timeout=5)
        expect_with_debug(child, r"Enter your choice \[r/s/q/c\]:", timeout=5)
        child.sendline('q')

        # Verify exit message
        expect_with_debug(child, r"Exiting without saving.", timeout=5)

    finally:
        print(f"\nFinal buffer state:\n{child.before}")
        if child.proc.poll() is None:
            try:
                child.sendintr()
                time.sleep(1)
            except:
                pass
            try:
                child.proc.terminate()
                time.sleep(1)
                if child.proc.poll() is None:
                    child.proc.kill()
            except:
                pass