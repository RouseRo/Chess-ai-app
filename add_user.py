import json
import os
import bcrypt
from datetime import datetime, timezone
import argparse

def add_user(username: str, email: str, password: str, is_admin: bool = False):
    """Add a new user to the system."""
    
    # Ensure directory exists
    users_dir = "user_data/users"
    os.makedirs(users_dir, exist_ok=True)
    
    user_file = os.path.join(users_dir, f"{username}.json")
    
    # Check if user already exists
    if os.path.exists(user_file):
        print(f"✗ Error: User '{username}' already exists")
        return False
    
    # Check email uniqueness
    for file in os.listdir(users_dir):
        if file.endswith('.json'):
            with open(os.path.join(users_dir, file), 'r') as f:
                existing_user = json.load(f)
                if existing_user.get('email') == email:
                    print(f"✗ Error: Email '{email}' is already registered")
                    return False
    
    # Validate password
    if len(password) < 6:
        print("✗ Error: Password must be at least 6 characters")
        return False
    
    if len(password) > 72:
        print("✗ Error: Password must be less than 72 characters")
        return False
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create user data
    user_data = {
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "is_admin": is_admin,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "games_played": 0
    }
    
    # Save user
    with open(user_file, 'w') as f:
        json.dump(user_data, f, indent=2)
    
    print(f"✓ User '{username}' created successfully!")
    print(f"  Email: {email}")
    print(f"  Admin: {is_admin}")
    
    return True

def list_users():
    """List all existing users."""
    users_dir = "user_data/users"
    
    if not os.path.exists(users_dir):
        print("No users found.")
        return
    
    print("\n--- Existing Users ---")
    print(f"{'Username':<15} {'Email':<30} {'Admin':<6} {'Games'}")
    print("-" * 60)
    
    for file in sorted(os.listdir(users_dir)):
        if file.endswith('.json'):
            with open(os.path.join(users_dir, file), 'r') as f:
                user = json.load(f)
                print(f"{user.get('username', 'N/A'):<15} {user.get('email', 'N/A'):<30} {str(user.get('is_admin', False)):<6} {user.get('games_played', 0)}")

def main():
    parser = argparse.ArgumentParser(description='Add users to Chess AI App')
    parser.add_argument('--list', action='store_true', help='List all users')
    parser.add_argument('--username', '-u', type=str, help='Username')
    parser.add_argument('--email', '-e', type=str, help='Email address')
    parser.add_argument('--password', '-p', type=str, help='Password')
    parser.add_argument('--admin', '-a', action='store_true', help='Make user an admin')
    
    args = parser.parse_args()
    
    if args.list:
        list_users()
        return
    
    # Interactive mode if no arguments provided
    if not args.username:
        print("=== Add New User ===\n")
        list_users()
        print()
        
        username = input("Enter username: ").strip()
        email = input("Enter email: ").strip()
        password = input("Enter password: ").strip()
        is_admin = input("Make admin? (y/n): ").strip().lower() == 'y'
        
        if username and email and password:
            add_user(username, email, password, is_admin)
        else:
            print("✗ Error: All fields are required")
    else:
        # Command line mode
        if not args.email or not args.password:
            print("✗ Error: --email and --password are required")
            return
        
        add_user(args.username, args.email, args.password, args.admin)

if __name__ == "__main__":
    main()