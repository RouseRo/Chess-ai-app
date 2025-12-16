# Pytest Testing Guide

## Introduction
This document provides information on how to test the Chess AI application using pytest. Our testing approach focuses on both unit tests for individual components and integration tests for verifying complete user flows through the application.

The Chess AI application uses a unified SQLite-based authentication system via the `auth-service` API. Tests mock the `AuthClient` class to simulate authentication without requiring a running Docker environment.

## Setup
### Prerequisites
- Python 3.12 or later
- pytest 8.0.0 or later
- pytest-timeout for managing test timeouts
- pexpect (for integration tests on non-Windows systems)

### Installation
Install all necessary testing dependencies from the project root:
```bash
# Install testing dependencies
pip install pytest pytest-timeout pexpect
```

## Test Organization
Tests are organized in the `tests/` directory, which keeps them separate from the application's source code.

```
tests/
├── conftest.py          # Shared fixtures (mock_auth_client, temp_db, app_instance)
├── test_basic.py        # Basic tests and examples
├── test_env_vars.py     # Tests for environment variables
├── test_main_parsing.py # Tests for CLI argument parsing
├── test_player_factory.py # Tests for player creation
└── ... other test files
```

## Running Tests

### Basic Commands
You can run tests from the root directory of the project.

```bash
# Run all tests in the 'tests' directory
pytest

# Run tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_player_factory.py

# Run a specific test function within a file
pytest tests/test_player_factory.py::test_create_human_player
```

### Viewing Print Output
By default, pytest captures all output from print statements.  
To see print output during test runs, use the `-s` flag:

```bash
pytest -s tests/test_env_vars.py
```

### Using Markers (`-m` option)
The `-m` option allows you to select tests to run based on "markers". Markers are custom labels you can apply to your test functions to categorize them (e.g., `integration`, `unit`, `slow`).

**How to Run Tests with Markers:**
*   **Run only integration tests:**
    ```bash
    pytest -m integration
    ```
*   **Run all tests EXCEPT integration tests:**
    ```bash
    pytest -m "not integration"
    ```
*   **Run tests that are marked as `unit` OR `regression`:**
    ```bash
    pytest -m "unit or regression"
    ```

**Defining Markers:**
To assign a marker to a test, use the `@pytest.mark.<marker_name>` decorator.
```python
import pytest

@pytest.mark.integration
def test_some_integration_feature():
    assert True

@pytest.mark.unit
def test_some_unit_logic():
    assert 1 + 1 == 2
```
To avoid warnings, markers should be registered in your `pytest.ini` file.
```ini
[pytest]
markers =
    integration: marks a test as an integration test
    unit: marks a test as a unit test
```

## Test File Descriptions

Detailed descriptions for all test files and individual tests in `tests/`:

---

### [test_basic.py](tests/test_basic.py)
General unit tests, examples, and helper utilities for the test suite.

| Test | Description |
|------|-------------|
| `test_basic_functionality` | Simple sanity test to verify pytest is working correctly. |
| `test_with_unit_marker` | Demonstrates usage of the `@pytest.mark.unit` marker. |

**Helper function:**
- `expect_with_debug(child, pattern, ...)`: Wrapper around `pexpect.expect()` that prints buffer content on timeout for easier debugging.

---

### [test_env_vars.py](tests/test_env_vars.py)
Verifies that key Windows and pytest-related environment variables are set and accessible during tests.

| Test | Description |
|------|-------------|
| `test_windows_env_vars` | (Windows-only) Checks `USERPROFILE`, `APPDATA`, `TEMP`, `COMPUTERNAME`, `USERNAME`, etc. |
| `test_path_variables` | (Windows-only) Validates `PATH` contains Windows/System32, checks `PROGRAMFILES`, `PROGRAMDATA`. |
| `test_pytest_env_vars` | Prints pytest-related variables like `PYTEST_CURRENT_TEST`, `COVERAGE_FILE`, etc. |
| `test_stockfish_env_var_matches_config` | Verifies `STOCKFISH_EXECUTABLE` env var matches the value in `config.json`. |

---

### [test_main_parsing.py](tests/test_main_parsing.py)
Tests for CLI argument parsing and game log header parsing in `ChessApp`.

| Test | Description |
|------|-------------|
| `test_parse_log_header_success` | Verifies a valid game log header is parsed correctly into a `GameHeader` object. |
| `test_parse_log_header_invalid_player_key` | Verifies parsing fails when a player key is not in the allowed list. |

---

### [test_player_factory.py](tests/test_player_factory.py)
Tests for `PlayerFactory` behaviour when creating different player types.

| Test | Description |
|------|-------------|
| `test_create_human_player` | Verifies `PlayerFactory` creates a `HumanPlayer` and calls the UI prompt to get the player name. |
| `test_create_ai_player` | Verifies AI player creation from config (mocks OpenAI client to avoid network calls). |
| `test_create_stockfish_player` | Verifies Stockfish player is instantiated with expected parameters (engine is mocked). |
| `test_create_stockfish_player_invalid_path` | Verifies `FileNotFoundError` is raised when the Stockfish path is invalid. |
| `test_create_player_invalid_type` | Verifies the factory raises `KeyError` or `ValueError` on unknown player type. |

---

### [conftest.py](tests/conftest.py)
Shared test fixtures and test-wide configuration used across all test files.

| Fixture | Description |
|---------|-------------|
| `app_instance` | Creates a `ChessApp` instance for testing its methods. |
| `mock_auth_client` | (Recommended) Mocks `AuthClient` for authentication tests without Docker. |
| `temp_db` | (Recommended) Creates a temporary SQLite database for testing. |

**Configuration:**
- Adds project root to `sys.path` so tests can import from `src/`.
- Sets `STOCKFISH_EXECUTABLE` environment variable for all tests.

## Mocking Authentication

The Chess AI application uses the `AuthClient` class to communicate with the auth-service API for user authentication. In tests, we mock this client to avoid requiring a running Docker environment.

### AuthClient Mock Fixture

Add this fixture to your `tests/conftest.py`:

```python
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_auth_client():
    """
    Creates a mocked AuthClient for testing authentication flows.
    Returns a mock that simulates successful login/register responses.
    """
    with patch('src.auth_client.AuthClient') as MockClient:
        mock_instance = MagicMock()
        mock_instance.login.return_value = {
            "success": True,
            "user": {"username": "testuser", "role": "user"},
            "token": "mock-jwt-token"
        }
        mock_instance.register.return_value = {
            "success": True,
            "message": "User registered successfully"
        }
        mock_instance.get_user.return_value = {
            "username": "testuser",
            "role": "user",
            "is_verified": True
        }
        MockClient.return_value = mock_instance
        yield mock_instance
```

### Temporary Database Fixture

For tests that need actual database operations:

```python
import tempfile
import sqlite3
import os

@pytest.fixture
def temp_db():
    """
    Creates a temporary SQLite database for testing.
    The database is automatically cleaned up after the test.
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Initialize database schema
    conn = sqlite3.connect(db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            is_verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    os.unlink(db_path)
```

### Example Test Using Mocked Authentication

```python
def test_user_login_flow(mock_auth_client):
    """Test that login calls AuthClient correctly."""
    from src.user_manager import UserManager
    
    manager = UserManager(auth_service_url="http://localhost:8002")
    manager.client = mock_auth_client  # Inject mock
    
    result = manager.login("testuser", "password123")
    
    mock_auth_client.login.assert_called_once_with("testuser", "password123")
    assert result["success"] is True
    assert result["user"]["username"] == "testuser"
```

## Writing Integration Tests
Our integration tests use `pexpect` to simulate a user interacting with the application's command-line interface.

### Key `pexpect` Commands
*   **`child.expect(r"pattern")`**: Waits for the application to print text that matches a regular expression.
*   **`child.sendline('input')`**: Simulates the user typing text and pressing Enter.

### Debugging Helper
When an `expect()` call times out, it can be hard to know what the application's output was. The `expect_with_debug` helper function is provided in the test suite to print the buffer content on failure.
```python
def expect_with_debug(child, pattern, timeout=None):
    """Helper to expect a pattern with debug output on failure"""
    try:
        return child.expect(pattern, timeout=timeout)
    except pexpect.TIMEOUT:
        print(f"\nTIMEOUT waiting for: {pattern}")
        print(f"Current buffer content:\n{child.before}")
        raise
```

## Testing CLI Applications

### Challenge
Testing CLI applications that require authentication can be challenging because:
1. Password inputs typically use `getpass.getpass()` which bypasses normal input mechanisms
2. The application requires a running auth-service for real authentication
3. Terminal interactions can be difficult to automate

### Solution: Mock the AuthClient

Instead of using environment variables to bypass authentication, we mock the `AuthClient` class:

```python
from unittest.mock import patch, MagicMock

def test_cli_with_mocked_auth():
    """Test CLI flow with mocked authentication."""
    mock_client = MagicMock()
    mock_client.login.return_value = {
        "success": True,
        "user": {"username": "testuser", "role": "user"},
        "token": "mock-token"
    }
    
    with patch('src.auth_client.AuthClient', return_value=mock_client):
        # Your test code here
        pass
```

### Testing UserManager

The `UserManager` class can be tested by injecting a mock `AuthClient`:

```python
def test_user_manager_registration(mock_auth_client):
    """Test user registration through UserManager."""
    from src.user_manager import UserManager
    
    manager = UserManager(auth_service_url="http://localhost:8002")
    manager.client = mock_auth_client
    
    result = manager.register("newuser", "password123")
    
    assert result["success"] is True
    mock_auth_client.register.assert_called_once()
```

## Best Practices

- Register all custom markers in `pytest.ini` to avoid warnings.
- Use `pexpect` for robust CLI automation and output matching.
- Use the provided `expect_with_debug` helper for easier debugging of test failures.
- Always clean up child processes in your tests to avoid resource leaks.
- **Mock the `AuthClient`** class instead of bypassing authentication with environment variables.
- Use temporary databases (`temp_db` fixture) for tests that need real database operations.
- Inject mock dependencies via fixtures for consistent, repeatable tests.

## Troubleshooting

- **Authentication Errors in Tests:**  
  Ensure you're mocking `AuthClient` properly. The mock should return the expected response structure with `success`, `user`, and `token` keys.
- **Missing Dependencies:**  
  If you see `ModuleNotFoundError`, add the missing package to `requirements.txt`.
- **Stockfish Not Found:**  
  Ensure Stockfish is installed and the path is set via `STOCKFISH_EXECUTABLE` in your workflow and code.
- **OpenAI API Key Error:**  
  Set a dummy `OPENAI_API_KEY` in your CI environment for tests that instantiate the OpenAI client.
- **Database Locked Errors:**  
  When testing with SQLite, ensure connections are properly closed. Use the `temp_db` fixture which handles cleanup automatically.

## Environment Variable Testing

A dedicated test file, `tests/test_env_vars.py`, is included to verify that key Windows and pytest-related environment variables are set and accessible.  
To see the values of these variables during test runs, use the `-s` flag with pytest:

```bash
pytest -s tests/test_env_vars.py
```

This will print the values of variables such as `USERPROFILE`, `APPDATA`, `PATH`, and others, helping you debug environment issues.

## conftest.py Reference

The `tests/conftest.py` file contains shared fixtures used across all tests:

```python
import sys
import os
import pytest

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set Stockfish path for all tests
os.environ["STOCKFISH_EXECUTABLE"] = "C:\\stockfish\\stockfish-windows-x86-64-avx2.exe"

@pytest.fixture
def app_instance():
    """Creates a ChessApp instance for testing."""
    from src.main import ChessApp
    return ChessApp()
```

Add the `mock_auth_client` and `temp_db` fixtures shown in the "Mocking Authentication" section above.

---

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- See `README.md` for project overview

---

For more details, see the code and tests in the `src/` and `tests/` directories.