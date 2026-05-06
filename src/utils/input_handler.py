"""Input handler utilities."""

import os
import sys
import getpass


def get_input(prompt: str = "") -> str:
    """
    Get input from user.

    Args:
        prompt: Optional prompt to display

    Returns:
        User input string
    """
    if prompt:
        print(prompt, end="", flush=True)
    return input()


def get_password(prompt: str = "Password: ") -> str:
    """
    Get password input (hidden).

    Args:
        prompt: Prompt to display

    Returns:
        Password string
    """
    return getpass.getpass(prompt)


def authenticate_user():
    username = input("Username: ")
    password = get_password("Password: ")
    # Add your authentication logic here
    print(f"Username: {username}, Password: {password}")

# Uncomment the following line to test the authentication function
# authenticate_user()