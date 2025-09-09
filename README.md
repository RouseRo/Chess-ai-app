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

---
