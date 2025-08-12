#!/usr/bin/env python3
"""
Diagnostic script to debug intermittent exhal executable detection issue.

This script tests the exact same detection logic used by HALCompressor._find_tool
under various conditions to identify why the detection sometimes fails.
"""

import os
import platform
import tempfile
import time
from pathlib import Path


def test_exhal_detection(tool_name="exhal", provided_path=None, test_name=""):
    """Test exhal detection using exact logic from HALCompressor._find_tool"""

    print(f"\n=== Test: {test_name} ===")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Tool name: {tool_name}")
    print(f"Provided path: {provided_path}")

    try:
        # Exact logic from _find_tool method
        if provided_path:
            print(f"Checking provided path: {provided_path}")
            if Path(provided_path).is_file():
                print(f"SUCCESS: Using provided {tool_name} at: {provided_path}")
                return str(provided_path)
            print(f"WARNING: Provided path does not exist: {provided_path}")

        # Platform-specific executable suffix
        exe_suffix = ".exe" if platform.system() == "Windows" else ""
        tool_with_suffix = f"{tool_name}{exe_suffix}"
        print(f"Tool with suffix: {tool_with_suffix}")

        # Search locations (exact same as HALCompressor)
        search_paths = [
            # Compiled tools directory (preferred)
            f"tools/{tool_with_suffix}",
            f"./tools/{tool_with_suffix}",
            # Current directory
            tool_with_suffix,
            f"./{tool_with_suffix}",
            # Archive directory (from codebase structure)
            f"../archive/obsolete_test_images/ultrathink/{tool_name}",
            f"../archive/obsolete_test_images/ultrathink/{tool_with_suffix}",
            # Parent directories
            f"../{tool_name}",
            f"../../{tool_name}",
            # System PATH
            tool_name,
        ]

        print(f"Searching {len(search_paths)} locations for {tool_name}")
        for i, path in enumerate(search_paths, 1):
            full_path = Path(path).resolve()
            exists = full_path.is_file()
            executable = False
            if exists:
                executable = os.access(full_path, os.X_OK)

            status = "FOUND" if exists else "not found"
            exec_status = f" (executable: {executable})" if exists else ""

            print(f"Location {i:2}/{len(search_paths)}: {status:9} - {full_path}{exec_status}")

            if exists:
                print(f"SUCCESS: Found {tool_name} at location {i}/{len(search_paths)}: {full_path}")
                if not executable:
                    print(f"WARNING: Found {tool_name} but it may not be executable: {full_path}")
                return str(full_path)

        print(f"FAILURE: Could not find {tool_name} executable in any search path")
        error_msg = (
            f"Could not find {tool_name} executable. "
            f"Please run 'python compile_hal_tools.py' to build for your platform."
        )
        raise Exception(error_msg)

    except Exception as e:
        print(f"ERROR: {e}")
        return None

def test_working_directory_impact():
    """Test if working directory affects detection"""

    print("\n" + "="*60)
    print("TESTING WORKING DIRECTORY IMPACT")
    print("="*60)

    original_cwd = os.getcwd()
    print(f"Original working directory: {original_cwd}")

    # Test from current directory
    result1 = test_exhal_detection(test_name="From spritepal directory")

    # Test from parent directory
    try:
        parent_dir = Path(original_cwd).parent
        print(f"\nChanging to parent directory: {parent_dir}")
        os.chdir(parent_dir)
        result2 = test_exhal_detection(test_name="From exhal-master directory")
    finally:
        os.chdir(original_cwd)

    # Test from root directory
    try:
        root_dir = Path(original_cwd).parts[0] + "/"
        if platform.system() != "Windows":  # Don't change to / on Windows
            print(f"\nChanging to root directory: {root_dir}")
            os.chdir(root_dir)
            result3 = test_exhal_detection(test_name="From root directory")
        else:
            result3 = None
    except Exception as e:
        print(f"Could not test from root directory: {e}")
        result3 = None
    finally:
        os.chdir(original_cwd)

    # Test from temp directory
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"\nChanging to temp directory: {temp_dir}")
            os.chdir(temp_dir)
            result4 = test_exhal_detection(test_name="From temp directory")
    except Exception as e:
        print(f"Error testing from temp directory: {e}")
        result4 = None
    finally:
        os.chdir(original_cwd)

    print("\n=== WORKING DIRECTORY IMPACT RESULTS ===")
    print(f"From spritepal directory: {'SUCCESS' if result1 else 'FAIL'}")
    print(f"From exhal-master directory: {'SUCCESS' if result2 else 'FAIL'}")
    print(f"From root directory: {'SUCCESS' if result3 else 'FAIL (or skipped)'}")
    print(f"From temp directory: {'SUCCESS' if result4 else 'FAIL'}")

    return result1, result2, result3, result4

def test_timing_sensitivity():
    """Test if there are timing-related issues"""

    print("\n" + "="*60)
    print("TESTING TIMING SENSITIVITY")
    print("="*60)

    results = []

    # Run detection multiple times in quick succession
    for i in range(10):
        print(f"\n--- Run {i+1}/10 ---")
        start_time = time.time()
        result = test_exhal_detection(test_name=f"Timing test {i+1}")
        end_time = time.time()
        duration = end_time - start_time

        success = result is not None
        results.append((success, duration))
        print(f"Result: {'SUCCESS' if success else 'FAIL'}, Duration: {duration:.4f}s")

        # Small delay between tests
        time.sleep(0.1)

    successes = sum(1 for success, _ in results if success)
    failures = len(results) - successes
    avg_duration = sum(duration for _, duration in results) / len(results)

    print("\n=== TIMING SENSITIVITY RESULTS ===")
    print(f"Total tests: {len(results)}")
    print(f"Successes: {successes}")
    print(f"Failures: {failures}")
    print(f"Success rate: {successes/len(results)*100:.1f}%")
    print(f"Average duration: {avg_duration:.4f}s")

    return results

def test_file_system_state():
    """Check the current state of the file system"""

    print("\n" + "="*60)
    print("TESTING FILE SYSTEM STATE")
    print("="*60)

    # Check if tools directory exists
    tools_dir = Path("tools")
    print(f"Tools directory exists: {tools_dir.exists()}")
    if tools_dir.exists():
        print("Tools directory contents:")
        try:
            for item in sorted(tools_dir.iterdir()):
                is_file = item.is_file()
                size = item.stat().st_size if is_file else "N/A"
                executable = os.access(item, os.X_OK) if is_file else False
                print(f"  {item.name:15} {'(file)' if is_file else '(dir)':6} {size:>8} bytes  executable: {executable}")
        except Exception as e:
            print(f"  Error reading tools directory: {e}")

    # Check specific exhal/inhal files
    exe_suffix = ".exe" if platform.system() == "Windows" else ""

    for tool in ["exhal", "inhal"]:
        tool_with_suffix = f"{tool}{exe_suffix}"
        tool_path = tools_dir / tool_with_suffix
        print(f"\n{tool} executable:")
        print(f"  Path: {tool_path}")
        print(f"  Exists: {tool_path.exists()}")
        if tool_path.exists():
            stat = tool_path.stat()
            print(f"  Size: {stat.st_size} bytes")
            print(f"  Executable: {os.access(tool_path, os.X_OK)}")
            print(f"  Modified: {time.ctime(stat.st_mtime)}")

def test_path_resolution():
    """Test path resolution under different conditions"""

    print("\n" + "="*60)
    print("TESTING PATH RESOLUTION")
    print("="*60)

    exe_suffix = ".exe" if platform.system() == "Windows" else ""
    tool_with_suffix = f"exhal{exe_suffix}"

    test_paths = [
        f"tools/{tool_with_suffix}",
        f"./tools/{tool_with_suffix}",
        f"../tools/{tool_with_suffix}",  # If run from parent
    ]

    for path in test_paths:
        p = Path(path)
        resolved = p.resolve()
        exists = p.exists()
        resolved_exists = resolved.exists() if resolved != p else "same"

        print(f"Path: {path}")
        print(f"  Resolved: {resolved}")
        print(f"  Original exists: {exists}")
        print(f"  Resolved exists: {resolved_exists}")
        print()

def main():
    """Run all diagnostic tests"""

    print("EXHAL DETECTION DIAGNOSTIC SCRIPT")
    print("="*60)
    print(f"Platform: {platform.system()}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Time: {time.ctime()}")

    # Test 1: Check file system state
    test_file_system_state()

    # Test 2: Test path resolution
    test_path_resolution()

    # Test 3: Basic detection test
    print("\n" + "="*60)
    print("BASIC DETECTION TEST")
    print("="*60)
    test_exhal_detection(test_name="Basic test")

    # Test 4: Working directory impact
    test_working_directory_impact()

    # Test 5: Timing sensitivity
    test_timing_sensitivity()

    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)
    print("If you see consistent failures, this indicates a real detection issue.")
    print("If you see intermittent failures, this suggests timing or working directory issues.")
    print("If all tests pass, the issue may be environment-specific or occur during manager initialization.")

if __name__ == "__main__":
    main()
