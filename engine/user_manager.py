import json
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

class UserManager:
    def __init__(self, data_dir: str = "user_data"):
        self.data_dir = data_dir
        self.users_file = os.path.join(data_dir, "users.json")
        self.sessions_file = os.path.join(data_dir, "sessions.json")
        os.makedirs(data_dir, exist_ok=True)
        self._ensure_files_exist()

    def _ensure_files_exist(self):
        """Create JSON files if they don't exist."""
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w') as f:
                json.dump({}, f)
        if not os.path.exists(self.sessions_file):
            with open(self.sessions_file, 'w') as f:
                json.dump({}, f)

    def _hash_password(self, password: str) -> str:
        """Hash password with salt."""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${hash_obj.hex()}"

    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            salt, hash_hex = hashed.split('$')
            hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return hash_obj.hex() == hash_hex
        except:
            return False

    def _load_users(self) -> dict:
        """Load users from JSON file."""
        with open(self.users_file, 'r') as f:
            return json.load(f)

    def _save_users(self, users: dict):
        """Save users to JSON file."""
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=2)

    def _load_sessions(self) -> dict:
        """Load sessions from JSON file."""
        with open(self.sessions_file, 'r') as f:
            return json.load(f)

    def _save_sessions(self, sessions: dict):
        """Save sessions to JSON file."""
        with open(self.sessions_file, 'w') as f:
            json.dump(sessions, f, indent=2)

    def register_user(self, username: str, email: str, password: str) -> Tuple[bool, str]:
        """Register a new user."""
        users = self._load_users()

        # Validate input
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters long"
        if not email or '@' not in email:
            return False, "Invalid email address"
        if not password or len(password) < 6:
            return False, "Password must be at least 6 characters long"

        # Check if user exists
        if username in users or any(u.get('email') == email for u in users.values()):
            return False, "Username or email already exists"

        # Create new user
        users[username] = {
            "email": email,
            "password": self._hash_password(password),
            "created_at": datetime.now().isoformat(),
            "games_played": 0
        }

        self._save_users(users)
        return True, "User registered successfully"

    def login_user(self, username: str, password: str) -> Tuple[bool, str, Optional[str]]:
        """Authenticate user and create session."""
        users = self._load_users()

        if username not in users:
            return False, "Invalid username or password", None

        user = users[username]
        if not self._verify_password(password, user['password']):
            return False, "Invalid username or password", None

        # Generate session token
        token = secrets.token_urlsafe(32)
        sessions = self._load_sessions()
        sessions[token] = {
            "username": username,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat()
        }
        self._save_sessions(sessions)

        return True, "Login successful", token

    def verify_token(self, token: str) -> Tuple[bool, Optional[str]]:
        """Verify session token."""
        sessions = self._load_sessions()

        if token not in sessions:
            return False, None

        session = sessions[token]
        expires_at = datetime.fromisoformat(session['expires_at'])

        if datetime.now() > expires_at:
            del sessions[token]
            self._save_sessions(sessions)
            return False, None

        return True, session['username']

    def logout_user(self, token: str) -> bool:
        """Logout user by removing session."""
        sessions = self._load_sessions()
        if token in sessions:
            del sessions[token]
            self._save_sessions(sessions)
            return True
        return False

    def get_user_info(self, username: str) -> Optional[dict]:
        """Get user information."""
        users = self._load_users()
        if username in users:
            user = users[username].copy()
            user.pop('password', None)  # Don't expose password
            return user
        return None