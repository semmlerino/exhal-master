#!/usr/bin/env python3
from __future__ import annotations

"""
Parallel test runner for SpritePal test suite.

This script provides optimized test execution by running safe tests in parallel
and thread-unsafe tests serially, with proper reporting and error handling.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

def run_command(cmd: list[str], description: str, timeout: int = 300) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path.cwd()
        )
        
        duration = time.time() - start_time
        success = result.returncode == 0
        
        print(f"\n{description} {'PASSED' if success else 'FAILED'} in {duration:.1f}s")
        
        if result.stdout:
            print("\nSTDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
            
        return success, result.stdout + result.stderr
        
    except subprocess.TimeoutExpired as e:
        duration = time.time() - start_time
        print(f"\n{description} TIMEOUT after {duration:.1f}s")
        return False, f"Command timed out after {timeout}s"
    except Exception as e:
        duration = time.time() - start_time
        print(f"\n{description} ERROR after {duration:.1f}s: {e}")
        return False, str(e)

def get_test_counts() -> tuple[int, int]:
    """Get counts of parallel vs serial tests."""
    try:
        # Count all tests
        result = subprocess.run([
            "pytest", "--collect-only", "-q", "tests/"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print("Warning: Could not count total tests")
            total_tests = "unknown"
        else:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'tests collected' in line:
                    total_tests = int(line.split()[0])
                    break
            else:
                total_tests = "unknown"
        
        # Count serial tests
        result = subprocess.run([
            "pytest", "--collect-only", "-q", "-m", "serial", "tests/"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print("Warning: Could not count serial tests")
            serial_tests = "unknown"
        else:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'tests collected' in line:
                    serial_tests = int(line.split()[0])
                    break
            else:
                serial_tests = 0
        
        if isinstance(total_tests, int) and isinstance(serial_tests, int):
            parallel_tests = total_tests - serial_tests
        else:
            parallel_tests = "unknown"
            
        return parallel_tests, serial_tests
        
    except Exception as e:
        print(f"Warning: Error counting tests: {e}")
        return "unknown", "unknown"

def main():
    parser = argparse.ArgumentParser(description="Run SpritePal tests with optimal parallel/serial execution")
    parser.add_argument("--parallel-only", action="store_true", help="Run only parallel-safe tests")
    parser.add_argument("--serial-only", action="store_true", help="Run only serial tests")
    parser.add_argument("--workers", "-n", type=int, default=4, help="Number of parallel workers (default: 4)")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout per test phase in seconds (default: 600)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--maxfail", type=int, default=5, help="Stop after N failures (default: 5)")
    parser.add_argument("tests", nargs="*", help="Specific test files to run")
    
    args = parser.parse_args()
    
    # Get test counts
    parallel_count, serial_count = get_test_counts()
    
    print("SpritePal Parallel Test Runner")
    print(f"Parallel tests: {parallel_count}")
    print(f"Serial tests: {serial_count}")
    print(f"Workers: {args.workers}")
    print(f"Timeout: {args.timeout}s per phase")
    
    # Base command components
    base_pytest = ["pytest"]
    if args.verbose:
        base_pytest.append("-v")
    else:
        base_pytest.append("-q")
    
    base_pytest.extend([
        "--tb=short",
        f"--maxfail={args.maxfail}",
        "--disable-warnings"
    ])
    
    # Determine test paths
    test_paths = args.tests if args.tests else ["tests/"]
    
    results = []
    
    if not args.serial_only:
        # Run parallel tests
        parallel_cmd = base_pytest + [
            f"-n{args.workers}",
            "--dist=worksteal",
            "-m", "not serial"
        ] + test_paths
        
        parallel_success, parallel_output = run_command(
            parallel_cmd,
            f"Parallel tests ({parallel_count} tests, {args.workers} workers)",
            args.timeout
        )
        results.append(("Parallel", parallel_success, parallel_output))
        
        if not parallel_success and not args.parallel_only:
            print("\n⚠️  Parallel tests failed, but continuing with serial tests...")
    
    if not args.parallel_only:
        # Run serial tests
        serial_cmd = base_pytest + [
            "-m", "serial"
        ] + test_paths
        
        serial_success, serial_output = run_command(
            serial_cmd,
            f"Serial tests ({serial_count} tests)",
            args.timeout
        )
        results.append(("Serial", serial_success, serial_output))
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    all_passed = True
    for phase, success, output in results:
        status = "PASSED" if success else "FAILED"
        print(f"{phase:12} {status}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\n✅ All test phases passed!")
        return 0
    else:
        print(f"\n❌ Some test phases failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())