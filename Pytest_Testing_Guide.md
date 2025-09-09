# Pytest Testing Guide for Chess AI App

## Overview

This guide explains how to run and write automated tests for the Chess AI App using pytest, including the use of passwordless test mode.

---

## Test Modes

### Passwordless Test Mode (`CHESS_APP_TEST_MODE=1`)
- Most tests run with `CHESS_APP_TEST_MODE=1` to skip authentication and password prompts.
- The app starts directly at the main menu, allowing fast and reliable menu and feature testing.

### Full Authentication Flow (`CHESS_APP_TEST_MODE=0`)
- The login integration test (`test_login_integration.py`) sets `CHESS_APP_TEST_MODE=0` to verify registration, email verification, and login.
- After the test, it restores test mode to `1`.

---

## Running Tests

### Run All Tests (Passwordless Mode)
```bash
set CHESS_APP_TEST_MODE=1
pytest
```

### Run Only the Login Integration Test (Full Auth Flow)
```bash
pytest tests/test_login_integration.py
```

### Run All Tests Except Login Integration
```bash
pytest --ignore=tests/test_login_integration.py
```

---

## Writing Tests

- Use `env=TEST_ENV` when spawning processes in tests, where `TEST_ENV` includes `CHESS_APP_TEST_MODE`.
- Do **not** send passwords or expect authentication prompts in passwordless mode.
- For authentication tests, set `os.environ["CHESS_APP_TEST_MODE"] = "0"` before spawning the process.

---

## Example Test Setup

```python
import os
from pexpect.popen_spawn import PopenSpawn

TEST_ENV = os.environ.copy()
TEST_ENV["CHESS_APP_TEST_MODE"] = "1"

child = PopenSpawn("python -m src.main", encoding='utf-8', timeout=15, env=TEST_ENV)
child.expect("--- Main Menu ---")
child.sendline("q")
child.expect("Exiting application.")
```

---

## Troubleshooting

- If a test fails due to missing authentication prompts, check the value of `CHESS_APP_TEST_MODE`.
- Always restore environment variables after tests that change them.

---

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- See `README.md` for more details on test mode