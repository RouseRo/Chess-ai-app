import os
import getpass


def get_password(prompt="Password: "):
    if os.environ.get("CHESS_APP_TEST_MODE") == "1":
        print(prompt, end="", flush=True)
        import builtins

        return builtins.input()
    else:
        return getpass.getpass(prompt)


def authenticate_user():
    username = input("Username: ")
    password = get_password("Password: ")
    # Add your authentication logic here
    print(f"Username: {username}, Password: {password}")

# Uncomment the following line to test the authentication function
# authenticate_user()