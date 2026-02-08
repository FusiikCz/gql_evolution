import uuid
import os

from src.Utils.api_key_utils import generate_api_key, verify_token, hash_token, API_KEY_PREFIX_LEN
from src.Utils.error_codes import (
    get_error_code, 
    get_error_description,
    get_error_message,
    get_error_category,
    get_all_error_codes,
    validate_error_code,
    ERROR_CODES
)
from src.GraphTypeDefinitions.UserGQLModel import validate_email


# ========== API Key Utility Tests ==========

def test_generate_api_key_and_verify():
    """Test API key generation and verification"""
    raw, prefix, key_hash = generate_api_key()
    assert raw
    assert prefix == raw[:API_KEY_PREFIX_LEN]
    assert verify_token(raw, key_hash) is True


def test_hash_token():
    """Test token hashing function"""
    token = "test_token_123"
    hash1 = hash_token(token)
    hash2 = hash_token(token)
    
    # Same token should produce same hash
    assert hash1 == hash2
    # Hash should be different from original token
    assert hash1 != token
    # Hash should be hex string (64 chars for SHA256)
    assert len(hash1) == 64
    assert all(c in '0123456789abcdef' for c in hash1)


def test_hash_token_with_pepper():
    """Test token hashing with PEPPER environment variable"""
    original_pepper = os.environ.get("API_KEY_PEPPER", "")
    
    try:
        # Set PEPPER
        os.environ["API_KEY_PEPPER"] = "test_pepper"
        # Reload module to pick up new PEPPER
        import importlib
        import src.Utils.api_key_utils as api_key_utils_module
        importlib.reload(api_key_utils_module)
        
        token = "test_token"
        hash_with_pepper = api_key_utils_module.hash_token(token)
        
        # Remove PEPPER
        if "API_KEY_PEPPER" in os.environ:
            del os.environ["API_KEY_PEPPER"]
        importlib.reload(api_key_utils_module)
        
        hash_without_pepper = api_key_utils_module.hash_token(token)
        
        # Hashes should be different when PEPPER is used
        assert hash_with_pepper != hash_without_pepper
    finally:
        # Restore original PEPPER
        if original_pepper:
            os.environ["API_KEY_PEPPER"] = original_pepper
        else:
            os.environ.pop("API_KEY_PEPPER", None)
        # Reload module one more time to restore original state
        import importlib
        import src.Utils.api_key_utils as api_key_utils_module
        importlib.reload(api_key_utils_module)


def test_verify_token_fails_wrong_token():
    """Test that verify_token returns False for wrong token"""
    raw, prefix, key_hash = generate_api_key()
    wrong_token = "wrong_token_12345"
    
    assert verify_token(wrong_token, key_hash) is False


def test_verify_token_fails_wrong_hash():
    """Test that verify_token returns False for wrong hash"""
    raw, prefix, key_hash = generate_api_key()
    wrong_hash = "a" * 64  # Wrong hash
    
    assert verify_token(raw, wrong_hash) is False


# ========== Error Code Utility Tests ==========

def test_error_code_is_uuid_and_stable():
    """Test that error codes return stable UUIDs"""
    code = "USER_NOT_FOUND"
    uuid_a = get_error_code(code)
    uuid_b = get_error_code(code)
    assert uuid_a == uuid_b
    assert uuid.UUID(uuid_a)
    assert uuid_a != code
    assert code in ERROR_CODES


def test_get_error_description():
    """Test getting error descriptions"""
    # Valid code
    desc = get_error_description("USER_NOT_FOUND")
    assert desc
    assert isinstance(desc, str)
    assert "user" in desc.lower() or "authentication" in desc.lower()
    
    # Invalid code
    desc_invalid = get_error_description("NONEXISTENT_CODE")
    assert desc_invalid == "Unknown error code: NONEXISTENT_CODE"


def test_get_error_message():
    """Test getting error messages"""
    # Valid code
    msg = get_error_message("USER_NOT_FOUND")
    assert msg
    assert isinstance(msg, str)
    assert "User not found" in msg or "user" in msg.lower()
    
    # Invalid code
    msg_invalid = get_error_message("NONEXISTENT_CODE")
    assert msg_invalid == "NONEXISTENT_CODE"


def test_get_error_category():
    """Test getting error categories"""
    # Valid code
    category = get_error_category("USER_NOT_FOUND")
    assert category == "authentication"
    
    category2 = get_error_category("INVALID_EMAIL")
    assert category2 == "validation"
    
    # Invalid code
    category_invalid = get_error_category("NONEXISTENT_CODE")
    assert category_invalid == "unknown"


def test_get_all_error_codes():
    """Test getting all error codes"""
    all_codes = get_all_error_codes()
    assert isinstance(all_codes, dict)
    assert len(all_codes) > 0
    assert "USER_NOT_FOUND" in all_codes
    assert "INVALID_EMAIL" in all_codes
    assert all("uuid" in meta for meta in all_codes.values())


def test_validate_error_code():
    """Test validating error codes"""
    # Valid codes
    assert validate_error_code("USER_NOT_FOUND") is True
    assert validate_error_code("INVALID_EMAIL") is True
    assert validate_error_code("OPTIMISTIC_LOCKING_CONFLICT") is True
    
    # Invalid codes
    assert validate_error_code("NONEXISTENT_CODE") is False
    assert validate_error_code("") is False
    assert validate_error_code(None) is False


def test_error_code_has_uuid():
    """Test that all error codes have UUIDs"""
    for code, meta in ERROR_CODES.items():
        assert "uuid" in meta, f"Error code {code} missing UUID"
        uuid_str = meta["uuid"]
        # Validate it's a valid UUID
        uuid.UUID(uuid_str)


# ========== Email Validation Tests ==========

def test_validate_email():
    """Test email validation with valid emails"""
    assert validate_email("john.doe@example.com") is True
    assert validate_email("user@domain.co.uk") is True
    assert validate_email("test+tag@example.org") is True
    assert validate_email("user_name@sub.domain.com") is True


def test_validate_email_invalid():
    """Test email validation with invalid emails"""
    assert validate_email("invalid-email") is False
    assert validate_email("missing@domain") is False
    assert validate_email("@domain.com") is False
    assert validate_email("user@") is False
    assert validate_email("user@domain") is False  # Missing TLD
    assert validate_email("user space@domain.com") is False


def test_validate_email_optional():
    """Test that email validation allows None/empty (optional field)"""
    assert validate_email(None) is True
    assert validate_email("") is True  # Empty string is considered optional
