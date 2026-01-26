import uuid

from src.Utils.api_key_utils import generate_api_key, verify_token, API_KEY_PREFIX_LEN
from src.Utils.error_codes import get_error_code, ERROR_CODES
from src.GraphTypeDefinitions.UserGQLModel import validate_email


def test_generate_api_key_and_verify():
    raw, prefix, key_hash = generate_api_key()
    assert raw
    assert prefix == raw[:API_KEY_PREFIX_LEN]
    assert verify_token(raw, key_hash) is True


def test_error_code_is_uuid_and_stable():
    code = "USER_NOT_FOUND"
    uuid_a = get_error_code(code)
    uuid_b = get_error_code(code)
    assert uuid_a == uuid_b
    assert uuid.UUID(uuid_a)
    assert uuid_a != code
    assert code in ERROR_CODES


def test_validate_email():
    assert validate_email("john.doe@example.com") is True
    assert validate_email("invalid-email") is False
