import os
import re
import json
import uuid
import hashlib
import secrets
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any

class UserManager:
    """
    Manages user accounts, authentication, and verification for the Chess AI application.
    Ensures saved games can only be continued by the users who created them.
    """
    
    def __init__(self, data_dir: str = "user_data", dev_mode: bool = True):
        """
        Initialize the UserManager with storage location.
        
        Args:
            data_dir: Directory to store user data files
            dev_mode: If True, use development mode (no actual emails sent)
        """
        self.data_dir = data_dir
        self.dev_mode = dev_mode
        self._ensure_data_dir_exists()
        
        # Store active user sessions
        self.active_sessions: Dict[str, str] = {}  # session_token -> username
        
        # Load email configuration
        self.email_config = self._load_email_config()
        
        # Dev mode verification tokens
        self.dev_verification_tokens = {}
    
    def _ensure_data_dir_exists(self) -> None:
        """Create the data directory if it doesn't exist."""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "profiles"), exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "verification"), exist_ok=True)
    
    def _load_email_config(self) -> Dict[str, str]:
        """
        Load email configuration from config file or environment variables.
        In a production app, these would be stored securely, not in code.
        """
        config_path = os.path.join(self.data_dir, "email_config.json")
        
        # Default configuration (replace with actual values)
        default_config = {
            "smtp_server": os.environ.get("CHESS_SMTP_SERVER", "smtp.example.com"),
            "smtp_port": os.environ.get("CHESS_SMTP_PORT", "587"),
            "smtp_username": os.environ.get("CHESS_SMTP_USERNAME", "noreply@yourdomain.com"),
            "smtp_password": os.environ.get("CHESS_SMTP_PASSWORD", ""),
            "from_email": os.environ.get("CHESS_FROM_EMAIL", "chess-app@yourdomain.com"),
        }
        
        # If config file exists, load it
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
                
        # Otherwise save and return the default
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
            
        return default_config
    
    def _get_user_path(self, username: str) -> str:
        """Get the path to a user's profile data file."""
        # Convert username to lowercase alphanumeric only for filename
        safe_username = re.sub(r'[^a-z0-9]', '', username.lower())
        return os.path.join(self.data_dir, "profiles", f"{safe_username}.json")
    
    def _hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash a password using a secure method with salt.
        
        Args:
            password: The password to hash
            salt: Optional salt, generated if not provided
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
            
        # In a production app, use a proper password hashing library like bcrypt
        # This is a simplified version using hashlib
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000  # Number of iterations
        )
        hashed_password = hash_obj.hex()
        
        return hashed_password, salt
    
    def _verify_password(self, stored_hash: str, stored_salt: str, provided_password: str) -> bool:
        """Verify a password against its stored hash."""
        calculated_hash, _ = self._hash_password(provided_password, stored_salt)
        return secrets.compare_digest(calculated_hash, stored_hash)
    
    def _generate_token(self) -> str:
        """Generate a secure random token for session or verification."""
        return secrets.token_urlsafe(32)
    
    def register_user(self, username: str, email: str, password: str) -> Tuple[bool, str]:
        """
        Register a new user with email verification.
        
        Args:
            username: Chosen username
            email: User's email address
            password: User's password
            
        Returns:
            Tuple of (success, message)
        """
        # Validate inputs
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            return False, "Username must be 3-20 characters and contain only letters, numbers, and underscores."
        
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            return False, "Please enter a valid email address."
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters."
        
        # Check if username already exists
        if os.path.exists(self._get_user_path(username)):
            return False, "Username already taken."
        
        # Check if email is already registered
        if self._is_email_registered(email):
            return False, "Email address already registered."
        
        # Create user profile
        hashed_pw, salt = self._hash_password(password)
        
        user_data = {
            "username": username,
            "email": email,
            "password_hash": hashed_pw,
            "password_salt": salt,
            "verified": False,
            "created_at": datetime.datetime.now().isoformat(),
            "last_login": None,
            "games": []  # List of game IDs associated with this user
        }
        
        # Save user data
        with open(self._get_user_path(username), 'w') as f:
            json.dump(user_data, f, indent=4)
        
        # Create verification token and send verification email
        verification_token = self._generate_token()
        self._save_verification_token(username, verification_token)
        
        email_sent = self._send_verification_email(email, username, verification_token)
        
        if email_sent:
            return True, "Registration successful! Please check your email to verify your account."
        else:
            return True, "Registration successful, but there was a problem sending the verification email. Please contact support."
    
    def _is_email_registered(self, email: str) -> bool:
        """Check if an email is already registered."""
        profiles_dir = os.path.join(self.data_dir, "profiles")
        
        if not os.path.exists(profiles_dir):
            return False
            
        for filename in os.listdir(profiles_dir):
            if not filename.endswith('.json'):
                continue
                
            try:
                with open(os.path.join(profiles_dir, filename), 'r') as f:
                    user_data = json.load(f)
                    if user_data.get("email", "").lower() == email.lower():
                        return True
            except (json.JSONDecodeError, IOError):
                continue
                
        return False
    
    def _save_verification_token(self, username: str, token: str) -> None:
        """Save a verification token for a user."""
        verification_data = {
            "username": username,
            "token": token,
            "created_at": datetime.datetime.now().isoformat(),
            "expires_at": (datetime.datetime.now() + datetime.timedelta(days=2)).isoformat()
        }
        
        token_path = os.path.join(self.data_dir, "verification", f"{token}.json")
        
        with open(token_path, 'w') as f:
            json.dump(verification_data, f, indent=4)
    
    def _send_verification_email(self, email: str, username: str, token: str) -> bool:
        """
        Send a verification email to the user.
        
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        # In development mode, just print the verification link to console
        if self.dev_mode:
            verification_link = f"http://localhost:8000/verify?token={token}"
            print("\n" + "="*50)
            print("DEVELOPMENT MODE: Email would be sent to:", email)
            print("Subject: Verify your Chess AI App Account")
            print("-"*50)
            print(f"Welcome {username}! Your verification token is: {token}")
            print(f"You can use this token directly in the application.")
            print("="*50 + "\n")
            
            # Store in dev verification tokens for easy access
            self.dev_verification_tokens[username] = token
            
            return True
        
        # In production mode, send actual email
        verification_link = f"http://localhost:8000/verify?token={token}"
        
        subject = "Verify your Chess AI App Account"
        
        # Create email body with HTML and plain text versions
        html_content = f"""
        <html>
        <body>
            <h2>Welcome to Chess AI App!</h2>
            <p>Hi {username},</p>
            <p>Thank you for registering. Please click the link below to verify your account:</p>
            <p><a href="{verification_link}">Verify Your Account</a></p>
            <p>This link will expire in 48 hours.</p>
            <p>If you didn't register for an account, please ignore this email.</p>
            <p>Best regards,<br>The Chess AI Team</p>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to Chess AI App!
        
        Hi {username},
        
        Thank you for registering. Please use the link below to verify your account:
        
        {verification_link}
        
        This link will expire in 48 hours.
        
        If you didn't register for an account, please ignore this email.
        
        Best regards,
        The Chess AI Team
        """
        
        # Create the email message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.email_config["from_email"]
        message["To"] = email
        
        # Attach parts
        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        message.attach(part1)
        message.attach(part2)
        
        # Send the email
        try:
            with smtplib.SMTP(self.email_config["smtp_server"], int(self.email_config["smtp_port"])) as server:
                server.starttls()
                if self.email_config["smtp_username"] and self.email_config["smtp_password"]:
                    server.login(self.email_config["smtp_username"], self.email_config["smtp_password"])
                server.sendmail(
                    self.email_config["from_email"],
                    email,
                    message.as_string()
                )
            return True
        except Exception as e:
            print(f"Error sending verification email: {e}")
            return False
    
    def verify_email(self, token: str) -> Tuple[bool, str]:
        """
        Verify a user's email using the verification token.
        
        Args:
            token: The verification token from the email
            
        Returns:
            Tuple of (success, message)
        """
        # In dev mode, check if token is in our dev tokens
        if self.dev_mode:
            for username, dev_token in self.dev_verification_tokens.items():
                if dev_token == token:
                    # Get user path
                    user_path = self._get_user_path(username)
                    
                    # Update user verification status
                    try:
                        with open(user_path, 'r') as f:
                            user_data = json.load(f)
                            
                        user_data["verified"] = True
                        
                        with open(user_path, 'w') as f:
                            json.dump(user_data, f, indent=4)
                        
                        # Remove from dev tokens
                        del self.dev_verification_tokens[username]
                        
                        return True, "Email verified successfully! You can now log in."
                    except Exception as e:
                        print(f"Error in dev mode verification: {e}")
                        return False, "An error occurred during verification."
    
        # Normal verification flow
        token_path = os.path.join(self.data_dir, "verification", f"{token}.json")
        
        if not os.path.exists(token_path):
            return False, "Invalid or expired verification token."
        
        try:
            with open(token_path, 'r') as f:
                verification_data = json.load(f)
                
            # Check if token is expired
            expires_at = datetime.datetime.fromisoformat(verification_data["expires_at"])
            if datetime.datetime.now() > expires_at:
                os.remove(token_path)
                return False, "Verification token has expired. Please request a new one."
                
            username = verification_data["username"]
            user_path = self._get_user_path(username)
            
            if not os.path.exists(user_path):
                os.remove(token_path)
                return False, "User account not found."
                
            # Update user verification status
            with open(user_path, 'r') as f:
                user_data = json.load(f)
                
            user_data["verified"] = True
            
            with open(user_path, 'w') as f:
                json.dump(user_data, f, indent=4)
                
            # Remove the used token
            os.remove(token_path)
            
            return True, "Email verified successfully! You can now log in."
            
        except (json.JSONDecodeError, KeyError, IOError) as e:
            print(f"Error verifying email: {e}")
            return False, "An error occurred during verification. Please try again."
    
    def login(self, username_or_email: str, password: str) -> Tuple[bool, str, Optional[str]]:
        """
        Authenticate a user and create a session.
        
        Args:
            username_or_email: Username or email address
            password: User's password
            
        Returns:
            Tuple of (success, message, session_token)
        """
        # Check if input is email or username
        is_email = '@' in username_or_email
        
        if is_email:
            # Find username by email
            profiles_dir = os.path.join(self.data_dir, "profiles")
            username = None
            
            for filename in os.listdir(profiles_dir):
                if not filename.endswith('.json'):
                    continue
                    
                try:
                    with open(os.path.join(profiles_dir, filename), 'r') as f:
                        user_data = json.load(f)
                        if user_data.get("email", "").lower() == username_or_email.lower():
                            username = user_data["username"]
                            break
                except (json.JSONDecodeError, IOError):
                    continue
                    
            if username is None:
                return False, "Email address not found.", None
        else:
            username = username_or_email
        
        # Check if user exists
        user_path = self._get_user_path(username)
        if not os.path.exists(user_path):
            return False, "Username not found.", None
            
        # Load user data
        try:
            with open(user_path, 'r') as f:
                user_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return False, "Error loading user data.", None
            
        # Check verification status
        if not user_data.get("verified", False):
            return False, "Account not verified. Please check your email for the verification link.", None
            
        # Verify password
        if not self._verify_password(
            user_data["password_hash"], 
            user_data["password_salt"], 
            password
        ):
            return False, "Incorrect password.", None
            
        # Create session token
        session_token = self._generate_token()
        self.active_sessions[session_token] = username
        
        # Update last login
        user_data["last_login"] = datetime.datetime.now().isoformat()
        
        with open(user_path, 'w') as f:
            json.dump(user_data, f, indent=4)
            
        return True, f"Welcome back, {username}!", session_token
    
    def logout(self, session_token: str) -> bool:
        """
        End a user session.
        
        Args:
            session_token: The active session token
            
        Returns:
            bool: True if session was found and ended, False otherwise
        """
        if session_token in self.active_sessions:
            del self.active_sessions[session_token]
            return True
        return False
    
    def get_current_user(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Get the current logged-in user's data.
        
        Args:
            session_token: The active session token
            
        Returns:
            User data dictionary or None if not logged in
        """
        if session_token not in self.active_sessions:
            return None
            
        username = self.active_sessions[session_token]
        user_path = self._get_user_path(username)
        
        if not os.path.exists(user_path):
            # Invalid session, user no longer exists
            del self.active_sessions[session_token]
            return None
            
        try:
            with open(user_path, 'r') as f:
                user_data = json.load(f)
                
            # Don't return sensitive data
            return {
                "username": user_data["username"],
                "email": user_data["email"],
                "verified": user_data["verified"],
                "created_at": user_data["created_at"],
                "last_login": user_data["last_login"],
                "games": user_data.get("games", [])
            }
        except (json.JSONDecodeError, IOError):
            return None
    
    def change_password(self, session_token: str, current_password: str, 
                       new_password: str) -> Tuple[bool, str]:
        """
        Change a user's password.
        
        Args:
            session_token: Active session token
            current_password: Current password for verification
            new_password: New password to set
            
        Returns:
            Tuple of (success, message)
        """
        if session_token not in self.active_sessions:
            return False, "Not logged in."
            
        username = self.active_sessions[session_token]
        user_path = self._get_user_path(username)
        
        try:
            with open(user_path, 'r') as f:
                user_data = json.load(f)
                
            # Verify current password
            if not self._verify_password(
                user_data["password_hash"],
                user_data["password_salt"],
                current_password
            ):
                return False, "Current password is incorrect."
                
            # Validate new password
            if len(new_password) < 8:
                return False, "New password must be at least 8 characters."
                
            # Update password
            new_hash, new_salt = self._hash_password(new_password)
            user_data["password_hash"] = new_hash
            user_data["password_salt"] = new_salt
            
            with open(user_path, 'w') as f:
                json.dump(user_data, f, indent=4)
                
            return True, "Password updated successfully."
            
        except (json.JSONDecodeError, IOError):
            return False, "Error updating password."
    
    def update_profile(self, session_token: str, 
                      profile_updates: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update a user's profile information.
        
        Args:
            session_token: Active session token
            profile_updates: Dictionary of fields to update
            
        Returns:
            Tuple of (success, message)
        """
        if session_token not in self.active_sessions:
            return False, "Not logged in."
            
        username = self.active_sessions[session_token]
        user_path = self._get_user_path(username)
        
        try:
            with open(user_path, 'r') as f:
                user_data = json.load(f)
            
            # Only allow updating certain fields
            allowed_fields = ["display_name", "preferences"]
            
            for field, value in profile_updates.items():
                if field in allowed_fields:
                    user_data[field] = value
            
            with open(user_path, 'w') as f:
                json.dump(user_data, f, indent=4)
                
            return True, "Profile updated successfully."
            
        except (json.JSONDecodeError, IOError):
            return False, "Error updating profile."
    
    def associate_game_with_user(self, session_token: str, game_id: str) -> bool:
        """
        Associate a game with a user, so they can continue it later.
        
        Args:
            session_token: Active session token
            game_id: ID of the game
            
        Returns:
            bool: True if successful, False otherwise
        """
        if session_token not in self.active_sessions:
            return False
            
        username = self.active_sessions[session_token]
        user_path = self._get_user_path(username)
        
        try:
            with open(user_path, 'r') as f:
                user_data = json.load(f)
                
            if "games" not in user_data:
                user_data["games"] = []
                
            if game_id not in user_data["games"]:
                user_data["games"].append(game_id)
                
            with open(user_path, 'w') as f:
                json.dump(user_data, f, indent=4)
                
            return True
                
        except (json.JSONDecodeError, IOError):
            return False
    
    def get_user_games(self, session_token: str) -> List[str]:
        """
        Get the list of games associated with a user.
        
        Args:
            session_token: Active session token
            
        Returns:
            List of game IDs
        """
        user_data = self.get_current_user(session_token)
        if user_data:
            return user_data.get("games", [])
        return []
    
    def request_password_reset(self, email: str) -> Tuple[bool, str]:
        """
        Generate a password reset token and email it to the user.
        
        Args:
            email: User's email address
            
        Returns:
            Tuple of (success, message)
        """
        # Find user by email
        profiles_dir = os.path.join(self.data_dir, "profiles")
        username = None
        
        for filename in os.listdir(profiles_dir):
            if not filename.endswith('.json'):
                continue
                
            try:
                with open(os.path.join(profiles_dir, filename), 'r') as f:
                    user_data = json.load(f)
                    if user_data.get("email", "").lower() == email.lower():
                        username = user_data["username"]
                        break
            except (json.JSONDecodeError, IOError):
                continue
                
        if not username:
            # Don't reveal if email exists or not for security
            return True, "If your email is registered, you will receive a password reset link."
            
        # Generate reset token
        reset_token = self._generate_token()
        reset_data = {
            "username": username,
            "token": reset_token,
            "created_at": datetime.datetime.now().isoformat(),
            "expires_at": (datetime.datetime.now() + datetime.timedelta(hours=24)).isoformat()
        }
        
        reset_path = os.path.join(self.data_dir, "verification", f"reset_{reset_token}.json")
        
        with open(reset_path, 'w') as f:
            json.dump(reset_data, f, indent=4)
            
        # Send reset email
        reset_link = f"http://localhost:8000/reset-password?token={reset_token}"
        
        subject = "Reset Your Chess AI App Password"
        
        html_content = f"""
        <html>
        <body>
            <h2>Chess AI App Password Reset</h2>
            <p>Hi {username},</p>
            <p>You requested a password reset. Please click the link below to reset your password:</p>
            <p><a href="{reset_link}">Reset Your Password</a></p>
            <p>This link will expire in 24 hours.</p>
            <p>If you didn't request a password reset, please ignore this email.</p>
            <p>Best regards,<br>The Chess AI Team</p>
        </body>
        </html>
        """
        
        text_content = f"""
        Chess AI App Password Reset
        
        Hi {username},
        
        You requested a password reset. Please use the link below to reset your password:
        
        {reset_link}
        
        This link will expire in 24 hours.
        
        If you didn't request a password reset, please ignore this email.
        
        Best regards,
        The Chess AI Team
        """
        
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.email_config["from_email"]
        message["To"] = email
        
        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        message.attach(part1)
        message.attach(part2)
        
        try:
            with smtplib.SMTP(self.email_config["smtp_server"], int(self.email_config["smtp_port"])) as server:
                server.starttls()
                if self.email_config["smtp_username"] and self.email_config["smtp_password"]:
                    server.login(self.email_config["smtp_username"], self.email_config["smtp_password"])
                server.sendmail(
                    self.email_config["from_email"],
                    email,
                    message.as_string()
                )
            return True, "If your email is registered, you will receive a password reset link."
        except Exception as e:
            print(f"Error sending password reset email: {e}")
            return False, "Error sending email. Please try again later."
    
    def reset_password(self, token: str, new_password: str) -> Tuple[bool, str]:
        """
        Reset a user's password using a reset token.
        
        Args:
            token: Password reset token
            new_password: New password to set
            
        Returns:
            Tuple of (success, message)
        """
        token_path = os.path.join(self.data_dir, "verification", f"reset_{token}.json")
        
        if not os.path.exists(token_path):
            return False, "Invalid or expired reset token."
            
        try:
            with open(token_path, 'r') as f:
                reset_data = json.load(f)
                
            # Check if token is expired
            expires_at = datetime.datetime.fromisoformat(reset_data["expires_at"])
            if datetime.datetime.now() > expires_at:
                os.remove(token_path)
                return False, "Reset token has expired. Please request a new one."
                
            username = reset_data["username"]
            user_path = self._get_user_path(username)
            
            if not os.path.exists(user_path):
                os.remove(token_path)
                return False, "User account not found."
                
            # Validate new password
            if len(new_password) < 8:
                return False, "New password must be at least 8 characters."
                
            # Update user password
            with open(user_path, 'r') as f:
                user_data = json.load(f)
                
            new_hash, new_salt = self._hash_password(new_password)
            user_data["password_hash"] = new_hash
            user_data["password_salt"] = new_salt
            
            with open(user_path, 'w') as f:
                json.dump(user_data, f, indent=4)
                
            # Remove the used token
            os.remove(token_path)
            
            return True, "Password reset successful! You can now log in with your new password."
            
        except (json.JSONDecodeError, KeyError, IOError) as e:
            print(f"Error resetting password: {e}")
            return False, "An error occurred during password reset. Please try again."