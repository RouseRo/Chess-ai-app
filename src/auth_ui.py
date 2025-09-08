import getpass
import re
from typing import Optional, Tuple

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
        password = getpass.getpass("Password: ")
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
            password = getpass.getpass("Password (minimum 8 characters): ")
            if len(password) >= 8:
                confirm_password = getpass.getpass("Confirm password: ")
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