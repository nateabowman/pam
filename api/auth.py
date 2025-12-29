"""
API authentication middleware for World P.A.M.
"""

from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
import os

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Simple API key storage (in production, use proper secret management)
_api_keys: set[str] = set()


def get_api_key_from_env() -> Optional[str]:
    """Get API key from environment variable."""
    return os.getenv("PAM_API_KEY")


def add_api_key(key: str):
    """Add an API key."""
    _api_keys.add(key)


def is_valid_api_key(key: Optional[str]) -> bool:
    """Check if API key is valid."""
    if not key:
        return False
    
    # Check environment variable
    env_key = get_api_key_from_env()
    if env_key and key == env_key:
        return True
    
    # Check stored keys
    return key in _api_keys


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """
    Verify API key from header.
    
    Args:
        api_key: API key from header
        
    Returns:
        API key if valid
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not is_valid_api_key(api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )
    return api_key

