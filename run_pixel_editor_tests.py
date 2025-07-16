#!/usr/bin/env python3
"""
Test Runner for Pixel Editor
Runs tests in the correct order to catch integration issues early.
"""

import os
import subprocess
import sys
import time
from pathlib import Path


class TestRunner:
    """Manages test execution for pixel editor"""

    def __init__(self):
        self.python = sys.executable
        self.failed_tests = []
        self.test_times = {}

        # Set Qt to offscreen mode
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["QT_LOGGING_RULES"] = "*.debug=false"

    def run_test_file(self, test_file, description):
        """Run a single test file and track results"""
        print(f"\n{'='*60}")
        print(f"Running: {description}")
        print(f"File: {test_file}")
        print("=" * 60)

        start_time = time.time()

        cmd = [self.python, "-m", "pytest", test_file, "-v", "--tb=short"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        elapsed = time.time() - start_time
        self.test_times[test_file] = elapsed

        if result.returncode != 0:
            self.failed_tests.append((test_file, description))
            print(f"❌ FAILED in {elapsed:.2f}s")
            if result.stdout:
                print("\nOutput:")
                print(result.stdout)
            if result.stderr:
                print("\nErrors:")
                print(result.stderr)
        else:
            print(f"✅ PASSED in {elapsed:.2f}s")

        return result.returncode == 0

    def run_test_category(self, pattern, description):
        """Run tests matching a pattern"""
        print(f"\n{'='*60}")
        print(f"Running: {description}")
        print(f"Pattern: {pattern}")
        print("=" * 60)

        start_time = time.time()

        cmd = [self.python, "-m", "pytest", "-k", pattern, "-v", "--tb=short"]
        result = subprocess.run(cmd, check=False)

        elapsed = time.time() - start_time
        self.test_times[pattern] = elapsed

        if result.returncode != 0:
            self.failed_tests.append((pattern, description))
            print(f"❌ FAILED in {elapsed:.2f}s")
        else:
            print(f"✅ PASSED in {elapsed:.2f}s")

        return result.returncode == 0

    def check_imports(self):
        """Verify all pixel editor modules can be imported"""
        print("\n" + "=" * 60)
        print("Checking module imports...")
        print("=" * 60)

        modules = [
            "indexed_pixel_editor",
            "pixel_editor_widgets",
            "pixel_editor_workers",
            "pixel_editor_commands",
            "pixel_editor_utils",
            "pixel_editor_constants",
        ]

        failed_imports = []

        for module in modules:
            try:
                __import__(module)
                print(f"✅ {module}")
            except ImportError as e:
                print(f"❌ {module}: {e}")
                failed_imports.append(module)

        if failed_imports:
            print(f"\n❌ Import check failed for: {', '.join(failed_imports)}")
            return False

        print("\n✅ All modules imported successfully!")
        return True

    def run_all_tests(self):
        """Run all pixel editor tests in order"""
        print("Pixel Editor Test Suite")
        print("=" * 60)
        print(f"Python: {sys.version}")
        print(f"Working directory: {os.getcwd()}")

        # Check imports first
        if not self.check_imports():
            print("\n❌ Cannot proceed - import errors must be fixed first")
            return 1

        # Phase 1: Critical Tests (would have caught ProgressDialog bug)
        print("\n\nPHASE 1: Critical Integration Tests")
        print("-" * 60)

        tests_phase1 = [
            (
                "pixel_editor/tests/test_pixel_editor_integration.py",
                "Integration Tests - Component Interactions",
            ),
            (
                "pixel_editor/tests/test_api_contracts.py",
                "API Contract Tests - Method Signatures",
            ),
            (
                "pixel_editor/tests/test_component_boundaries.py",
                "Boundary Tests - Cross-Component",
            ),
        ]

        for test_file, description in tests_phase1:
            if Path(test_file).exists():
                self.run_test_file(test_file, description)
            else:
                print(f"⚠️  Skipping {test_file} - file not found")

        # Phase 2: Unit Tests
        print("\n\nPHASE 2: Unit Tests")
        print("-" * 60)

        unit_tests = [
            (
                "pixel_editor/tests/test_indexed_pixel_editor_enhanced.py",
                "Enhanced Pixel Editor Tests",
            ),
            ("pixel_editor/tests/test_pixel_editor_core.py", "Core Pixel Editor Tests"),
        ]

        for test_file, description in unit_tests:
            if Path(test_file).exists():
                self.run_test_file(test_file, description)

        # Phase 3: Performance Tests
        print("\n\nPHASE 3: Performance & Benchmark Tests")
        print("-" * 60)

        perf_tests = [
            (
                "pixel_editor/tests/test_phase1_improvements.py",
                "Phase 1 Performance Tests",
            ),
            (
                "pixel_editor/tests/benchmark_phase1_enhanced.py",
                "Performance Benchmarks",
            ),
        ]

        for test_file, description in perf_tests:
            if Path(test_file).exists():
                self.run_test_file(test_file, description)

        # Phase 4: Sprite Editor Tests (if requested)
        if "--all" in sys.argv:
            print("\n\nPHASE 4: Sprite Editor Tests")
            print("-" * 60)
            self.run_test_category("sprite_editor", "All Sprite Editor Tests")

        # Summary
        self.print_summary()

        return len(self.failed_tests)

    def print_summary(self):
        """Print test execution summary"""
        print("\n\n" + "=" * 60)
        print("TEST EXECUTION SUMMARY")
        print("=" * 60)

        # Timing summary
        if self.test_times:
            print("\nTest Execution Times:")
            for test, elapsed in sorted(
                self.test_times.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {test}: {elapsed:.2f}s")
            print(f"\nTotal time: {sum(self.test_times.values()):.2f}s")

        # Results summary
        if self.failed_tests:
            print(f"\n❌ {len(self.failed_tests)} test group(s) FAILED:")
            for test, desc in self.failed_tests:
                print(f"  - {desc} ({test})")
        else:
            print("\n✅ All tests PASSED!")

        # Recommendations
        if self.failed_tests:
            print("\nRecommendations:")
            print("1. Fix failing tests before committing")
            print("2. Run 'pre-commit install' to enable automatic testing")
            print("3. Check test output above for specific failures")


def main():
    """Main entry point"""
    runner = TestRunner()

    # Special modes
    if "--quick" in sys.argv:
        print("Running quick critical tests only...")
        # Just run the most critical tests
        if Path("pixel_editor/tests/test_pixel_editor_integration.py").exists():
            success = runner.run_test_file(
                "pixel_editor/tests/test_pixel_editor_integration.py",
                "Critical Integration Tests",
            )
            return 0 if success else 1

    # Normal mode - run all tests
    return runner.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
