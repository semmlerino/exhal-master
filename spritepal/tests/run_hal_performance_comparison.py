#!/usr/bin/env python3
"""
Script to compare HAL test performance with and without mocking.

This demonstrates the performance improvements achieved by the HAL mocking infrastructure.
"""

import subprocess
import time
import sys
from pathlib import Path

def run_tests_with_timing(use_real_hal=False, test_pattern="test_hal"):
    """Run HAL-related tests and measure execution time."""
    
    cmd = [
        sys.executable, "-m", "pytest",
        "-xvs",
        f"-k", test_pattern,
        "--tb=short",
        "--no-header"
    ]
    
    if use_real_hal:
        cmd.append("--use-real-hal")
    
    print(f"\n{'='*60}")
    print(f"Running tests with {'REAL' if use_real_hal else 'MOCK'} HAL")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    
    start_time = time.perf_counter()
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    elapsed_time = time.perf_counter() - start_time
    
    # Parse test results
    passed = failed = 0
    for line in result.stdout.split('\n'):
        if 'passed' in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if part == 'passed':
                    try:
                        passed = int(parts[i-1])
                    except (ValueError, IndexError):
                        pass
        if 'failed' in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if part == 'failed':
                    try:
                        failed = int(parts[i-1])
                    except (ValueError, IndexError):
                        pass
    
    return {
        'time': elapsed_time,
        'passed': passed,
        'failed': failed,
        'output': result.stdout,
        'errors': result.stderr,
        'returncode': result.returncode
    }


def main():
    """Run performance comparison."""
    
    print("\n" + "="*80)
    print("HAL MOCKING PERFORMANCE COMPARISON")
    print("="*80)
    
    # Run with mock HAL (default)
    print("\n1. Running tests with MOCK HAL (fast)...")
    mock_results = run_tests_with_timing(use_real_hal=False)
    
    # Run with real HAL
    print("\n2. Running tests with REAL HAL (slow)...")
    real_results = run_tests_with_timing(use_real_hal=True)
    
    # Calculate improvements
    speedup = real_results['time'] / mock_results['time'] if mock_results['time'] > 0 else 0
    time_saved = real_results['time'] - mock_results['time']
    
    # Print summary
    print("\n" + "="*80)
    print("PERFORMANCE SUMMARY")
    print("="*80)
    
    print(f"\nMock HAL Results:")
    print(f"  Time: {mock_results['time']:.2f}s")
    print(f"  Tests Passed: {mock_results['passed']}")
    print(f"  Tests Failed: {mock_results['failed']}")
    
    print(f"\nReal HAL Results:")
    print(f"  Time: {real_results['time']:.2f}s")
    print(f"  Tests Passed: {real_results['passed']}")
    print(f"  Tests Failed: {real_results['failed']}")
    
    print(f"\nPerformance Improvement:")
    print(f"  Speedup: {speedup:.1f}x faster")
    print(f"  Time Saved: {time_saved:.2f}s")
    print(f"  Percentage Reduction: {(1 - mock_results['time']/real_results['time'])*100:.1f}%")
    
    if speedup >= 7:
        print(f"\n✅ SUCCESS: Achieved target 7x speedup!")
    else:
        print(f"\n⚠️  Speedup is {speedup:.1f}x, target was 7x")
    
    # Check for errors
    if mock_results['failed'] > 0 or real_results['failed'] > 0:
        print("\n⚠️  WARNING: Some tests failed")
        if mock_results['errors']:
            print(f"Mock errors: {mock_results['errors'][:500]}")
        if real_results['errors']:
            print(f"Real errors: {real_results['errors'][:500]}")
    
    return 0 if speedup >= 7 else 1


if __name__ == "__main__":
    sys.exit(main())