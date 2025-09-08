Pytest Testing Guide
Introduction
This document provides information on how to test the Chess AI application using pytest. Our testing approach focuses on both unit tests for individual components and integration tests for verifying complete user flows through the application.

Setup
Prerequisites
Python 3.12 or later
pytest 8.0.0 or later
pytest-timeout for managing test timeouts
Installation
# Install testing dependencies
pip install pytest pytest-timeout

Test Organization
Tests are organized in the tests directory:


tests/
├── test_basic.py              # Basic tests and examples
├── test_integration_main_menu.py  # Integration tests for menu flows
└── ... other test files


# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_basic.py

# Run a specific test
pytest tests/test_basic.py::test_main_menu_new_game_flow

# Match exact text
expect_with_debug(child, r"--- Main Menu ---")

# Match with wildcards
expect_with_debug(child, r"Move 1.*White.*Enter your move")

# Send a menu choice
child.sendline('1')

# Press Enter (empty input)
child.sendline('')

# Send a chess move
child.sendline('e2e4')

def expect_with_debug(child, pattern, timeout=None):
    """Helper to expect a pattern with debug output on failure"""
    try:
        return child.expect(pattern, timeout=timeout)
    except pexpect.TIMEOUT:
        print(f"\nTIMEOUT waiting for: {pattern}")
        print(f"Current buffer content:\n{child.before}")
        raise