#!/usr/bin/env python
"""
Helper script to run individual tests with better output.

Usage:
    python tests/run_test.py <test_name> [options]
    python tests/run_test.py --list
    python tests/run_test.py -l

Examples:
    python tests/run_test.py test_endpoint_config_insert
    python tests/run_test.py test_endpoint_config_insert -v
    python tests/run_test.py test_endpoint_config_insert --cov
    python tests/run_test.py test_endpoint_config_insert -x  # stop on first fail
    python tests/run_test.py --list  # list all available tests
"""
import sys
import subprocess
import json
import html
import datetime
from pathlib import Path


def write_report(command, result):
    report_path = Path("tests/report.json")
    html_path = Path("tests/report.html")
    report = {
        "timestamp": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout or "",
        "stderr": result.stderr or ""
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    escaped = html.escape(report["stdout"] + "\n" + report["stderr"])
    html_payload = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Test Report</title></head>
<body>
<h2>Test Report</h2>
<pre>{escaped}</pre>
</body>
</html>
"""
    html_path.write_text(html_payload, encoding="utf-8")

def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/run_test.py <test_name> [options]")
        print("       python tests/run_test.py --list")
        print("\nExamples:")
        print("  python tests/run_test.py test_endpoint_config_insert")
        print("  python tests/run_test.py test_endpoint_config_insert -v")
        print("  python tests/run_test.py test_endpoint_config_insert --cov")
        print("  python tests/run_test.py test_endpoint_config_insert -x  # stop on first fail")
        print("\nTo list all available tests:")
        print("  python tests/run_test.py --list")
        print("  python tests/run_test.py -l")
        print("\nAlternative:")
        print("  pytest tests/ --collect-only -q")
        sys.exit(1)
    
    # Check for help flag first
    if sys.argv[1] in ["--help", "-h"]:
        print(__doc__)
        sys.exit(0)
    
    # Check if user wants to list tests
    if sys.argv[1] == "--list" or sys.argv[1] == "-l":
        print("Available tests:\n")
        # Override addopts to remove coverage options
        cmd = ["pytest", "tests/", "--collect-only", "-q",
               "--override-ini", "addopts=-v --strict-markers --tb=line --showlocals --color=yes -ra"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
            write_report(cmd, result)
        else:
            # If override fails, try to install pytest-cov or use workaround
            print("Note: Coverage options in pytest.ini may cause issues.")
            print("You can install pytest-cov with: pip install pytest-cov")
            print("\nTrying to list tests anyway (may show errors):\n")
            cmd = ["pytest", "tests/", "--collect-only", "-q"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            write_report(cmd, result)
        sys.exit(0)
    
    test_name = sys.argv[1]
    options = sys.argv[2:] if len(sys.argv) > 2 else []
    
    # Find test file
    test_file = None
    test_files = [
        "tests/test_endpoint_config.py",
        "tests/test_gt_definitions.py",
        "tests/test_dbdefinitions.py",
        "tests/test_dataloaders.py",
        "tests/test_client.py",
    ]
    
    for tf in test_files:
        if Path(tf).exists():
            # Check if test exists in file
            with open(tf, 'r', encoding='utf-8') as f:
                if f"def {test_name}" in f.read() or f"async def {test_name}" in f.read():
                    test_file = tf
                    break
    
    if not test_file:
        # Try pattern matching with pytest -k
        cmd = ["pytest", "tests/", "-k", test_name, "--collect-only", "-q",
               "--override-ini", "addopts=-v --strict-markers --tb=line --showlocals --color=yes -ra"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        # If override fails, try without it
        if result.returncode != 0:
            cmd = ["pytest", "tests/", "-k", test_name, "--collect-only", "-q"]
            result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            # Test found, run it
            print(f"Found test matching pattern '{test_name}'")
            cmd = ["pytest", "tests/", "-k", test_name, "-v",
                   "--override-ini", "addopts=-v --strict-markers --tb=line --showlocals --color=yes -ra"] + options
            print(f"Running: {' '.join(cmd)}\n")
            run_result = subprocess.run(cmd, capture_output=True, text=True)
            
            # If override fails due to coverage, try without it
            if run_result.returncode != 0 and run_result.stderr and "unrecognized arguments" in run_result.stderr and "--cov" in run_result.stderr:
                print("Note: Coverage options in pytest.ini may cause issues.")
                print("Trying without override...\n")
                cmd = ["pytest", "tests/", "-k", test_name, "-v"] + options
                run_result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Check for missing dependencies
            error_text = ""
            if run_result.stderr:
                error_text = run_result.stderr
            if run_result.stdout:
                error_text += run_result.stdout
            
            # Check for async test issues
            if run_result.returncode != 0 and ("async def functions are not natively supported" in error_text or 
                                                "pytest-asyncio" in error_text.lower() or
                                                "You need to install a suitable plugin" in error_text):
                print("\n" + "="*80)
                print("ERROR: pytest-asyncio is required for async tests")
                print("="*80)
                print("\nInstall it with:")
                print("  pip install pytest-asyncio")
                print("\nOr install all dev dependencies:")
                print("  pip install -r requirements-dev.txt")
                print("="*80 + "\n")
                if run_result.stdout:
                    print(run_result.stdout)
                if run_result.stderr:
                    print(run_result.stderr, file=sys.stderr)
                sys.exit(run_result.returncode)
            
            # Check for missing aiosqlite
            if run_result.returncode != 0 and ("No module named 'aiosqlite'" in error_text or
                                                "ModuleNotFoundError: No module named 'aiosqlite'" in error_text):
                print("\n" + "="*80)
                print("ERROR: aiosqlite is required for async SQLite tests")
                print("="*80)
                print("\nInstall it with:")
                print("  pip install aiosqlite")
                print("\nOr install all dev dependencies:")
                print("  pip install -r requirements-dev.txt")
                print("="*80 + "\n")
                if run_result.stdout:
                    print(run_result.stdout)
                if run_result.stderr:
                    print(run_result.stderr, file=sys.stderr)
                sys.exit(run_result.returncode)
            
            write_report(cmd, run_result)

            # Always show output (success or failure)
            if run_result.stdout:
                print(run_result.stdout)
            if run_result.stderr:
                print(run_result.stderr, file=sys.stderr)
            sys.exit(run_result.returncode)
            return
        else:
            print(f"ERROR: Test '{test_name}' not found")
            print("\nAvailable tests:")
            cmd = ["pytest", "tests/", "--collect-only", "-q",
                   "--override-ini", "addopts=-v --strict-markers --tb=line --showlocals --color=yes -ra"]
            list_result = subprocess.run(cmd, capture_output=True, text=True)
            if list_result.returncode == 0:
                print(list_result.stdout)
            else:
                cmd = ["pytest", "tests/", "--collect-only", "-q"]
                subprocess.run(cmd)
            sys.exit(1)
    
    # Run specific test
    # Try to override coverage options if they cause issues
    cmd = ["pytest", f"{test_file}::{test_name}", "-v",
           "--override-ini", "addopts=-v --strict-markers --tb=line --showlocals --color=yes -ra"] + options
    print(f"Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # If override fails due to coverage options, try without it
    if result.returncode != 0 and result.stderr and "unrecognized arguments" in result.stderr and "--cov" in result.stderr:
        print("Note: Coverage options in pytest.ini may cause issues.")
        print("Trying without override (coverage plugin may not be installed)...\n")
        cmd = ["pytest", f"{test_file}::{test_name}", "-v"] + options
        result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Check for missing dependencies
    error_text = ""
    if result.stderr:
        error_text = result.stderr
    if result.stdout:
        error_text += result.stdout
    
    # Check for async test issues
    if result.returncode != 0 and ("async def functions are not natively supported" in error_text or 
                                    "pytest-asyncio" in error_text.lower() or
                                    "You need to install a suitable plugin" in error_text):
        print("\n" + "="*80)
        print("ERROR: pytest-asyncio is required for async tests")
        print("="*80)
        print("\nInstall it with:")
        print("  pip install pytest-asyncio")
        print("\nOr install all dev dependencies:")
        print("  pip install -r requirements-dev.txt")
        print("="*80 + "\n")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    
    # Check for missing aiosqlite
    if result.returncode != 0 and ("No module named 'aiosqlite'" in error_text or
                                    "ModuleNotFoundError: No module named 'aiosqlite'" in error_text):
        print("\n" + "="*80)
        print("ERROR: aiosqlite is required for async SQLite tests")
        print("="*80)
        print("\nInstall it with:")
        print("  pip install aiosqlite")
        print("\nOr install all dev dependencies:")
        print("  pip install -r requirements-dev.txt")
        print("="*80 + "\n")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    
    write_report(cmd, result)

    # Always show output (success or failure)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
