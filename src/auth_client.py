"""
HTTP client for authentication service.
Provides unified authentication for both CLI and web interfaces.
"""

import os
import requests
from typing import Tuple, Optional, Dict, Any


class AuthClient:
    """Client for communicating with the auth-service API."""
    
    def __init__(self, base_url: str = None):
        """
        Initialize the auth client.
        
        Args:
            base_url: Base URL for the auth service. 
                      Defaults to AUTH_SERVICE_URL env var or http://localhost:8002
        """
        self.base_url = base_url or os.environ.get(
            "AUTH_SERVICE_URL", 
            "http://localhost:8002"
        )
        self.timeout = 10  # seconds
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: dict = None,
        token: str = None
    ) -> Tuple[bool, dict]:
        """
        Make an HTTP request to the auth service.
        
        Returns:
            Tuple of (success, response_data)
        """
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=self.timeout)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            else:
                return False, {"message": f"Unsupported HTTP method: {method}"}
            
            response_data = response.json()
            return response.ok, response_data
            
        except requests.exceptions.ConnectionError:
            return False, {
                "message": f"Cannot connect to auth service at {self.base_url}. "
                           "Make sure the service is running (docker-compose up)."
            }
        except requests.exceptions.Timeout:
            return False, {"message": "Auth service request timed out."}
        except requests.exceptions.RequestException as e:
            return False, {"message": f"Auth service error: {str(e)}"}
        except ValueError:
            return False, {"message": "Invalid response from auth service."}
    
    def health_check(self) -> bool:
        """Check if the auth service is available."""
        success, _ = self._make_request("GET", "/health")
        return success
    
    def login(
        self, 
        username_or_email: str, 
        password: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Authenticate a user.
        
        Args:
            username_or_email: Username or email address
            password: User's password
            
        Returns:
            Tuple of (success, message, token)
        """
        data = {
            "username": username_or_email,
            "password": password
        }
        
        success, response = self._make_request("POST", "/auth/login", data)
        
        if success and response.get("success"):
            return True, response.get("message", "Login successful"), response.get("token")
        else:
            return False, response.get("message", "Login failed"), None
    
    def register(
        self, 
        username: str, 
        email: str, 
        password: str
    ) -> Tuple[bool, str]:
        """
        Register a new user.
        
        Args:
            username: Desired username
            email: Email address
            password: Password
            
        Returns:
            Tuple of (success, message)
        """
        data = {
            "username": username,
            "email": email,
            "password": password
        }
        
        success, response = self._make_request("POST", "/auth/register", data)
        
        if success and response.get("success"):
            return True, response.get("message", "Registration successful")
        else:
            return False, response.get("message", "Registration failed")
    
    def verify_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Verify a JWT token and get user data.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Tuple of (is_valid, user_data)
        """
        data = {"token": token}
        
        success, response = self._make_request("POST", "/auth/verify", data)
        
        if success and response.get("valid"):
            user_data = {
                "username": response.get("username"),
                "is_admin": response.get("is_admin", False),
                "email": response.get("email", "")
            }
            return True, user_data
        else:
            return False, None
    
    def verify_email(self, token: str) -> Tuple[bool, str]:
        """
        Verify a user's email with verification token.
        
        Args:
            token: Email verification token
            
        Returns:
            Tuple of (success, message)
        """
        data = {"token": token}
        
        success, response = self._make_request("POST", "/auth/verify-email", data)
        
        if success and response.get("success"):
            return True, response.get("message", "Email verified successfully")
        else:
            return False, response.get("message", "Email verification failed")
    
    def logout(self, token: str) -> Tuple[bool, str]:
        """
        Logout a user (invalidate token on server if supported).
        
        Args:
            token: JWT token to invalidate
            
        Returns:
            Tuple of (success, message)
        """
        data = {"token": token}
        
        success, response = self._make_request("POST", "/auth/logout", data)
        
        # Logout is always "successful" from client perspective
        return True, response.get("message", "Logged out successfully")
    
    def change_password(
        self, 
        token: str, 
        old_password: str, 
        new_password: str
    ) -> Tuple[bool, str]:
        """
        Change user's password.
        
        Args:
            token: JWT token for authentication
            old_password: Current password
            new_password: New password
            
        Returns:
            Tuple of (success, message)
        """
        data = {
            "old_password": old_password,
            "new_password": new_password
        }
        
        success, response = self._make_request(
            "POST", "/auth/change-password", data, token=token
        )
        
        if success and response.get("success"):
            return True, response.get("message", "Password changed successfully")
        else:
            return False, response.get("message", "Password change failed")
    
    def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get current user data from token.
        
        Args:
            token: JWT token
            
        Returns:
            User data dict or None if invalid
        """
        is_valid, user_data = self.verify_token(token)
        return user_data if is_valid else None