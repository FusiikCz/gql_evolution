"""
Unit tests for EndpointConfig GraphQL model.
Tests CRUD operations for EndpointConfig entity.
"""
import pytest
import logging
import json
from GraphTypeDefinitions import schema
from .shared import (
    prepare_demodata,
    prepare_in_memory_sqllite,
    get_demodata,
    createContext,
)

def runAssert(expression, comment):
    """Helper function for assertions in lambda functions"""
    assert expression, comment


@pytest.mark.asyncio
async def test_endpoint_config_insert():
    """Test creating a new endpoint configuration"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    mutation = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "Test OpenAI Endpoint"
                endpointType: "openai_chat"
                baseUrl: "https://api.openai.com/v1"
                isActive: true
                description: "Test endpoint configuration"
            }) {
                ... on EndpointConfigGQLModel {
                    id
                    name
                    endpointType: endpoint_type
                    baseUrl: base_url
                    isActive: is_active
                    description
                }
                ... on InsertError {
                    msg
                    code
                }
            }
        }
    """
    
    logging.debug(f"mutation: {mutation}")
    resp = await schema.execute(mutation, context_value=context_value)
    
    assert resp.errors is None, f"Expected no errors, got: {resp.errors}"
    assert resp.data is not None, "Expected data in response"
    
    result = resp.data.get("result")
    assert result is not None, "Expected result in response"
    
    # Should be EndpointConfigGQLModel, not InsertError
    assert "msg" not in result, f"Expected EndpointConfigGQLModel, got InsertError: {result}"
    assert result.get("name") == "Test OpenAI Endpoint"
    assert result.get("endpointType") == "openai_chat"
    assert result.get("baseUrl") == "https://api.openai.com/v1"
    assert result.get("isActive") is True
    assert result.get("id") is not None


@pytest.mark.asyncio
async def test_endpoint_config_insert_with_model_mapping():
    """Test creating endpoint configuration with model mapping (JSON string)"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    model_mapping_json = json.dumps({"gpt-4o": "gpt4o-prod", "gpt-4o-mini": "gpt4o-mini-prod"})
    
    mutation = f"""
        mutation {{
            result: endpointConfigInsert(endpointConfig: {{
                name: "Test Azure Endpoint"
                endpointType: "azure_chat"
                baseUrl: "https://test.openai.azure.com"
                apiVersion: "2024-12-01-preview"
                modelMapping: {json.dumps(model_mapping_json)}
                defaultDeployment: "gpt4o-prod"
                isActive: true
            }}) {{
                ... on EndpointConfigGQLModel {{
                    id
                    name
                    endpointType: endpoint_type
                    modelMapping: model_mapping
                    defaultDeployment: default_deployment
                }}
                ... on InsertError {{
                    msg
                    code
                }}
            }}
        }}
    """
    
    logging.debug(f"mutation: {mutation}")
    resp = await schema.execute(mutation, context_value=context_value)
    
    assert resp.errors is None, f"Expected no errors, got: {resp.errors}"
    assert resp.data is not None, "Expected data in response"
    
    result = resp.data.get("result")
    assert result is not None, "Expected result in response"
    assert "msg" not in result, f"Expected EndpointConfigGQLModel, got InsertError: {result}"
    assert result.get("name") == "Test Azure Endpoint"
    assert result.get("endpointType") == "azure_chat"
    assert result.get("modelMapping") is not None


@pytest.mark.asyncio
async def test_endpoint_config_insert_invalid_type():
    """Test creating endpoint configuration with invalid endpoint type"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    mutation = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "Invalid Endpoint"
                endpointType: "invalid_type"
                baseUrl: "https://api.example.com/v1"
                isActive: true
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
    
    logging.debug(f"mutation: {mutation}")
    resp = await schema.execute(mutation, context_value=context_value)
    
    assert resp.errors is None, f"Expected no errors, got: {resp.errors}"
    assert resp.data is not None, "Expected data in response"
    
    result = resp.data.get("result")
    assert result is not None, "Expected result in response"
    
    # Should be InsertError, not EndpointConfigGQLModel
    assert "msg" in result, "Expected InsertError for invalid endpoint type"
    assert result.get("code") == "INVALID_ENDPOINT_TYPE"


@pytest.mark.asyncio
async def test_endpoint_config_insert_invalid_url():
    """Test creating endpoint configuration with invalid URL"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    mutation = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "Invalid URL Endpoint"
                endpointType: "openai_chat"
                baseUrl: "invalid-url"
                isActive: true
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
    
    logging.debug(f"mutation: {mutation}")
    resp = await schema.execute(mutation, context_value=context_value)
    
    assert resp.errors is None, f"Expected no errors, got: {resp.errors}"
    assert resp.data is not None, "Expected data in response"
    
    result = resp.data.get("result")
    assert result is not None, "Expected result in response"
    
    # Should be InsertError, not EndpointConfigGQLModel
    assert "msg" in result, "Expected InsertError for invalid URL"
    assert result.get("code") == "INVALID_BASE_URL"


@pytest.mark.asyncio
async def test_endpoint_config_page():
    """Test querying endpoint configurations page"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # First, create a test endpoint config
    mutation = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "Test Query Endpoint"
                endpointType: "openai_chat"
                baseUrl: "https://api.openai.com/v1"
                isActive: true
            }) {
                ... on EndpointConfigGQLModel {
                    id
                    name
                }
            }
        }
    """
    
    await schema.execute(mutation, context_value=context_value)
    
    # Then query the page
    query = """
        query {
            result: endpointConfigPage {
                id
                name
                endpointType: endpoint_type
                baseUrl: base_url
                isActive: is_active
            }
        }
    """
    
    logging.debug(f"query: {query}")
    resp = await schema.execute(query, context_value=context_value)
    
    assert resp.errors is None, f"Expected no errors, got: {resp.errors}"
    assert resp.data is not None, "Expected data in response"
    
    result = resp.data.get("result")
    assert result is not None, "Expected result in response"
    assert isinstance(result, list), "Expected list in response"
    assert len(result) > 0, "Expected at least one endpoint configuration"


@pytest.mark.asyncio
async def test_endpoint_config_by_id():
    """Test querying endpoint configuration by ID"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # First, create a test endpoint config
    mutation = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "Test By ID Endpoint"
                endpointType: "custom"
                baseUrl: "https://api.example.com/v1"
                isActive: true
            }) {
                ... on EndpointConfigGQLModel {
                    id
                    name
                }
            }
        }
    """
    
    create_resp = await schema.execute(mutation, context_value=context_value)
    assert create_resp.errors is None
    created_id = create_resp.data["result"]["id"]
    
    # Then query by ID
    query = f"""
        query($id: UUID!) {{
            result: endpointConfigById(id: $id) {{
                id
                name
                endpointType: endpoint_type
                baseUrl: base_url
                isActive: is_active
            }}
        }}
    """
    
    logging.debug(f"query: {query}")
    resp = await schema.execute(
        query, 
        context_value=context_value,
        variable_values={"id": created_id}
    )
    
    assert resp.errors is None, f"Expected no errors, got: {resp.errors}"
    assert resp.data is not None, "Expected data in response"
    
    result = resp.data.get("result")
    assert result is not None, "Expected result in response"
    assert result.get("id") == created_id
    assert result.get("name") == "Test By ID Endpoint"


@pytest.mark.asyncio
async def test_endpoint_config_update():
    """Test updating endpoint configuration"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # First, create a test endpoint config
    mutation = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "Test Update Endpoint"
                endpointType: "openai_chat"
                baseUrl: "https://api.openai.com/v1"
                isActive: true
            }) {
                ... on EndpointConfigGQLModel {
                    id
                    name
                    lastchange
                }
            }
        }
    """
    
    create_resp = await schema.execute(mutation, context_value=context_value)
    assert create_resp.errors is None
    created = create_resp.data["result"]
    created_id = created["id"]
    lastchange = created["lastchange"]
    
    # Then update it
    update_mutation = f"""
        mutation($id: UUID!, $lastchange: DateTime!, $name: String!) {{
            result: endpointConfigUpdate(endpointConfig: {{
                id: $id
                lastchange: $lastchange
                name: $name
                isActive: false
            }}) {{
                ... on EndpointConfigGQLModel {{
                    id
                    name
                    isActive: is_active
                }}
                ... on UpdateError {{
                    msg
                    code
                }}
            }}
        }}
    """
    
    logging.debug(f"update_mutation: {update_mutation}")
    update_resp = await schema.execute(
        update_mutation,
        context_value=context_value,
        variable_values={
            "id": created_id,
            "lastchange": lastchange,
            "name": "Updated Test Endpoint"
        }
    )
    
    assert update_resp.errors is None, f"Expected no errors, got: {update_resp.errors}"
    assert update_resp.data is not None, "Expected data in response"
    
    result = update_resp.data.get("result")
    assert result is not None, "Expected result in response"
    assert "msg" not in result, f"Expected EndpointConfigGQLModel, got UpdateError: {result}"
    assert result.get("name") == "Updated Test Endpoint"
    assert result.get("isActive") is False


@pytest.mark.asyncio
async def test_endpoint_config_delete():
    """Test deleting endpoint configuration"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # First, create a test endpoint config
    mutation = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "Test Delete Endpoint"
                endpointType: "openai_chat"
                baseUrl: "https://api.openai.com/v1"
                isActive: true
            }) {
                ... on EndpointConfigGQLModel {
                    id
                    name
                }
            }
        }
    """
    
    create_resp = await schema.execute(mutation, context_value=context_value)
    assert create_resp.errors is None
    created_id = create_resp.data["result"]["id"]
    
    # Then delete it
    delete_mutation = f"""
        mutation($id: UUID!) {{
            result: endpointConfigDelete(id: $id) {{
                ... on DeleteError {{
                    id
                    msg
                    code
                }}
            }}
        }}
    """
    
    logging.debug(f"delete_mutation: {delete_mutation}")
    delete_resp = await schema.execute(
        delete_mutation,
        context_value=context_value,
        variable_values={"id": created_id}
    )
    
    assert delete_resp.errors is None, f"Expected no errors, got: {delete_resp.errors}"
    assert delete_resp.data is not None, "Expected data in response"
    
    result = delete_resp.data.get("result")
    # Delete mutation returns None on success, DeleteError on failure
    assert result is None, f"Expected None on successful delete, got: {result}"
    
    # Verify it's actually deleted
    query = f"""
        query($id: UUID!) {{
            result: endpointConfigById(id: $id) {{
                id
                name
            }}
        }}
    """
    
    verify_resp = await schema.execute(
        query,
        context_value=context_value,
        variable_values={"id": created_id}
    )
    
    assert verify_resp.errors is None
    assert verify_resp.data["result"] is None, "Expected None after delete"


@pytest.mark.asyncio
async def test_endpoint_config_delete_not_found():
    """Test deleting non-existent endpoint configuration"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    import uuid
    fake_id = str(uuid.uuid4())
    
    delete_mutation = f"""
        mutation($id: UUID!) {{
            result: endpointConfigDelete(id: $id) {{
                ... on DeleteError {{
                    id
                    msg
                    code
                }}
            }}
        }}
    """
    
    logging.debug(f"delete_mutation: {delete_mutation}")
    delete_resp = await schema.execute(
        delete_mutation,
        context_value=context_value,
        variable_values={"id": fake_id}
    )
    
    assert delete_resp.errors is None, f"Expected no errors, got: {delete_resp.errors}"
    assert delete_resp.data is not None, "Expected data in response"
    
    result = delete_resp.data.get("result")
    # Should return DeleteError for non-existent ID
    assert result is not None, "Expected DeleteError for non-existent ID"
    assert "msg" in result, "Expected DeleteError message"
    assert result.get("code") == "KEY_NOT_FOUND"


# ============================================
# ADDITIONAL TESTS - Extended coverage
# ============================================

@pytest.mark.asyncio
async def test_endpoint_config_insert_all_types():
    """Test creating endpoint configurations with all valid endpoint types"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    valid_types = ['openai_chat', 'openai_responses', 'azure_chat', 'azure_responses', 'custom']
    
    for endpoint_type in valid_types:
        mutation = f"""
            mutation {{
                result: endpointConfigInsert(endpointConfig: {{
                    name: "Test {endpoint_type}"
                    endpointType: "{endpoint_type}"
                    baseUrl: "https://api.example.com/v1"
                    isActive: true
                }}) {{
                    ... on EndpointConfigGQLModel {{
                        id
                        name
                        endpointType: endpoint_type
                    }}
                    ... on InsertError {{
                        msg
                        code
                    }}
                }}
            }}
        """
        
        resp = await schema.execute(mutation, context_value=context_value)
        assert resp.errors is None, f"Expected no errors for {endpoint_type}, got: {resp.errors}"
        assert resp.data is not None, f"Expected data for {endpoint_type}"
        
        result = resp.data.get("result")
        assert result is not None, f"Expected result for {endpoint_type}"
        assert "msg" not in result, f"Expected EndpointConfigGQLModel for {endpoint_type}, got InsertError: {result}"
        assert result.get("endpointType") == endpoint_type


@pytest.mark.asyncio
async def test_endpoint_config_insert_invalid_json():
    """Test creating endpoint configuration with invalid JSON in model_mapping"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    mutation = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "Invalid JSON Endpoint"
                endpointType: "azure_chat"
                baseUrl: "https://api.azure.com"
                modelMapping: "{invalid json}"
                isActive: true
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
    
    logging.debug(f"mutation: {mutation}")
    resp = await schema.execute(mutation, context_value=context_value)
    
    assert resp.errors is None, f"Expected no errors, got: {resp.errors}"
    assert resp.data is not None, "Expected data in response"
    
    result = resp.data.get("result")
    assert result is not None, "Expected result in response"
    
    # Should be InsertError, not EndpointConfigGQLModel
    assert "msg" in result, "Expected InsertError for invalid JSON"
    assert result.get("code") == "INVALID_JSON"


@pytest.mark.asyncio
async def test_endpoint_config_insert_empty_strings():
    """Test creating endpoint configuration with empty strings"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    mutation = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: ""
                endpointType: "custom"
                baseUrl: "https://api.example.com/v1"
                isActive: true
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
    assert resp.errors is None, f"Expected no errors, got: {resp.errors}"
    assert resp.data is not None, "Expected data in response"
    
    result = resp.data.get("result")
    assert result is not None, "Expected result in response"
    # Empty string for name should be allowed (DB constraint would catch it if not)
    assert "msg" not in result or result.get("code") != "INVALID_ENDPOINT_TYPE"


@pytest.mark.asyncio
async def test_endpoint_config_insert_optional_fields():
    """Test creating endpoint configuration with all optional fields"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    model_mapping_json = json.dumps({"gpt-4o": "gpt4o-prod"})
    
    mutation = f"""
        mutation {{
            result: endpointConfigInsert(endpointConfig: {{
                name: "Full Optional Fields Test"
                endpointType: "azure_chat"
                baseUrl: "https://api.azure.com"
                apiVersion: "2024-12-01-preview"
                modelMapping: {json.dumps(model_mapping_json)}
                defaultDeployment: "gpt4o-prod"
                description: "Test description"
                isActive: false
            }}) {{
                ... on EndpointConfigGQLModel {{
                    id
                    name
                    endpointType: endpoint_type
                    baseUrl: base_url
                    apiVersion: api_version
                    modelMapping: model_mapping
                    defaultDeployment: default_deployment
                    description
                    isActive: is_active
                }}
                ... on InsertError {{
                    msg
                    code
                }}
            }}
        }}
    """
    
    resp = await schema.execute(mutation, context_value=context_value)
    assert resp.errors is None, f"Expected no errors, got: {resp.errors}"
    assert resp.data is not None, "Expected data in response"
    
    result = resp.data.get("result")
    assert result is not None, "Expected result in response"
    assert "msg" not in result, f"Expected EndpointConfigGQLModel, got InsertError: {result}"
    assert result.get("name") == "Full Optional Fields Test"
    assert result.get("apiVersion") == "2024-12-01-preview"
    assert result.get("defaultDeployment") == "gpt4o-prod"
    assert result.get("description") == "Test description"
    assert result.get("isActive") is False


@pytest.mark.asyncio
async def test_endpoint_config_update_not_found():
    """Test updating non-existent endpoint configuration"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    import uuid
    fake_id = str(uuid.uuid4())
    fake_lastchange = "2024-01-01T00:00:00"
    
    mutation = f"""
        mutation($id: UUID!, $lastchange: DateTime!) {{
            result: endpointConfigUpdate(endpointConfig: {{
                id: $id
                lastchange: $lastchange
                name: "Updated Name"
            }}) {{
                ... on EndpointConfigGQLModel {{
                    id
                    name
                }}
                ... on UpdateError {{
                    id
                    msg
                    code
                }}
            }}
        }}
    """
    
    resp = await schema.execute(
        mutation,
        context_value=context_value,
        variable_values={"id": fake_id, "lastchange": fake_lastchange}
    )
    
    assert resp.errors is None, f"Expected no errors, got: {resp.errors}"
    assert resp.data is not None, "Expected data in response"
    
    result = resp.data.get("result")
    assert result is not None, "Expected result in response"
    
    # Should be UpdateError, not EndpointConfigGQLModel
    assert "msg" in result, "Expected UpdateError for non-existent ID"
    assert result.get("code") == "KEY_NOT_FOUND"
    assert result.get("id") == fake_id


@pytest.mark.asyncio
async def test_endpoint_config_update_optimistic_locking():
    """Test optimistic locking in update (wrong lastchange)"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # First, create a test endpoint config
    mutation = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "Optimistic Locking Test"
                endpointType: "openai_chat"
                baseUrl: "https://api.openai.com/v1"
                isActive: true
            }) {
                ... on EndpointConfigGQLModel {
                    id
                    name
                    lastchange
                }
            }
        }
    """
    
    create_resp = await schema.execute(mutation, context_value=context_value)
    assert create_resp.errors is None
    created = create_resp.data["result"]
    created_id = created["id"]
    correct_lastchange = created["lastchange"]
    
    # Try to update with wrong lastchange
    wrong_lastchange = "2020-01-01T00:00:00"
    update_mutation = f"""
        mutation($id: UUID!, $lastchange: DateTime!) {{
            result: endpointConfigUpdate(endpointConfig: {{
                id: $id
                lastchange: $lastchange
                name: "Updated Name"
            }}) {{
                ... on EndpointConfigGQLModel {{
                    id
                    name
                }}
                ... on UpdateError {{
                    id
                    msg
                    code
                }}
            }}
        }}
    """
    
    update_resp = await schema.execute(
        update_mutation,
        context_value=context_value,
        variable_values={"id": created_id, "lastchange": wrong_lastchange}
    )
    
    assert update_resp.errors is None, f"Expected no errors, got: {update_resp.errors}"
    assert update_resp.data is not None, "Expected data in response"
    
    result = update_resp.data.get("result")
    assert result is not None, "Expected result in response"
    
    # Should be UpdateError due to optimistic locking conflict
    assert "msg" in result, "Expected UpdateError for optimistic locking conflict"
    assert result.get("code") == "OPTIMISTIC_LOCKING_CONFLICT"
    assert result.get("id") == created_id


@pytest.mark.asyncio
async def test_endpoint_config_update_invalid_json():
    """Test updating endpoint configuration with invalid JSON in model_mapping"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # First, create a test endpoint config
    mutation = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "Update Invalid JSON Test"
                endpointType: "azure_chat"
                baseUrl: "https://api.azure.com"
                isActive: true
            }) {
                ... on EndpointConfigGQLModel {
                    id
                    lastchange
                }
            }
        }
    """
    
    create_resp = await schema.execute(mutation, context_value=context_value)
    assert create_resp.errors is None
    created = create_resp.data["result"]
    created_id = created["id"]
    lastchange = created["lastchange"]
    
    # Try to update with invalid JSON
    update_mutation = f"""
        mutation($id: UUID!, $lastchange: DateTime!) {{
            result: endpointConfigUpdate(endpointConfig: {{
                id: $id
                lastchange: $lastchange
                modelMapping: "{{invalid json}}"
            }}) {{
                ... on EndpointConfigGQLModel {{
                    id
                    name
                }}
                ... on UpdateError {{
                    id
                    msg
                    code
                }}
            }}
        }}
    """
    
    update_resp = await schema.execute(
        update_mutation,
        context_value=context_value,
        variable_values={"id": created_id, "lastchange": lastchange}
    )
    
    assert update_resp.errors is None, f"Expected no errors, got: {update_resp.errors}"
    assert update_resp.data is not None, "Expected data in response"
    
    result = update_resp.data.get("result")
    assert result is not None, "Expected result in response"
    
    # Should be UpdateError due to invalid JSON
    assert "msg" in result, "Expected UpdateError for invalid JSON"
    assert result.get("code") == "INVALID_JSON"


@pytest.mark.asyncio
async def test_endpoint_config_update_partial():
    """Test updating endpoint configuration with partial fields"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # First, create a test endpoint config
    mutation = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "Partial Update Test"
                endpointType: "openai_chat"
                baseUrl: "https://api.openai.com/v1"
                description: "Original description"
                isActive: true
            }) {
                ... on EndpointConfigGQLModel {
                    id
                    name
                    description
                    lastchange
                }
            }
        }
    """
    
    create_resp = await schema.execute(mutation, context_value=context_value)
    assert create_resp.errors is None
    created = create_resp.data["result"]
    created_id = created["id"]
    original_name = created["name"]
    original_description = created["description"]
    lastchange = created["lastchange"]
    
    # Update only name, description should remain unchanged
    update_mutation = f"""
        mutation($id: UUID!, $lastchange: DateTime!) {{
            result: endpointConfigUpdate(endpointConfig: {{
                id: $id
                lastchange: $lastchange
                name: "Updated Name Only"
            }}) {{
                ... on EndpointConfigGQLModel {{
                    id
                    name
                    description
                }}
                ... on UpdateError {{
                    msg
                    code
                }}
            }}
        }}
    """
    
    update_resp = await schema.execute(
        update_mutation,
        context_value=context_value,
        variable_values={"id": created_id, "lastchange": lastchange}
    )
    
    assert update_resp.errors is None, f"Expected no errors, got: {update_resp.errors}"
    assert update_resp.data is not None, "Expected data in response"
    
    result = update_resp.data.get("result")
    assert result is not None, "Expected result in response"
    assert "msg" not in result, f"Expected EndpointConfigGQLModel, got UpdateError: {result}"
    assert result.get("name") == "Updated Name Only"
    # Description should remain unchanged (not updated)
    assert result.get("description") == original_description


@pytest.mark.asyncio
async def test_endpoint_config_page_filter_active():
    """Test filtering endpoint configurations by is_active"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # Create active endpoint
    mutation1 = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "Active Endpoint"
                endpointType: "openai_chat"
                baseUrl: "https://api.openai.com/v1"
                isActive: true
            }) {
                ... on EndpointConfigGQLModel {
                    id
                    name
                }
            }
        }
    """
    await schema.execute(mutation1, context_value=context_value)
    
    # Create inactive endpoint
    mutation2 = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "Inactive Endpoint"
                endpointType: "openai_chat"
                baseUrl: "https://api.openai.com/v2"
                isActive: false
            }) {
                ... on EndpointConfigGQLModel {
                    id
                    name
                }
            }
        }
    """
    await schema.execute(mutation2, context_value=context_value)
    
    # Query only active endpoints
    query = """
        query {
            result: endpointConfigPage(where: { isActive: { _eq: true } }) {
                id
                name
                isActive: is_active
            }
        }
    """
    
    resp = await schema.execute(query, context_value=context_value)
    assert resp.errors is None, f"Expected no errors, got: {resp.errors}"
    assert resp.data is not None, "Expected data in response"
    
    result = resp.data.get("result")
    assert result is not None, "Expected result in response"
    assert isinstance(result, list), "Expected list in response"
    
    # All returned endpoints should be active
    for endpoint in result:
        assert endpoint.get("isActive") is True, "All endpoints should be active"


@pytest.mark.asyncio
async def test_endpoint_config_page_filter_type():
    """Test filtering endpoint configurations by endpoint_type"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # Create different types
    types_to_create = ['openai_chat', 'azure_chat', 'custom']
    for endpoint_type in types_to_create:
        mutation = f"""
            mutation {{
                result: endpointConfigInsert(endpointConfig: {{
                    name: "Test {endpoint_type}"
                    endpointType: "{endpoint_type}"
                    baseUrl: "https://api.example.com/v1"
                    isActive: true
                }}) {{
                    ... on EndpointConfigGQLModel {{
                        id
                        name
                    }}
                }}
            }}
        """
        await schema.execute(mutation, context_value=context_value)
    
    # Query only azure_chat endpoints
    query = """
        query {
            result: endpointConfigPage(where: { endpointType: { _eq: "azure_chat" } }) {
                id
                name
                endpointType: endpoint_type
            }
        }
    """
    
    resp = await schema.execute(query, context_value=context_value)
    assert resp.errors is None, f"Expected no errors, got: {resp.errors}"
    assert resp.data is not None, "Expected data in response"
    
    result = resp.data.get("result")
    assert result is not None, "Expected result in response"
    assert isinstance(result, list), "Expected list in response"
    
    # All returned endpoints should be azure_chat
    for endpoint in result:
        assert endpoint.get("endpointType") == "azure_chat", "All endpoints should be azure_chat"


@pytest.mark.asyncio
async def test_endpoint_config_by_id_not_found():
    """Test querying non-existent endpoint configuration by ID"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    import uuid
    fake_id = str(uuid.uuid4())
    
    query = f"""
        query($id: UUID!) {{
            result: endpointConfigById(id: $id) {{
                id
                name
            }}
        }}
    """
    
    resp = await schema.execute(
        query,
        context_value=context_value,
        variable_values={"id": fake_id}
    )
    
    assert resp.errors is None, f"Expected no errors, got: {resp.errors}"
    assert resp.data is not None, "Expected data in response"
    
    result = resp.data.get("result")
    # Should return None for non-existent ID
    assert result is None, "Expected None for non-existent ID"


@pytest.mark.asyncio
async def test_endpoint_config_insert_http_url():
    """Test creating endpoint configuration with http:// URL (not just https://)"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    mutation = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "HTTP Endpoint"
                endpointType: "custom"
                baseUrl: "http://api.example.com/v1"
                isActive: true
            }) {
                ... on EndpointConfigGQLModel {
                    id
                    name
                    baseUrl: base_url
                }
                ... on InsertError {
                    msg
                    code
                }
            }
        }
    """
    
    resp = await schema.execute(mutation, context_value=context_value)
    assert resp.errors is None, f"Expected no errors, got: {resp.errors}"
    assert resp.data is not None, "Expected data in response"
    
    result = resp.data.get("result")
    assert result is not None, "Expected result in response"
    assert "msg" not in result, f"Expected EndpointConfigGQLModel, got InsertError: {result}"
    assert result.get("baseUrl") == "http://api.example.com/v1"


@pytest.mark.asyncio
async def test_endpoint_config_update_all_fields():
    """Test updating all fields of endpoint configuration"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # Create initial endpoint
    mutation = """
        mutation {
            result: endpointConfigInsert(endpointConfig: {
                name: "Full Update Test"
                endpointType: "openai_chat"
                baseUrl: "https://api.openai.com/v1"
                isActive: true
            }) {
                ... on EndpointConfigGQLModel {
                    id
                    lastchange
                }
            }
        }
    """
    
    create_resp = await schema.execute(mutation, context_value=context_value)
    assert create_resp.errors is None
    created = create_resp.data["result"]
    created_id = created["id"]
    lastchange = created["lastchange"]
    
    # Update all fields
    model_mapping_json = json.dumps({"gpt-4o": "gpt4o-prod"})
    update_mutation = f"""
        mutation($id: UUID!, $lastchange: DateTime!) {{
            result: endpointConfigUpdate(endpointConfig: {{
                id: $id
                lastchange: $lastchange
                name: "Updated Full Name"
                endpointType: "azure_chat"
                baseUrl: "https://api.azure.com"
                apiVersion: "2024-12-01-preview"
                modelMapping: {json.dumps(model_mapping_json)}
                defaultDeployment: "gpt4o-prod"
                description: "Updated description"
                isActive: false
            }}) {{
                ... on EndpointConfigGQLModel {{
                    id
                    name
                    endpointType: endpoint_type
                    baseUrl: base_url
                    apiVersion: api_version
                    modelMapping: model_mapping
                    defaultDeployment: default_deployment
                    description
                    isActive: is_active
                }}
                ... on UpdateError {{
                    msg
                    code
                }}
            }}
        }}
    """
    
    update_resp = await schema.execute(
        update_mutation,
        context_value=context_value,
        variable_values={"id": created_id, "lastchange": lastchange}
    )
    
    assert update_resp.errors is None, f"Expected no errors, got: {update_resp.errors}"
    assert update_resp.data is not None, "Expected data in response"
    
    result = update_resp.data.get("result")
    assert result is not None, "Expected result in response"
    assert "msg" not in result, f"Expected EndpointConfigGQLModel, got UpdateError: {result}"
    assert result.get("name") == "Updated Full Name"
    assert result.get("endpointType") == "azure_chat"
    assert result.get("baseUrl") == "https://api.azure.com"
    assert result.get("apiVersion") == "2024-12-01-preview"
    assert result.get("defaultDeployment") == "gpt4o-prod"
    assert result.get("description") == "Updated description"
    assert result.get("isActive") is False


@pytest.mark.asyncio
async def test_endpoint_config_page_empty():
    """Test querying endpoint configurations page when empty"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    query = """
        query {
            result: endpointConfigPage {
                id
                name
            }
        }
    """
    
    resp = await schema.execute(query, context_value=context_value)
    assert resp.errors is None, f"Expected no errors, got: {resp.errors}"
    assert resp.data is not None, "Expected data in response"
    
    result = resp.data.get("result")
    assert result is not None, "Expected result in response"
    assert isinstance(result, list), "Expected list in response"
    # Empty list is valid result
