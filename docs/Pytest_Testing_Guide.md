# Pytest Testing Guide

## Introduction
This document provides information on how to test the Chess AI application using pytest. Our testing approach focuses on both unit tests for individual components and integration tests for verifying complete user flows through the application.

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
├── test_basic.py                  # Basic tests and examples
├── test_integration_main_menu.py  # Integration tests for menu flows
├── test_env_vars.py               # Tests for environment variables
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
pytest tests/test_integration_main_menu.py

# Run a specific test function within a file
pytest tests/test_integration_main_menu.py::test_main_menu_new_game_flow
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

**Example Output:**
When you run `pytest -m integration`, pytest scans all tests, deselects those without the `integration` marker, and runs only the selected ones, as shown in this output:
```
C:\Users\rober\Source\Repos\Chess-ai-app>pytest -m integration
============================= test session starts ==============================
platform win32 -- Python 3.13.3, pytest-8.4.1, pluggy-1.6.0
rootdir: C:\Users\rober\Source\Repos\Chess-ai-app
configfile: pytest.ini
collected 20 items / 15 deselected / 5 selected

tests\test_integration_main_menu.py .....                            [100%]

======================= 5 passed, 15 deselected in 1.23s =======================
```
This shows that 5 tests with the `integration` marker were run, and 15 other tests were deselected.

**Defining Markers:**
To assign a marker to a test, use the `@pytest.mark.<marker_name>` decorator.
```python
# In a test file like tests/test_basic.py
import pytest

@pytest.mark.integration
def test_some_integration_feature():
    # This test will be selected by 'pytest -m integration'
    assert True

@pytest.mark.unit
def test_some_unit_logic():
    # This test will be deselected
    assert 1 + 1 == 2
```
To avoid warnings, markers should be registered in your `pytest.ini` file.
```ini
[pytest]
markers =
    integration: marks a test as an integration test
    unit: marks a test as a unit test
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

# Automated Testing of CLI Applications with Password Inputs

## Challenge
Testing CLI applications that require password input can be challenging because:
1. Password inputs typically use `getpass.getpass()` which bypasses normal input mechanisms
2. This can cause tests to hang waiting for user input
3. Terminal interactions can be difficult to automate

## Solution
We use a combination of techniques to automate password input:

1. **Environment variables for test detection**:
   ```python
   # In tests
   TEST_ENV = os.environ.copy()
   TEST_ENV["CHESS_APP_TEST_MODE"] = "1"
   ```
   When `CHESS_APP_TEST_MODE=1`, the application bypasses authentication and password prompts, allowing tests to interact directly with the main menu and game flows.

2. **Test Mode for Integration Testing**:
   - Set `CHESS_APP_TEST_MODE=1` before running integration tests to enable passwordless mode.
   - This mode is used in CI/CD pipelines and local integration testing for reliability.

3. **Handling Authentication in Full Mode**:
   - For tests that require full authentication (e.g., login integration tests), set `CHESS_APP_TEST_MODE=0` or unset the variable.
   - Your test code should handle authentication prompts before proceeding to main menu interactions.

## Best Practices

- Register all custom markers in `pytest.ini` to avoid warnings.
- Use `pexpect` for robust CLI automation and output matching.
- Use the provided `expect_with_debug` helper for easier debugging of test failures.
- Always clean up child processes in your tests to avoid resource leaks.
- Use environment variables to control test modes and application behavior.

## Troubleshooting

- **Authentication Menu Timeout:**  
  If a test fails waiting for the main menu but the authentication menu is shown, update your test to handle authentication (login or register) before proceeding to the main menu when `CHESS_APP_TEST_MODE=0`.
- **Missing Dependencies:**  
  If you see `ModuleNotFoundError`, add the missing package to `requirements.txt`.
- **Stockfish Not Found:**  
  Ensure Stockfish is installed and the path is set via `STOCKFISH_EXECUTABLE` in your workflow and code.
- **OpenAI API Key Error:**  
  Set a dummy `OPENAI_API_KEY` in your CI environment for tests that instantiate the OpenAI client.

## Environment Variable Testing

A dedicated test file, `tests/test_env_vars.py`, is included to verify that key Windows and pytest-related environment variables are set and accessible.  
To see the values of these variables during test runs, use the `-s` flag with pytest:

```bash
pytest -s tests/test_env_vars.py
```

This will print the values of variables such as `USERPROFILE`, `APPDATA`, `PATH`, and others, helping you debug environment issues.

---

For more details, see the code and tests in the `src/` and `tests/` directories.

---

### Summary of Updates:
1. **Added Test Descriptions:**
   - Detailed the purpose and steps for each test.

2. **Updated Utilities Section:**
   - Explained the purpose of helper functions like [expect_with_debug](http://_vscodecontentref_/0).

3. **Environment Setup:**
   - Included details about the test environment and how to run the tests.

4. **Recent Updates Section:**
   - Highlighted recent changes to the tests.

---

Let me know if you need further updates or additional documentation!