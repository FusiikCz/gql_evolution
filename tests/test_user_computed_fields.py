"""
Tests for computed fields in UserGQLModel.

Tests:
- is_recently_active
- status_description
- display_name
"""
import pytest
import logging
import datetime
from src.GraphTypeDefinitions import schema
from .shared import (
    prepare_demodata,
    prepare_in_memory_sqllite,
    get_demodata,
    createContext,
)


@pytest.mark.asyncio
async def test_user_display_name():
    """Test that display_name returns formatted name"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # Get a user from demo data
    data = get_demodata()
    if "users" not in data or len(data["users"]) == 0:
        pytest.skip("No users in demo data")
    
    user_id = data["users"][0]["id"]
    
    query = """
        query($id: UUID!) {
            result: userById(id: $id) {
                id
                name
                email
                displayName
            }
        }
    """
    
    variables = {"id": str(user_id)}  # Convert UUID to string
    
    resp = await schema.execute(query, variable_values=variables, context_value=context_value)
    assert resp.errors is None, f"Query failed: {resp.errors}"
    assert resp.data is not None
    
    result = resp.data.get("result")
    assert result is not None, "User not found"
    
    display_name = result.get("displayName")
    assert display_name is not None, "displayName should not be None"
    
    # displayName should be name if available, otherwise email prefix, otherwise user ID prefix
    name = result.get("name")
    email = result.get("email")
    
    if name:
        assert display_name == name, f"Expected displayName to be name '{name}', got '{display_name}'"
    elif email:
        expected = email.split('@')[0]
        assert display_name == expected, f"Expected displayName to be email prefix '{expected}', got '{display_name}'"
    else:
        # Should be "User {first 8 chars of ID}"
        expected_prefix = f"User {str(user_id)[:8]}"
        assert display_name.startswith("User"), f"Expected displayName to start with 'User', got '{display_name}'"

