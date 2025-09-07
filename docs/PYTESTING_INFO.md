Pytest Testing Guide
Introduction
This document provides information on how to test the Chess AI application using pytest. Our testing approach focuses on both unit tests for individual components and integration tests for verifying complete user flows through the application.

Setup
Prerequisites
Python 3.12 or later
pytest 8.0.0 or later
pytest-timeout for managing test timeouts
Installation
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