#!/usr/bin/env python
"""
Helper script to run individual tests with better output.

Usage:
    python tests/run_test.py <test_name> [options]
    python tests/run_test.py --list
    python tests/run_test.py -l
    python tests/run_test.py --all
"""
import sys
import subprocess
import json
import html
import datetime
import re
from pathlib import Path


def _extract_total_tests(output: str | None) -> int | None:
    if not output:
        return None
    match = re.search(r"collected\s+(\d+)\s+items", output)
    if match:
        return int(match.group(1))
    return None


def write_report(command, result):
    report_path = Path("tests/report.json")
    html_path = Path("tests/report.html")
    combined_output = (result.stdout or "") + "\n" + (result.stderr or "")
    total_tests = _extract_total_tests(combined_output)
    report = {
        "timestamp": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout or "",
        "stderr": result.stderr or "",
        "total_tests": total_tests,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    escaped = html.escape(report["stdout"] + "\n" + report["stderr"])
    total_line = f"<p>Total tests: {total_tests}</p>" if total_tests is not None else ""
    html_payload = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Test Report</title></head>
<body>
<h2>Test Report</h2>
{total_line}
<pre>{escaped}</pre>
</body>
</html>
"""
    html_path.write_text(html_payload, encoding="utf-8")


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/run_test.py <test_name> [options]")
        print("       python tests/run_test.py --list")
        print("       python tests/run_test.py --all")
        sys.exit(1)

    if sys.argv[1] in ["--help", "-h"]:
        print(__doc__)
        sys.exit(0)

    if sys.argv[1] in ["--list", "-l"]:
        cmd = [
            "pytest",
            "tests/",
            "--collect-only",
            "-q",
            "--override-ini",
            "addopts=-v --strict-markers --tb=line --showlocals --color=yes -ra",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            cmd = ["pytest", "tests/", "--collect-only", "-q"]
            result = subprocess.run(cmd, capture_output=True, text=True)
        write_report(cmd, result)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

    if sys.argv[1] == "--all":
        cmd = [
            "pytest",
            "tests/",
            "-v",
            "--override-ini",
            "addopts=-v --strict-markers --tb=line --showlocals --color=yes -ra",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if (
            result.returncode != 0
            and result.stderr
            and "unrecognized arguments" in result.stderr
            and "--cov" in result.stderr
        ):
            cmd = ["pytest", "tests/", "-v"]
            result = subprocess.run(cmd, capture_output=True, text=True)
        write_report(cmd, result)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

    test_name = sys.argv[1]
    options = sys.argv[2:] if len(sys.argv) > 2 else []

    test_files = [
        "tests/test_endpoint_config.py",
        "tests/test_gt_definitions.py",
        "tests/test_dbdefinitions.py",
        "tests/test_dataloaders.py",
        "tests/test_client.py",
    ]

    test_file = None
    for tf in test_files:
        if Path(tf).exists():
            with open(tf, "r", encoding="utf-8") as f:
                if f"def {test_name}" in f.read() or f"async def {test_name}" in f.read():
                    test_file = tf
                    break

    if not test_file:
        cmd = [
            "pytest",
            "tests/",
            "-k",
            test_name,
            "--collect-only",
            "-q",
            "--override-ini",
            "addopts=-v --strict-markers --tb=line --showlocals --color=yes -ra",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            cmd = ["pytest", "tests/", "-k", test_name, "--collect-only", "-q"]
            result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            cmd = [
                "pytest",
                "tests/",
                "-k",
                test_name,
                "-v",
                "--override-ini",
                "addopts=-v --strict-markers --tb=line --showlocals --color=yes -ra",
            ] + options
            run_result = subprocess.run(cmd, capture_output=True, text=True)
            if (
                run_result.returncode != 0
                and run_result.stderr
                and "unrecognized arguments" in run_result.stderr
                and "--cov" in run_result.stderr
            ):
                cmd = ["pytest", "tests/", "-k", test_name, "-v"] + options
                run_result = subprocess.run(cmd, capture_output=True, text=True)
            write_report(cmd, run_result)
            if run_result.stdout:
                print(run_result.stdout)
            if run_result.stderr:
                print(run_result.stderr, file=sys.stderr)
            sys.exit(run_result.returncode)
        print(f"ERROR: Test '{test_name}' not found")
        sys.exit(1)

    cmd = [
        "pytest",
        f"{test_file}::{test_name}",
        "-v",
        "--override-ini",
        "addopts=-v --strict-markers --tb=line --showlocals --color=yes -ra",
    ] + options
    result = subprocess.run(cmd, capture_output=True, text=True)
    if (
        result.returncode != 0
        and result.stderr
        and "unrecognized arguments" in result.stderr
        and "--cov" in result.stderr
    ):
        cmd = ["pytest", f"{test_file}::{test_name}", "-v"] + options
        result = subprocess.run(cmd, capture_output=True, text=True)
    write_report(cmd, result)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
