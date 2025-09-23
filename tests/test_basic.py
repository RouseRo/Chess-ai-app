# tests/test_basic.py
import pytest
import sys
import pexpect
from pexpect.popen_spawn import PopenSpawn
import re

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
