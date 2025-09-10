# Chess AI App

## Overview
Chess AI App is a Python-based chess application supporting user authentication, game management, and AI-powered features. It includes robust automated testing using pytest and supports a passwordless test mode for streamlined integration testing.

## Features
- User registration, login, and email verification
- Play, load, and practice chess games
- View player stats and ask a chess expert
- Automated tests with pytest
- **Test Mode:** Set `CHESS_APP_TEST_MODE=1` to bypass authentication and password prompts for automated testing

## Running the Application

```bash
python -m src.main
```

## Running Tests

### Standard Test Mode (Passwordless)
Most tests use passwordless test mode for speed and reliability.  
Set the environment variable before running tests:

```bash
set CHESS_APP_TEST_MODE=1
pytest
```

### Full Authentication Flow Test
The login integration test (`tests/test_login_integration.py`) temporarily disables test mode to verify the full authentication flow:

```bash
pytest tests/test_login_integration.py
```

### Running All Tests Except Login Integration
```bash
pytest --ignore=tests/test_login_integration.py
```

## Test Mode Details

- When `CHESS_APP_TEST_MODE=1`, the app starts directly at the main menu and bypasses authentication and password prompts.
- When `CHESS_APP_TEST_MODE=0`, the app runs in normal mode with full authentication.

## Directory Structure

```
src/
  main.py
  auth_ui.py
  utils/
    input_handler.py
tests/
  test_basic.py
  test_login_integration.py
  test_integration_main_menu.py
  ...
```

## Contributing

1. Fork the repo
2. Create a feature branch
3. Submit a pull request

## Continuous Integration

This project uses GitHub Actions for CI/CD.  
On every pull request to `master`, the pipeline will:

- Install dependencies
- Set a dummy `OPENAI_API_KEY` for tests that require OpenAI client instantiation
- Install Stockfish on Linux runners and set the `STOCKFISH_EXECUTABLE` environment variable
- Run all pytest tests in passwordless mode (`CHESS_APP_TEST_MODE=1`) except the login integration test
- Run the login integration test in full authentication mode (`CHESS_APP_TEST_MODE=0`)

See `.github/workflows/python-app.yml` for details.

### CI/CD Notes

- The CI pipeline sets a dummy `OPENAI_API_KEY` for tests that require OpenAI client instantiation.
- If your tests do not need to call the real OpenAI API, use `pytest-mock` to mock the OpenAI client.
- The Stockfish chess engine is installed on Linux runners and its path is set using the `STOCKFISH_EXECUTABLE` environment variable.
- All tests should use `os.environ.get("STOCKFISH_EXECUTABLE", "stockfish")` to locate the Stockfish binary.
- If you encounter authentication menu prompts in tests when `CHESS_APP_TEST_MODE=0`, ensure your test code navigates through authentication before expecting the main menu.
- For tests that expect the main menu immediately, use `CHESS_APP_TEST_MODE=1`.

---

## Troubleshooting Test Failures

- **Authentication Menu Timeout:**  
  If a test fails waiting for the main menu but the authentication menu is shown, update your test to handle authentication (login or register) before proceeding to the main menu when `CHESS_APP_TEST_MODE=0`.
- **Missing Dependencies:**  
  If you see `ModuleNotFoundError`, add the missing package to `requirements.txt`.
- **Stockfish Not Found:**  
  Ensure Stockfish is installed and the path is set via `STOCKFISH_EXECUTABLE` in your workflow and code.
- **OpenAI API Key Error:**  
  Set a dummy `OPENAI_API_KEY` in your CI environment for tests that instantiate the OpenAI client.

---
