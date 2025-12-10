"""
Encryption utilities for secure API key storage.
"""
import os
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config import settings


def _get_cipher() -> Fernet:
    """Get or create encryption cipher."""
    key = settings.encryption_key
    key_file = settings.data_dir / ".encryption_key"
    
    if key is None:
        # Try to load existing key from file
        if key_file.exists():
            key = key_file.read_text().strip()
        else:
            # Generate and save a new key
            key = Fernet.generate_key().decode()
            key_file.write_text(key)
            print(f"[INFO] Generated new encryption key and saved to {key_file}")
    else:
        # If key is a passphrase, derive a proper key from it
        if len(key) != 44:  # Fernet keys are 44 chars base64
            salt = b"deeprp_salt_v1"  # Fixed salt for reproducibility
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=480000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(key.encode())).decode()
    
    return Fernet(key.encode())


_cipher = None


def get_cipher() -> Fernet:
    """Get cached cipher instance."""
    global _cipher
    if _cipher is None:
        _cipher = _get_cipher()
    return _cipher


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for storage."""
    cipher = get_cipher()
    return cipher.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key from storage."""
    cipher = get_cipher()
    return cipher.decrypt(encrypted_key.encode()).decode()
