"""
Advanced rate limiting middleware for FastAPI.
Per-user/per-API-key rate limiting.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import time
from fastapi import Request, HTTPException
from logger import get_logger


class RateLimiter:
    """Per-user rate limiter."""
    
    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_windows: Dict[str, list] = defaultdict(list)
        self.hour_windows: Dict[str, list] = defaultdict(list)
        self.logger = get_logger("rate_limit")
    
    def check_rate_limit(self, identifier: str) -> tuple[bool, Optional[str]]:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: User ID or API key ID
            
        Returns:
            Tuple of (allowed, error_message)
        """
        now = time.time()
        
        # Clean old entries
        self.minute_windows[identifier] = [
            ts for ts in self.minute_windows[identifier]
            if now - ts < 60
        ]
        self.hour_windows[identifier] = [
            ts for ts in self.hour_windows[identifier]
            if now - ts < 3600
        ]
        
        # Check minute limit
        if len(self.minute_windows[identifier]) >= self.requests_per_minute:
            return False, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"
        
        # Check hour limit
        if len(self.hour_windows[identifier]) >= self.requests_per_hour:
            return False, f"Rate limit exceeded: {self.requests_per_hour} requests per hour"
        
        # Record request
        self.minute_windows[identifier].append(now)
        self.hour_windows[identifier].append(now)
        
        return True, None


# Global rate limiter
_global_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter."""
    return _global_rate_limiter


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware for FastAPI.
    
    Args:
        request: FastAPI request
        call_next: Next middleware/handler
        
    Returns:
        Response
    """
    # Get identifier (API key or user ID)
    identifier = None
    
    # Try API key first
    api_key = request.headers.get("X-API-Key")
    if api_key:
        identifier = f"api_key:{api_key}"
    
    # Try JWT token
    if not identifier:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            from security.jwt_auth import get_jwt_auth
            jwt_auth = get_jwt_auth()
            payload = jwt_auth.verify_token(token)
            if payload:
                identifier = f"user:{payload.get('user_id')}"
    
    # Fallback to IP address
    if not identifier:
        identifier = f"ip:{request.client.host}"
    
    # Check rate limit
    rate_limiter = get_rate_limiter()
    allowed, error_msg = rate_limiter.check_rate_limit(identifier)
    
    if not allowed:
        raise HTTPException(status_code=429, detail=error_msg)
    
    response = await call_next(request)
    
    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = str(rate_limiter.requests_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(
        rate_limiter.requests_per_minute - len(rate_limiter.minute_windows.get(identifier, []))
    )
    
    return response

