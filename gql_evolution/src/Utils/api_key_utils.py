"""
Utility functions for API key generation and management
"""
import hashlib
import secrets
import os

# Configuration
API_KEY_PREFIX_LEN = int(os.getenv("API_KEY_PREFIX_LEN", "8"))
API_KEY_BYTES = int(os.getenv("API_KEY_BYTES", "32"))  # entropy ~ 256 bits
API_KEY_PEPPER = os.getenv("API_KEY_PEPPER", "")  # optional server-side secret for hashing


def hash_token(raw_token: str) -> str:
    """
    Hash an API key token using SHA256.
    
    Args:
        raw_token: The plaintext API key
        
    Returns:
        Hex digest of the hashed token
    """
    return hashlib.sha256((API_KEY_PEPPER + raw_token).encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.
    
    Returns:
        Tuple of (plaintext, prefix, hash)
        - plaintext: Full API key that should be shown once to user
        - prefix: First N characters for identification
        - hash: SHA256 hash of the plaintext for storage
    """
    # Generate URL-safe random token
    raw = secrets.token_urlsafe(API_KEY_BYTES).replace("-", "").replace("_", "")
    # Extract prefix for fast lookups
    prefix = raw[:API_KEY_PREFIX_LEN]
    # Hash for secure storage
    key_hash = hash_token(raw)
    return raw, prefix, key_hash


def verify_token(plaintext: str, stored_hash: str) -> bool:
    """
    Verify if a plaintext token matches a stored hash.
    
    Args:
        plaintext: The plaintext API key to verify
        stored_hash: The stored hash to compare against
        
    Returns:
        True if token matches, False otherwise
    """
    return secrets.compare_digest(hash_token(plaintext), stored_hash)

