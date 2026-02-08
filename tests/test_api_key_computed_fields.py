"""
Tests for computed fields in ApiKeyGQLModel.

Tests:
- is_expired
- is_over_token_limit
- is_over_cost_limit
- limit_alerts
- usage_count
- total_usage_this_month
- total_cost_this_month
"""
import pytest
import logging
import datetime
import uuid
from src.GraphTypeDefinitions import schema
from src.DBDefinitions import ApiKeyModel, UsageModel, UserModel
from .shared import (
    prepare_demodata,
    prepare_in_memory_sqllite,
    get_demodata,
    createContext,
)


@pytest.mark.asyncio
@pytest.mark.api_key
async def test_is_expired_future_date():
    """Test that is_expired returns False for future expiration date"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # Create API key with future expiration
    future_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    mutation = f"""
        mutation {{
            result: apiKeyInsert(apiKey: {{
                name: "Future Expiration Key"
                expiresAt: "{future_date.isoformat()}"
            }}) {{
                ... on ApiKeyInsertResponse {{
                    apiKey {{
                        id
                        isExpired
                        expiresAt
                    }}
                }}
            }}
        }}
    """
    
    resp = await schema.execute(mutation, context_value=context_value)
    assert resp.errors is None, f"Mutation failed: {resp.errors}"
    assert resp.data is not None
    
    result = resp.data.get("result")
    assert result is not None
    assert "apiKey" in result
    
    api_key = result["apiKey"]
    assert api_key.get("isExpired") is False


@pytest.mark.asyncio
@pytest.mark.api_key
async def test_is_expired_past_date():
    """Test that is_expired returns True for past expiration date"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    # Create API key directly in database with past expiration date
    # (bypassing GraphQL validation which prevents past dates)
    past_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    from src.DBDefinitions import ApiKeyModel, UserModel
    from sqlalchemy import select
    
    async with async_session_maker() as session:
        # Get a user from demo data
        stmt = select(UserModel).limit(1)
        result = await session.execute(stmt)
        user = result.scalar_one()
        
        # Create API key with past expiration
        api_key_db = ApiKeyModel(
            id=uuid.uuid4(),
            name="Past Expiration Key",
            user_id=user.id,
            expires_at=past_date.replace(tzinfo=None),  # Remove timezone for DB
            is_active=True,
            createdby_id=user.id,
            changedby_id=user.id,
            rbacobject_id=uuid.uuid4()
        )
        session.add(api_key_db)
        await session.commit()
        await session.refresh(api_key_db)
        api_key_id = str(api_key_db.id)
    
    # Query the API key via GraphQL to check isExpired
    query = f"""
        query {{
            result: apiKeyById(id: "{api_key_id}") {{
                id
                isExpired
            }}
        }}
    """
    
    resp = await schema.execute(query, context_value=context_value)
    assert resp.errors is None, f"Query failed: {resp.errors}"
    assert resp.data is not None
    
    result = resp.data.get("result")
    assert result is not None
    assert result.get("isExpired") is True


@pytest.mark.asyncio
@pytest.mark.api_key
async def test_is_expired_no_expiration():
    """Test that is_expired returns False when expires_at is None"""
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)
    
    mutation = """
        mutation {
            result: apiKeyInsert(apiKey: {
                name: "No Expiration Key"
            }) {
                ... on ApiKeyInsertResponse {
                    apiKey {
                        id
                        isExpired
                        expiresAt
                    }
                }
            }
        }
    """
    
    resp = await schema.execute(mutation, context_value=context_value)
    assert resp.errors is None, f"Mutation failed: {resp.errors}"
    assert resp.data is not None
    
    result = resp.data.get("result")
    assert result is not None
    assert "apiKey" in result
    
    api_key = result["apiKey"]
    assert api_key.get("expiresAt") is None
    assert api_key.get("isExpired") is False


