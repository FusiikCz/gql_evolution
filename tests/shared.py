import sqlalchemy
import sys
import os
import asyncio
import re
import uuid
from pathlib import Path

# Add parent directory to Python path so we can import src module
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest

from src.DBDefinitions import BaseModel, EventModel, EventInvitationModel, UserModel
from src.Dataloaders import createLoadersContext

# Import get_demodata with alias to avoid name conflict
from src.DBFeeder import get_demodata as _get_demodata


_TEST_ASYNC_ENGINES = []
_TEST_DB_PATHS = []
_TEST_ASYNC_SESSIONS = []


async def prepare_in_memory_sqllite():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    tmp_dir = Path(__file__).parent / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    db_path = tmp_dir / f"test_{uuid.uuid4().hex}.db"
    asyncEngine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    _TEST_ASYNC_ENGINES.append(asyncEngine)
    _TEST_DB_PATHS.append(db_path)
    async with asyncEngine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    async_session_maker = sessionmaker(
        asyncEngine, expire_on_commit=False, class_=AsyncSession
    )

    return async_session_maker


async def cleanup_test_engines():
    for session in list(_TEST_ASYNC_SESSIONS):
        try:
            await session.close()
        except Exception:
            pass
    _TEST_ASYNC_SESSIONS.clear()

    for engine in list(_TEST_ASYNC_ENGINES):
        try:
            await engine.dispose()
        except Exception:
            pass
    _TEST_ASYNC_ENGINES.clear()

    for path in list(_TEST_DB_PATHS):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except Exception:
            pass
    _TEST_DB_PATHS.clear()


async def prepare_demodata(async_session_maker):
    data = _get_demodata()

    from uoishelpers.feeders import ImportModels

    await ImportModels(
        async_session_maker,
        [
            UserModel,
            EventModel,
            EventInvitationModel
        ],
        data,
    )

async def fake_ug_client(query, variables):
    aliases = re.findall(r"\bitem\d+\b", query or "")
    if not aliases:
        aliases = ["item1"]

    is_roles_query = "roles(" in (query or "")
    data = {}
    role_name = "administr\u00e1tor"  # Default to "administrátor" for userInsert mutations
    for alias in aliases:
        if is_roles_query:
            data[alias] = {
                "result": [
                    {
                        "roletype": {
                            "id": "00000000-0000-0000-0000-000000000000",
                            "name": role_name,
                            "path": role_name
                        },
                        "userId": str(variables.get("user_id", "")) if variables else "",
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
            }
        else:
            data[alias] = {"result": True}
    return {"data": data}


def fake_ug_client_sync(query, variables, role_name: str = "administrátor"):
    """
    Synchronous variant of fake_ug_client for use where the caller does not await
    (e.g. uoishelpers RolePermissionSchemaExtension may call gqlClient without await).
    Returns the same structure as fake_ug_client with the given role_name.
    """
    aliases = re.findall(r"\bitem\d+\b", query or "")
    if not aliases:
        aliases = ["item1"]
    is_roles_query = "roles(" in (query or "")
    data = {}
    for alias in aliases:
        if is_roles_query:
            data[alias] = {
                "result": [
                    {
                        "roletype": {
                            "id": "00000000-0000-0000-0000-000000000000",
                            "name": role_name,
                            "path": role_name
                        },
                        "userId": str(variables.get("user_id", "")) if variables else "",
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
            }
        else:
            data[alias] = {"result": True}
    return {"data": data}


# Export get_demodata for use in tests
def get_demodata():
    """Get demo data for testing"""
    return _get_demodata()

class TestRequest:
    def __init__(self, user_id, include_user=True, user=None):
        auth = f"Bearer {user_id}"
        self._headers = {"Authorization": auth}
        # Minimal ASGI-like scope for uoishelpers resolvers
        self.scope = {
            "headers": [(b"authorization", auth.encode("utf-8"))],
        }
        if include_user:
            if user:
                # CRITICAL: Use the user object directly - it should already have roles set
                # This is required by SimpleInsertPermission which checks "roles" in user
                self.scope["user"] = user
            else:
                self.scope["user"] = {"id": user_id}

    @property
    def headers(self):
        return self._headers


def createContext(asyncSessionMaker, withuser=True, roles=None):
    session = asyncSessionMaker() if callable(asyncSessionMaker) else asyncSessionMaker
    if session is not None and hasattr(session, "close"):
        _TEST_ASYNC_SESSIONS.append(session)
    loadersContext = createLoadersContext(session) if session is not None else {"loaders": None}
    loadersContext["asyncSessionMaker"] = asyncSessionMaker
    user = {
        "id": "2d9dc5ca-a4a2-11ed-b9df-0242ac120003",
        "name": "John",
        "surname": "Newbie",
        "email": "john.newbie@world.com"
    }
    # Add roles to user if provided, otherwise use default admin role
    if roles is None:
        roles = [
            {
                "roletype": {
                    "id": "00000000-0000-0000-0000-000000000000",
                    "name": "administrátor",  # Use "administrátor" instead of "plánovací administrátor" for userInsert
                    "path": "administrátor"
                },
                "userId": user["id"],
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
    # CRITICAL: Add roles to user object BEFORE setting it in context
    # This is required by SimpleInsertPermission and UserRoleProviderExtension
    user["roles"] = roles
    if withuser:
        loadersContext["user"] = user
        # Also set user in request.scope for uoishelpers resolvers
        loadersContext["request"] = TestRequest(user["id"], include_user=True, user=user)
    else:
        loadersContext["request"] = TestRequest(user["id"], include_user=False)
    loadersContext["ug_client"] = fake_ug_client
    return loadersContext

def createInfo(asyncSessionMaker, withuser=True):
    class Info():
        @property
        def context(self):
            context = createContext(asyncSessionMaker, withuser=withuser)
            # Use the same user object from context to ensure roles are preserved
            user = context.get("user")
            if user:
                context["request"] = TestRequest(user["id"], include_user=True, user=user)
            else:
                context["request"] = TestRequest("2d9dc5ca-a4a2-11ed-b9df-0242ac120003", include_user=False)
            return context
        
    return Info()


# Helper functions for better test output
def assert_no_errors(resp, test_name=""):
    """Assert no GraphQL errors occurred"""
    assert resp.errors is None, f"ERROR [{test_name}] GraphQL errors: {resp.errors}"
    return True


def assert_has_data(resp, test_name=""):
    """Assert response has data"""
    assert resp.data is not None, f"ERROR [{test_name}] No data in response"
    return resp.data


def assert_result_exists(data, key="result", test_name=""):
    """Assert result exists in data"""
    result = data.get(key)
    assert result is not None, f"ERROR [{test_name}] No '{key}' in response data"
    return result


def assert_is_success(result, test_name=""):
    """Assert result is success (not error)"""
    assert "msg" not in result, f"ERROR [{test_name}] Expected success, got error: {result}"
    return True


def assert_is_error(result, expected_code=None, test_name=""):
    """Assert result is error"""
    assert "msg" in result, f"ERROR [{test_name}] Expected error, got success: {result}"
    if expected_code:
        assert result.get("code") == expected_code, f"ERROR [{test_name}] Expected error code '{expected_code}', got '{result.get('code')}'"
    return True


def print_success(message):
    """Print success message"""
    print(f"SUCCESS: {message}")


def print_info(message):
    """Print info message"""
    print(f"INFO: {message}")