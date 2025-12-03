import json
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict

class UserManager:
    def __init__(self, data_dir: str = "user_data"):
        self.data_dir = data_dir
        self.users_file = os.path.join(data_dir, "users.json")
        self.sessions_file = os.path.join(data_dir, "sessions.json")
        self.models_file = os.path.join(data_dir, "ai_models.json")
        os.makedirs(data_dir, exist_ok=True)
        self._ensure_files_exist()
        self._create_default_admin()

    def _ensure_files_exist(self):
        """Create JSON files if they don't exist."""
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w') as f:
                json.dump({}, f)
        if not os.path.exists(self.sessions_file):
            with open(self.sessions_file, 'w') as f:
                json.dump({}, f)
        if not os.path.exists(self.models_file):
            with open(self.models_file, 'w') as f:
                json.dump(self._default_ai_models(), f, indent=2)

    def _default_ai_models(self) -> dict:
        """Return default AI models configuration."""
        return {
            "models": [
                {
                    "id": "stockfish",
                    "name": "Stockfish",
                    "type": "local",
                    "skill_level": 10,
                    "enabled": True
                },
                {
                    "id": "openai_gpt4",
                    "name": "OpenAI GPT-4",
                    "type": "api",
                    "provider": "OpenAI",
                    "enabled": False
                },
                {
                    "id": "deepseek",
                    "name": "DeepSeek",
                    "type": "api",
                    "provider": "DeepSeek",
                    "enabled": False
                }
            ]
        }

    def _create_default_admin(self):
        """Create default admin user if no users exist."""
        users = self._load_users()
        
        # Only create default admin if no users exist
        if len(users) == 0:
            admin_password = self._hash_password("Admin@123")
            users["admin"] = {
                "email": "admin@chessai.app",
                "password": admin_password,
                "is_admin": True,
                "created_at": datetime.now().isoformat(),
                "games_played": 0,
                "last_login": None
            }
            self._save_users(users)
            print("✓ Default admin user created: admin / Admin@123")
            print("⚠ IMPORTANT: Change the admin password immediately!")

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

    def _load_models(self) -> dict:
        """Load AI models configuration."""
        with open(self.models_file, 'r') as f:
            return json.load(f)

    def _save_models(self, models: dict):
        """Save AI models configuration."""
        with open(self.models_file, 'w') as f:
            json.dump(models, f, indent=2)

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
            "is_admin": False,
            "created_at": datetime.now().isoformat(),
            "games_played": 0,
            "last_login": None
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

        # Update last login
        user['last_login'] = datetime.now().isoformat()
        self._save_users(users)

        # Generate session token
        token = secrets.token_urlsafe(32)
        sessions = self._load_sessions()
        sessions[token] = {
            "username": username,
            "is_admin": user.get('is_admin', False),
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

    def is_admin(self, token: str) -> bool:
        """Check if token belongs to an admin user."""
        sessions = self._load_sessions()
        
        if token not in sessions:
            return False
        
        return sessions[token].get('is_admin', False)

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

    # ============ ADMIN METHODS ============

    def list_all_users(self) -> List[dict]:
        """Get list of all users (admin only)."""
        users = self._load_users()
        user_list = []
        
        for username, user_data in users.items():
            user_list.append({
                "username": username,
                "email": user_data.get('email'),
                "is_admin": user_data.get('is_admin', False),
                "created_at": user_data.get('created_at'),
                "last_login": user_data.get('last_login'),
                "games_played": user_data.get('games_played', 0)
            })
        
        return user_list

    def delete_user(self, username: str, admin_username: str) -> Tuple[bool, str]:
        """Delete a user (admin only)."""
        if username == "admin":
            return False, "Cannot delete the admin user"
        
        if username == admin_username:
            return False, "Cannot delete your own account"
        
        users = self._load_users()
        
        if username not in users:
            return False, "User not found"
        
        del users[username]
        self._save_users(users)
        
        return True, f"User '{username}' deleted successfully"

    def promote_user_to_admin(self, username: str) -> Tuple[bool, str]:
        """Promote a user to admin status."""
        users = self._load_users()
        
        if username not in users:
            return False, "User not found"
        
        if users[username].get('is_admin', False):
            return False, "User is already an admin"
        
        users[username]['is_admin'] = True
        self._save_users(users)
        
        return True, f"User '{username}' promoted to admin"

    def demote_user_from_admin(self, username: str) -> Tuple[bool, str]:
        """Demote an admin user to regular user."""
        if username == "admin":
            return False, "Cannot demote the default admin user"
        
        users = self._load_users()
        
        if username not in users:
            return False, "User not found"
        
        if not users[username].get('is_admin', False):
            return False, "User is not an admin"
        
        users[username]['is_admin'] = False
        self._save_users(users)
        
        return True, f"User '{username}' demoted to regular user"

    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user password."""
        users = self._load_users()
        
        if username not in users:
            return False, "User not found"
        
        user = users[username]
        
        if not self._verify_password(old_password, user['password']):
            return False, "Invalid current password"
        
        if len(new_password) < 6:
            return False, "New password must be at least 6 characters long"
        
        user['password'] = self._hash_password(new_password)
        self._save_users(users)
        
        return True, "Password changed successfully"

    def get_ai_models(self) -> dict:
        """Get all AI models configuration."""
        return self._load_models()

    def add_ai_model(self, model_id: str, model_data: dict) -> Tuple[bool, str]:
        """Add a new AI model (admin only)."""
        models = self._load_models()
        
        if any(m['id'] == model_id for m in models['models']):
            return False, "Model with this ID already exists"
        
        model_data['id'] = model_id
        if 'enabled' not in model_data:
            model_data['enabled'] = False
        
        models['models'].append(model_data)
        self._save_models(models)
        
        return True, f"AI model '{model_id}' added successfully"

    def remove_ai_model(self, model_id: str) -> Tuple[bool, str]:
        """Remove an AI model (admin only)."""
        models = self._load_models()
        
        original_count = len(models['models'])
        models['models'] = [m for m in models['models'] if m['id'] != model_id]
        
        if len(models['models']) == original_count:
            return False, "Model not found"
        
        self._save_models(models)
        return True, f"AI model '{model_id}' removed successfully"

    def update_ai_model(self, model_id: str, updates: dict) -> Tuple[bool, str]:
        """Update AI model configuration (admin only)."""
        models = self._load_models()
        
        model_found = False
        for model in models['models']:
            if model['id'] == model_id:
                model.update(updates)
                model_found = True
                break
        
        if not model_found:
            return False, "Model not found"
        
        self._save_models(models)
        return True, f"AI model '{model_id}' updated successfully"

    def get_system_stats(self) -> dict:
        """Get system statistics (admin only)."""
        users = self._load_users()
        sessions = self._load_sessions()
        models = self._load_models()
        
        total_games = sum(u.get('games_played', 0) for u in users.values())
        admin_count = sum(1 for u in users.values() if u.get('is_admin', False))
        
        return {
            "total_users": len(users),
            "admin_users": admin_count,
            "active_sessions": len(sessions),
            "total_games_played": total_games,
            "total_ai_models": len(models.get('models', [])),
            "enabled_models": len([m for m in models.get('models', []) if m.get('enabled', False)])
        }