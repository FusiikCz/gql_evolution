"""
Pytest configuration and fixtures for better test output and functionality.
"""
import pytest
import sys
import os
import asyncio
import warnings
from pathlib import Path

# Ensure tests run in DEMO mode and disable WhoAmIExtension explicitly
os.environ.setdefault("DEMO", "True")
os.environ.setdefault("DISABLE_WHOAMI_EXTENSION", "True")

# Silence strawberry deprecation warning from third-party extensions.
warnings.filterwarnings(
    "ignore",
    message="Event driven styled extensions for on_request_start or on_request_end are deprecated, use on_operation instead",
    category=DeprecationWarning,
)

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
    
    # Get stats from terminal reporter - stats are populated during test execution
    try:
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter and hasattr(reporter, 'stats') and reporter.stats:
            passed = len(reporter.stats.get('passed', []))
            failed = len(reporter.stats.get('failed', []))
            skipped = len(reporter.stats.get('skipped', []))
            total = passed + failed + skipped
        else:
            # Fallback: use exitstatus and session items count
            total = len(session.items)
            # If we can't get stats, just show total - pytest will show details anyway
            passed = failed = skipped = 0
    except Exception as e:
        # Ultimate fallback - just show total
        total = len(session.items)
        passed = failed = skipped = 0
    
    print(f"Total tests: {total}")
    if passed + failed + skipped > 0:
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")
    else:
        print("(Detailed stats shown above by pytest)")
    print("="*80)

    # Clean up async engines created in tests to avoid GC warnings.
    try:
        from tests import shared as test_shared
        try:
            asyncio.run(test_shared.cleanup_test_engines())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(test_shared.cleanup_test_engines())
            finally:
                loop.close()
    except Exception:
        pass
