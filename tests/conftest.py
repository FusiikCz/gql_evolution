"""
Pytest configuration and fixtures for better test output and functionality.
"""
import pytest
import sys
import os
from pathlib import Path

# Ensure tests run in DEMO mode (disable WhoAmIExtension)
os.environ.setdefault("DEMO", "True")

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Keep schema extensions isolated per test
from src.GraphTypeDefinitions import schema as _schema
_BASE_SCHEMA_EXTENSIONS = list(_schema.extensions)


@pytest.fixture(autouse=True)
def reset_schema_extensions():
    _schema.extensions[:] = list(_BASE_SCHEMA_EXTENSIONS)
    yield
    _schema.extensions[:] = list(_BASE_SCHEMA_EXTENSIONS)


@pytest.fixture(autouse=True)
def log_test_start(request):
    """Automatically log test start and end for better visibility"""
    test_name = request.node.name
    # Only print detailed info in verbose mode
    verbose = request.config.getoption("-v", default=False) or request.config.getoption("--verbose", default=False)
    if verbose:
        print(f"\n{'='*80}")
        print(f"TEST: {test_name}")
        if hasattr(request.node, 'obj') and request.node.obj.__doc__:
            doc = request.node.obj.__doc__.strip()
            print(f"Description: {doc}")
        print(f"{'='*80}")
    yield
    if verbose:
        print(f"COMPLETED: {test_name}\n")


def pytest_collection_modifyitems(config, items):
    """Add markers based on test names for better organization"""
    for item in items:
        # Add category markers based on test name patterns
        test_name = item.name.lower()
        
        if "insert" in test_name or "create" in test_name:
            item.add_marker(pytest.mark.crud)
            item.add_marker(pytest.mark.create)
        elif "update" in test_name:
            item.add_marker(pytest.mark.crud)
            item.add_marker(pytest.mark.update)
        elif "delete" in test_name or "remove" in test_name:
            item.add_marker(pytest.mark.crud)
            item.add_marker(pytest.mark.delete)
        elif "page" in test_name or "list" in test_name or "get" in test_name or "by_id" in test_name:
            item.add_marker(pytest.mark.crud)
            item.add_marker(pytest.mark.read)
        elif "invalid" in test_name or "error" in test_name or "fail" in test_name:
            item.add_marker(pytest.mark.validation)
            item.add_marker(pytest.mark.error_handling)
        elif "filter" in test_name:
            item.add_marker(pytest.mark.filtering)
        elif "empty" in test_name or "not_found" in test_name:
            item.add_marker(pytest.mark.edge_cases)
        
        # Add entity markers
        if "endpoint" in test_name:
            item.add_marker(pytest.mark.endpoint_config)
        elif "api_key" in test_name or "apikey" in test_name:
            item.add_marker(pytest.mark.api_key)
        elif "event" in test_name:
            item.add_marker(pytest.mark.event)
        elif "user" in test_name:
            item.add_marker(pytest.mark.user)
        elif "document" in test_name:
            item.add_marker(pytest.mark.document)


def pytest_runtest_setup(item):
    """Print test description before running"""
    if item.obj.__doc__:
        doc = item.obj.__doc__.strip()
        print(f"\nDescription: {doc}")


def pytest_runtest_makereport(item, call):
    """Custom report formatting (only in verbose mode)"""
    verbose = item.config.getoption("-v", default=False) or item.config.getoption("--verbose", default=False)
    if verbose and call.when == "call":
        if call.excinfo is not None:
            print(f"\nFAILED: {item.name}")
            if call.excinfo.value:
                print(f"   Error: {call.excinfo.value}")
        else:
            print(f"PASSED: {item.name}")


def pytest_sessionfinish(session, exitstatus):
    """Print summary at the end"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = len([r for r in session.items if hasattr(r, 'call') and r.call.excinfo is None])
    failed = len([r for r in session.items if hasattr(r, 'call') and r.call.excinfo is not None])
    total = len(session.items)
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {total - passed - failed}")
    print("="*80)
