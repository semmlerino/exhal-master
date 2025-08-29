#!/usr/bin/env python3
from __future__ import annotations

"""Analyze test failures and categorize them by root cause."""

import subprocess
import sys
import re
from pathlib import Path
from collections import defaultdict
import json

def run_single_test(test_path):
    """Run a single test file and capture the result."""
    cmd = [
        "../venv/bin/pytest",
        str(test_path),
        "--tb=short",
        "--timeout=3",
        "-q",
        "--no-header"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent
        )
        return {
            "status": "passed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "errors": extract_errors(result.stdout + result.stderr)
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "returncode": -1,
            "stdout": "",
            "stderr": "Test timed out",
            "errors": ["Test execution timeout"]
        }
    except Exception as e:
        return {
            "status": "error",
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "errors": [str(e)]
        }

def extract_errors(text):
    """Extract error messages from test output."""
    errors = []
    
    # Common error patterns
    patterns = [
        r"AttributeError: (.+)",
        r"ImportError: (.+)",
        r"TypeError: (.+)",
        r"ValueError: (.+)",
        r"Failed: (.+)",
        r"AssertionError: (.+)",
        r"ModuleNotFoundError: (.+)",
        r"FAILED (.+) - (.+)",
        r"ERROR (.+) - (.+)",
        r"Timeout \(>(.+)\)",
        r"INTERNALERROR>(.+)"
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                errors.append(" - ".join(match))
            else:
                errors.append(match)
    
    return errors

def categorize_failures():
    """Run tests and categorize failures."""
    test_dir = Path("tests")
    
    # Find all test files
    test_files = []
    for pattern in ["test_*.py", "*_test.py"]:
        test_files.extend(test_dir.glob(f"**/{pattern}"))
    
    # Filter out archive directory
    test_files = [f for f in test_files if "archive" not in str(f)]
    
    # Sample a subset for quick analysis
    sample_size = 20
    test_files = test_files[:sample_size]
    
    results = defaultdict(list)
    
    print(f"Analyzing {len(test_files)} test files...")
    
    for i, test_file in enumerate(test_files, 1):
        rel_path = test_file.relative_to(test_dir.parent)
        print(f"[{i}/{len(test_files)}] Testing {rel_path}...", end=" ")
        
        result = run_single_test(test_file)
        
        # Categorize by status
        results[result["status"]].append({
            "file": str(rel_path),
            "errors": result["errors"][:3]  # First 3 errors
        })
        
        print(result["status"])
    
    return results

def main():
    """Main analysis function."""
    print("SpritePal Test Failure Analysis")
    print("=" * 50)
    
    results = categorize_failures()
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    for status, tests in results.items():
        print(f"\n{status.upper()}: {len(tests)} tests")
        if tests and status != "passed":
            print("  Common issues:")
            # Group by error type
            error_groups = defaultdict(list)
            for test in tests:
                for error in test["errors"]:
                    # Extract error type
                    if ":" in error:
                        error_type = error.split(":")[0].split()[-1]
                    else:
                        error_type = "Unknown"
                    error_groups[error_type].append(test["file"])
            
            for error_type, files in error_groups.items():
                print(f"    {error_type}: {len(files)} files")
                for file in files[:3]:  # Show first 3 files
                    print(f"      - {file}")
    
    # Save detailed results
    output_file = Path("test_failure_analysis.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to {output_file}")

if __name__ == "__main__":
    main()