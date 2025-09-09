import getpass
import re
import os
from typing import Optional, Tuple
from src.utils.input_handler import get_password

class AuthUI:
    """User interface for authentication and registration."""
    
    def display_auth_menu(self) -> str:
        """Display the authentication menu and get user choice."""
        print("\n--- Authentication Required ---")
        print("  1: Login")
        print("  2: Register New Account")
        print("  q: Quit Application")
        
        while True:
            choice = input("Enter your choice: ").strip().lower()
            if choice in ['1', '2', 'q']:
                return choice
            print("Invalid choice. Please try again.")
    
    def get_login_credentials(self) -> Tuple[str, str]:
        """Get username/email and password for login."""
        print("\n--- Login ---")
        username_or_email = input("Username or Email: ").strip()
        password = get_password("Password: ")
        return username_or_email, password
    
    def get_registration_info(self) -> Optional[Tuple[str, str, str]]:
        """Get username, email, and password for registration."""
        print("\n--- Register New Account ---")
        
        # Get username
        while True:
            username = input("Username (3-20 characters, letters, numbers, underscores only): ").strip()
            if re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
                break
            print("Invalid username format. Please try again.")
        
        # Get email
        while True:
            email = input("Email address: ").strip()
            if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                break
            print("Invalid email format. Please try again.")
        
        # Get password
        while True:
            password = get_password("Password (minimum 8 characters): ")
            if len(password) >= 8:
                confirm_password = get_password("Confirm password: ")
                if password == confirm_password:
                    break
                print("Passwords don't match. Please try again.")
            else:
                print("Password must be at least 8 characters.")
        
        return username, email, password
    
    def display_message(self, message: str) -> None:
        """Display a message to the user."""
        print(f"\n{message}")
    
    def get_verification_token(self) -> str:
        """Get a verification token from user."""
        return input("Enter verification token from email: ").strip()
    
    def get_verification_option(self) -> str:
        """Display verification options and get user choice."""
        print("\n--- Email Verification Required ---")
        print("  1: Enter Verification Code")
        print("  2: Resend Verification Email")
        print("  3: Back to Main Menu")
        
        while True:
            choice = input("Enter your choice: ").strip()
            if choice in ['1', '2', '3']:
                return choice
            print("Invalid choice. Please try again.")

    def show_main_menu(self):
        """Show the main menu of the application."""
        print("\n--- Main Menu ---")
        print("  1: Continue as Guest")
        print("  2: Login")
        print("  3: Register")
        print("  q: Quit")
        
        while True:
            choice = input("Enter your choice: ").strip().lower()
            if choice in ['1', '2', '3', 'q']:
                if choice == '1':
                    self.display_message("Continuing as guest...")
                    # Logic for guest access
                elif choice == '2':
                    self.display_message("Please log in.")
                    # Logic for login
                elif choice == '3':
                    self.display_message("Please register.")
                    # Logic for registration
                elif choice == 'q':
                    self.display_message("Quitting the application. Goodbye!")
                    exit(0)
                return
            print("Invalid choice. Please try again.")

def main():
    if os.environ.get("CHESS_APP_TEST_MODE") == "1":
        # In test mode, skip authentication and go straight to main menu
        AuthUI().show_main_menu()
    else:
        # Normal flow: show authentication menu first
        AuthUI().display_auth_menu()
        # Continue with login/registration as needed

if __name__ == "__main__":
    main()