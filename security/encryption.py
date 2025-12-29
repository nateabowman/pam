"""
Encryption utilities for World P.A.M.
Provides encryption for sensitive data at rest and in transit.
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional
from logger import get_logger


class EncryptionManager:
    """Manages encryption/decryption of sensitive data."""
    
    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize encryption manager.
        
        Args:
            key: Encryption key (if None, generates from environment or creates new)
        """
        self.logger = get_logger("encryption")
        
        if key:
            self.key = key
        else:
            # Try to get from environment
            env_key = os.getenv("PAM_ENCRYPTION_KEY")
            if env_key:
                try:
                    self.key = base64.urlsafe_b64decode(env_key.encode())
                except Exception:
                    self.logger.warning("Invalid encryption key in environment, generating new one")
                    self.key = self._generate_key()
            else:
                self.key = self._generate_key()
        
        self.cipher = Fernet(base64.urlsafe_b64encode(self.key))
    
    @staticmethod
    def _generate_key() -> bytes:
        """Generate a new encryption key."""
        return Fernet.generate_key()
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt string data.
        
        Args:
            data: Plaintext string
            
        Returns:
            Encrypted string (base64 encoded)
        """
        if not data:
            return ""
        
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            self.logger.error(f"Encryption error: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt string data.
        
        Args:
            encrypted_data: Encrypted string (base64 encoded)
            
        Returns:
            Decrypted plaintext string
        """
        if not encrypted_data:
            return ""
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            self.logger.error(f"Decryption error: {e}")
            raise
    
    def get_key_for_storage(self) -> str:
        """
        Get encryption key as base64 string for storage.
        
        Returns:
            Base64 encoded key string
        """
        return base64.urlsafe_b64encode(self.key).decode()


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """
    Derive encryption key from password using PBKDF2.
    
    Args:
        password: Password string
        salt: Salt bytes
        
    Returns:
        Derived key bytes
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return kdf.derive(password.encode())

