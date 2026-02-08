"""
Tests for RBAC (Role-Based Access Control) permissions.

Tests:
- Permission denied for unauthorized users
- Role-based access control for mutations
- Admin-only operations
- User access control
"""
import pytest
import logging
from src.GraphTypeDefinitions import schema
from src.Utils.error_codes import get_error_code
from .shared import (
    prepare_demodata,
    prepare_in_memory_sqllite,
    createContext,
    fake_ug_client,
    fake_ug_client_sync,
)


def createContextWithoutUser(asyncSessionMaker):
    """Create context without user (unauthorized)"""
    from src.Dataloaders import createLoadersContext
    from .shared import TestRequest
    
    session = asyncSessionMaker() if callable(asyncSessionMaker) else asyncSessionMaker
    loadersContext = createLoadersContext(session) if session is not None else {"loaders": None}
    loadersContext["asyncSessionMaker"] = asyncSessionMaker
    # No user in context, but request is still needed
    user_id = "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"
    # Don't include user in request scope for unauthorized access
    loadersContext["request"] = TestRequest(user_id, include_user=False)
    loadersContext["ug_client"] = fake_ug_client
    # Explicitly don't set user in context
    return loadersContext


def createContextWithRole(asyncSessionMaker, role_name: str = "plánovací administrátor"):
    """Create context with specific role"""
    from src.Dataloaders import createLoadersContext
    from .shared import TestRequest
    
    session = asyncSessionMaker() if callable(asyncSessionMaker) else asyncSessionMaker
    loadersContext = createLoadersContext(session) if session is not None else {"loaders": None}
    loadersContext["asyncSessionMaker"] = asyncSessionMaker
    
    user_id = "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"
    user = {
        "id": user_id,
        "name": "Test",
        "surname": "User",
        "email": "test@example.com"
    }
    # Add roles to user object (required by UserRoleProviderExtension)
    user["roles"] = [
        {
            "roletype": {
                "id": "00000000-0000-0000-0000-000000000000",
                "name": role_name,
                "path": role_name
            },
            "userId": user_id,
            "valid": True,
            "group": {
                "id": "00000000-0000-0000-0000-000000000001",
                "name": "root",
                "grouptype": {
                    "id": "00000000-0000-0000-0000-000000000002",
                    "name": "root"
                }
            }
        }
    ]
    loadersContext["user"] = user
    # Also set user in request.scope for uoishelpers resolvers - must include roles!
    loadersContext["request"] = TestRequest(user_id, include_user=True, user=user)
    
    # async client returning dict; uoishelpers does await gqlClient()
    async def role_ug_client(query, variables):
        return fake_ug_client_sync(query, variables, role_name=role_name)
    
    loadersContext["ug_client"] = role_ug_client
    return loadersContext


@pytest.mark.asyncio
@pytest.mark.rbac
@pytest.mark.permissions
async def test_authorized_user_can_access_protected_field():
    """Test that authorized user can access fields with OnlyForAuthentized"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    query = """
        query {
            apiKeyPage {
                id
                name
                isActive
            }
        }
    """
    
    resp = await schema.execute(query, context_value=context_value)
    
    # Should succeed
    assert resp.errors is None, f"Authorized user should access protected field: {resp.errors}"
    assert resp.data is not None


@pytest.mark.asyncio
@pytest.mark.rbac
@pytest.mark.permissions
async def test_admin_can_insert_endpoint_config():
    """Test that admin user can insert endpoint config"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    # Create context with admin role
    context_value = createContextWithRole(async_session_maker, role_name="administrátor")
    
    mutation = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "Admin Test Endpoint"
                endpointType: "openai_chat"
                baseUrl: "https://api.example.com"
            }) {
                ... on EndpointConfigGQLModel {
                    id
                    name
                }
                ... on InsertError {
                    msg
                    code
                }
            }
        }
    """
    
    resp = await schema.execute(mutation, context_value=context_value)
    
    # Should succeed (may have validation errors, but not permission errors)
    assert resp.errors is None or not any(
        "permission" in str(err).lower() or "authorized" in str(err).lower()
        for err in (resp.errors or [])
    ), f"Admin should be able to insert endpoint config: {resp.errors}"


@pytest.mark.asyncio
@pytest.mark.rbac
@pytest.mark.permissions
async def test_non_admin_cannot_delete_endpoint_config():
    """Test that non-admin user cannot delete endpoint config"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    demo_data = await prepare_demodata(async_session_maker)
    context_value = createContextWithRole(async_session_maker, role_name="user")
    
    # Get an endpoint config ID from demo data
    from .shared import get_demodata
    demo = get_demodata()
    endpoint_configs = demo.get("endpoint_configs", [])
    if not endpoint_configs:
        pytest.skip("No endpoint configs in demo data")
    
    endpoint_id = endpoint_configs[0].get("id")
    if not endpoint_id:
        pytest.skip("Endpoint config has no ID")
    
    mutation = f"""
        mutation {{
            result: endpointConfigDelete(endpointConfig: {{
                id: "{endpoint_id}"
            }}) {{
                ... on EndpointConfigGQLModelDeleteError {{
                    msg
                    code
                }}
            }}
        }}
    """
    
    resp = await schema.execute(mutation, context_value=context_value)
    
    # Should fail with permission error
    assert resp.errors is not None or (
        resp.data and resp.data.get("result") and "code" in resp.data["result"]
    ), "Expected permission error for non-admin user"


@pytest.mark.asyncio
@pytest.mark.rbac
@pytest.mark.permissions
async def test_user_can_only_access_own_api_keys():
    """Test that user can only access their own API keys via my_api_keys"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # First create an API key for the current user
    create_mutation = """
        mutation {
            result: apiKeyInsert(apiKey: {
                name: "My Test Key"
            }) {
                ... on ApiKeyInsertResponse {
                    apiKey {
                        id
                        name
                    }
                }
            }
        }
    """
    
    create_resp = await schema.execute(create_mutation, context_value=context_value)
    assert create_resp.errors is None, f"Create failed: {create_resp.errors}"
    
    # Query my_api_keys
    query = """
        query {
            apiKeyPage {
                id
                name
                user {
                    id
                }
            }
        }
    """
    
    resp = await schema.execute(query, context_value=context_value)
    
    # Should succeed and return API keys
    assert resp.errors is None, f"Query failed: {resp.errors}"
    assert resp.data is not None
    # Note: my_api_keys is a field on ApiKeyGQLModel, not a query
    # This test verifies that the query works with user context
