"""
User Manager - Unified authentication using auth-service API.
"""

import logging
from typing import Tuple, Optional, Dict, Any

from src.auth_client import AuthClient


class UserManager:
    """
    Manages user authentication via auth-service API.
    """
    
    def __init__(self, auth_service_url: str = None):
        """
        Initialize UserManager.
        
        Args:
            auth_service_url: URL for auth service (default: http://localhost:8002)
        """
        self.auth_client = AuthClient(auth_service_url)
        self._api_available = None
    
    def _is_api_available(self) -> bool:
        """Check if auth service is available."""
        if self._api_available is None:
            self._api_available = self.auth_client.health_check()
            if self._api_available:
                logging.debug("Auth service API is available")
            else:
                logging.warning("Auth service API not available")
        return self._api_available
    
    def login(
        self, 
        username_or_email: str, 
        password: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Authenticate a user via API.
        
        Args:
            username_or_email: Username or email
            password: Password
            
        Returns:
            Tuple of (success, message, token)
        """
        if not self._is_api_available():
            return False, "Auth service not available. Please ensure Docker services are running.", None
        
        return self.auth_client.login(username_or_email, password)
    
    def register_user(
        self, 
        username: str, 
        email: str, 
        password: str
    ) -> Tuple[bool, str]:
        """
        Register a new user via API.
        
        Args:
            username: Desired username
            email: Email address
            password: Password
            
        Returns:
            Tuple of (success, message)
        """
        if not self._is_api_available():
            return False, "Auth service not available. Please ensure Docker services are running."
        
        return self.auth_client.register(username, email, password)
    
    def verify_email(self, token: str) -> Tuple[bool, str]:
        """
        Verify email with token.
        
        Args:
            token: Verification token
            
        Returns:
            Tuple of (success, message)
        """
        if not self._is_api_available():
            return False, "Auth service not available."
        
        return self.auth_client.verify_email(token)
    
    def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get user data from token.
        
        Args:
            token: JWT token
            
        Returns:
            User data dict or None
        """
        if not self._is_api_available():
            return None
        
        return self.auth_client.get_current_user(token)
    
    def logout(self, token: str) -> Tuple[bool, str]:
        """
        Logout user.
        
        Args:
            token: Session token
            
        Returns:
            Tuple of (success, message)
        """
        if not self._is_api_available():
            return True, "Logged out."
        
        return self.auth_client.logout(token)
    
    def change_password(
        self,
        token: str,
        old_password: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """
        Change user's password.
        
        Args:
            token: JWT token
            old_password: Current password
            new_password: New password
            
        Returns:
            Tuple of (success, message)
        """
        if not self._is_api_available():
            return False, "Auth service not available."
        
        return self.auth_client.change_password(token, old_password, new_password)