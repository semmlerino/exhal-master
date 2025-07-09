#!/usr/bin/env python3
"""
Test runner for Kirby Super Star Sprite Editor
Runs all unit and integration tests
"""

import sys
import unittest

# Test modules
TEST_MODULES = [
    "test_sprite_edit_helpers",
    "test_sprite_workflows",
    "test_integration_workflows"
]


class ColoredTextTestResult(unittest.TextTestResult):
    """Test result class with colored output"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.success_count = 0

    def addSuccess(self, test):
        super().addSuccess(test)
        self.success_count += 1
        if self.showAll:
            self.stream.writeln("\033[92m✓ PASS\033[0m")
        elif self.dots:
            self.stream.write("\033[92m.\033[0m")
            self.stream.flush()

    def addError(self, test, err):
        super().addError(test, err)
        if self.showAll:
            self.stream.writeln("\033[91m✗ ERROR\033[0m")
        elif self.dots:
            self.stream.write("\033[91mE\033[0m")
            self.stream.flush()

    def addFailure(self, test, err):
        super().addFailure(test, err)
        if self.showAll:
            self.stream.writeln("\033[91m✗ FAIL\033[0m")
        elif self.dots:
            self.stream.write("\033[91mF\033[0m")
            self.stream.flush()


class ColoredTextTestRunner(unittest.TextTestRunner):
    """Test runner with colored output"""
    resultclass = ColoredTextTestResult


def run_tests(verbosity=2, failfast=False):
    """Run all tests and return results"""
    print("Kirby Super Star Sprite Editor - Test Suite")
    print("=" * 60)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Load tests from each module
    for module_name in TEST_MODULES:
        try:
            module = __import__(module_name)
            tests = loader.loadTestsFromModule(module)
            suite.addTests(tests)
            print(f"✓ Loaded tests from {module_name}")
        except ImportError as e:
            print(f"✗ Failed to load {module_name}: {e}")

    print(f"\nTotal tests to run: {suite.countTestCases()}")
    print("-" * 60)

    # Run tests
    runner = ColoredTextTestRunner(
        verbosity=verbosity,
        failfast=failfast,
        stream=sys.stdout
    )

    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    success = total_tests - failures - errors

    print(f"Tests run: {total_tests}")
    print(f"\033[92m✓ Passed: {success}\033[0m")

    if failures > 0:
        print(f"\033[91m✗ Failed: {failures}\033[0m")

    if errors > 0:
        print(f"\033[91m✗ Errors: {errors}\033[0m")

    if result.wasSuccessful():
        print("\n\033[92m✅ All tests passed!\033[0m")
    else:
        print("\n\033[91m❌ Some tests failed!\033[0m")

    return result.wasSuccessful()


def run_specific_test(test_path):
    """Run a specific test method"""
    # Format: module.TestClass.test_method
    parts = test_path.split(".")

    if len(parts) < 2:
        print(f"Invalid test path: {test_path}")
        print("Format: module.TestClass.test_method")
        return False

    module_name = parts[0]

    try:
        module = __import__(module_name)

        if len(parts) == 2:
            # Run all tests in a class
            suite = unittest.TestLoader().loadTestsFromName(parts[1], module)
        else:
            # Run specific test method
            suite = unittest.TestLoader().loadTestsFromName(".".join(parts[1:]), module)

        runner = ColoredTextTestRunner(verbosity=2)
        result = runner.run(suite)
        return result.wasSuccessful()

    except Exception as e:
        print(f"Error running test: {e}")
        return False


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Run sprite editor tests")
    parser.add_argument("test", nargs="?", help="Specific test to run (e.g., test_sprite_workflows.TestSpriteEditWorkflow)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-f", "--failfast", action="store_true", help="Stop on first failure")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet output")

    args = parser.parse_args()

    # Determine verbosity
    if args.quiet:
        verbosity = 0
    elif args.verbose:
        verbosity = 2
    else:
        verbosity = 1

    # Run tests
    if args.test:
        # Run specific test
        success = run_specific_test(args.test)
    else:
        # Run all tests
        success = run_tests(verbosity=verbosity, failfast=args.failfast)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
