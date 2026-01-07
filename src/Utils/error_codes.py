"""
Registry všech chybových kódů používaných v GraphQL mutacích.

Každý error code má unikátní identifikátor a popisný text.
Tento registry slouží pro:
- Dokumentaci všech možných error codes
- Konzistentní použití napříč aplikací
- Export do GraphQL schema pro client-side handling
"""

ERROR_CODES = {
    # ========== User Authentication & Authorization Errors ==========
    "USER_NOT_FOUND": {
        "message": "User not found in authentication context",
        "category": "authentication",
        "description": "The user could not be retrieved from the authentication context. This usually means the user is not logged in or the session is invalid."
    },
    "USER_INVALID": {
        "message": "User missing required ID attribute",
        "category": "authentication",
        "description": "The user object exists but is missing the required ID attribute. This indicates an issue with user data structure."
    },
    
    # ========== API Key Errors ==========
    "INVALID_RATE_LIMITS": {
        "message": "Rate limits are not logically consistent",
        "category": "validation",
        "description": "Rate limits must satisfy: per_minute <= per_hour <= per_day. All values must be non-negative."
    },
    "INVALID_EXPIRATION": {
        "message": "Expiration date must be in the future",
        "category": "validation",
        "description": "The API key expiration date must be set to a future date. Past dates are not allowed."
    },
    "MAX_KEYS_EXCEEDED": {
        "message": "User has reached the maximum number of API keys",
        "category": "business_logic",
        "description": "The user has reached their maximum allowed number of active API keys. Deactivate an existing key before creating a new one."
    },
    "KEY_NOT_FOUND": {
        "message": "API key with given ID not found",
        "category": "not_found",
        "description": "The requested API key does not exist or has been deleted. Check the key ID and try again."
    },
    
    # ========== Optimistic Locking Errors ==========
    "OPTIMISTIC_LOCKING_CONFLICT": {
        "message": "Entity was modified by another request (lastchange mismatch)",
        "category": "concurrency",
        "description": "The entity was modified by another request before your changes could be saved. Refresh the entity and try again with the new lastchange value."
    },
    
    # ========== Duplicate Entry Errors ==========
    "DUPLICATE_ENTRY": {
        "message": "Entity with these attributes already exists",
        "category": "constraint",
        "description": "An entity with the same unique attributes already exists in the database. Modify the attributes or use the existing entity."
    },
    "DUPLICATE_INVITATION": {
        "message": "Invitation for this event and user already exists",
        "category": "constraint",
        "description": "An invitation for this event and user combination already exists. Check existing invitations or update the existing one."
    },
    
    # ========== Validation Errors ==========
    "VALIDATION_ERROR": {
        "message": "Input validation failed",
        "category": "validation",
        "description": "One or more input fields failed validation. Check the input data format and constraints."
    },
    "INVALID_INPUT": {
        "message": "Invalid input parameters provided",
        "category": "validation",
        "description": "The provided input parameters are invalid or do not match the expected format."
    },
    
    # ========== Not Found Errors ==========
    "ENTITY_NOT_FOUND": {
        "message": "Requested entity not found",
        "category": "not_found",
        "description": "The requested entity does not exist in the database. Check the ID and try again."
    },
    
    # ========== Permission Errors ==========
    "PERMISSION_DENIED": {
        "message": "Insufficient permissions to perform this action",
        "category": "authorization",
        "description": "You do not have the required permissions or roles to perform this operation. Contact an administrator if you need access."
    },
    "ADMIN_REQUIRED": {
        "message": "Administrator role required",
        "category": "authorization",
        "description": "This operation requires administrator privileges. Only users with administrator role can perform this action."
    },
    "NOT_AUTHORIZED": {
        "message": "You are not authorized",
        "category": "authorization",
        "description": "You do not have the required authorization to perform this operation. This may be due to insufficient roles or permissions."
    },
    "NOT_ORGANIZER": {
        "message": "You are not organizer",
        "category": "authorization",
        "description": "This operation can only be performed by the event organizer. Only users with organizer role for this event can perform this action."
    },
}

def get_error_description(code: str) -> str:
    """
    Get human-readable description for an error code.
    
    Args:
        code: Error code string (e.g., "USER_NOT_FOUND")
        
    Returns:
        Description string or default message if code not found
    """
    if code in ERROR_CODES:
        return ERROR_CODES[code].get("description", ERROR_CODES[code]["message"])
    return f"Unknown error code: {code}"

def get_error_message(code: str) -> str:
    """
    Get short error message for an error code.
    
    Args:
        code: Error code string
        
    Returns:
        Short message string or code itself if not found
    """
    if code in ERROR_CODES:
        return ERROR_CODES[code]["message"]
    return code

def get_error_category(code: str) -> str:
    """
    Get error category for an error code.
    
    Args:
        code: Error code string
        
    Returns:
        Category string or "unknown" if not found
    """
    if code in ERROR_CODES:
        return ERROR_CODES[code].get("category", "unknown")
    return "unknown"

def get_all_error_codes() -> dict:
    """
    Get all error codes with their metadata.
    
    Returns:
        Dictionary with all error codes and their descriptions
    """
    return ERROR_CODES

def validate_error_code(code: str) -> bool:
    """
    Check if an error code exists in the registry.
    
    Args:
        code: Error code string to validate
        
    Returns:
        True if code exists, False otherwise
    """
    return code in ERROR_CODES

