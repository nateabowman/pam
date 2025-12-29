"""
JWT authentication for World P.A.M.
"""

import os
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from logger import get_logger


class JWTAuth:
    """JWT authentication manager."""
    
    def __init__(self, secret_key: Optional[str] = None, algorithm: str = "HS256"):
        """
        Initialize JWT auth.
        
        Args:
            secret_key: Secret key for signing (from env if None)
            algorithm: JWT algorithm
        """
        self.secret_key = secret_key or os.getenv("PAM_JWT_SECRET", "change-me-in-production")
        self.algorithm = algorithm
        self.logger = get_logger("jwt_auth")
    
    def create_token(
        self,
        user_id: str,
        username: str,
        role: str,
        expires_in_hours: int = 24
    ) -> str:
        """
        Create JWT token.
        
        Args:
            user_id: User ID
            username: Username
            role: User role
            expires_in_hours: Token expiration in hours
            
        Returns:
            JWT token string
        """
        payload = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "exp": datetime.utcnow() + timedelta(hours=expires_in_hours),
            "iat": datetime.utcnow(),
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded payload or None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            self.logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.warning(f"Invalid JWT token: {e}")
            return None
    
    def refresh_token(self, token: str, expires_in_hours: int = 24) -> Optional[str]:
        """
        Refresh JWT token.
        
        Args:
            token: Existing token
            expires_in_hours: New expiration time
            
        Returns:
            New token or None if original invalid
        """
        payload = self.verify_token(token)
        if not payload:
            return None
        
        # Create new token with same user info
        return self.create_token(
            user_id=payload["user_id"],
            username=payload["username"],
            role=payload["role"],
            expires_in_hours=expires_in_hours
        )


# Global JWT auth instance
_global_jwt = JWTAuth()


def get_jwt_auth() -> JWTAuth:
    """Get global JWT auth instance."""
    return _global_jwt

