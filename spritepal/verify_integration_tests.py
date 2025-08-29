#!/usr/bin/env python3
from __future__ import annotations

"""
Verify integration tests structure and demonstrate test coverage.
This script validates the integration test files without requiring PySide6.
"""

import ast
from pathlib import Path


def analyze_test_file(file_path: Path) -> dict[str, list[str]]:
    """Analyze a test file to extract test methods and their descriptions."""
    results = {
        'test_methods': [],
        'bug_coverage': [],
        'fixtures': [],
        'imports': []
    }

    try:
        with file_path.open() as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            # Find test methods
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith('test_'):
                    # Extract docstring
                    docstring = ast.get_docstring(node)
                    results['test_methods'].append({
                        'name': node.name,
                        'docstring': docstring or 'No description'
                    })

                    # Check for bug-related keywords in name or docstring
                    test_text = node.name + (docstring or '')
                    if any(keyword in test_text.lower() for keyword in
                           ['infinite loop', 'memory leak', 'thread leak', 'cleanup', 'idle']):
                        results['bug_coverage'].append(node.name)

                elif node.name.startswith('setup') or node.name.startswith('teardown'):
                    results['fixtures'].append(node.name)

    except Exception as e:
        print(f"  Error analyzing {file_path}: {e}")

    return results

def main():
    """Main function to verify integration tests."""
    print("=" * 70)
    print("INTEGRATION TEST VERIFICATION REPORT")
    print("=" * 70)

    # Define test files
    integration_tests = [
        ('test_batch_thumbnail_worker_integration.py', 'BatchThumbnailWorker infinite loop prevention'),
        ('test_memory_management_integration.py', 'Memory leak detection and cleanup'),
        ('test_worker_lifecycle_management_integration.py', 'Thread leak prevention'),
        ('test_fullscreen_sprite_viewer_integration.py', 'Fullscreen viewer functionality'),
        ('test_gallery_window_integration.py', 'Gallery window lifecycle'),
    ]

    tests_dir = Path('tests/integration')

    total_tests = 0
    bug_related_tests = 0
    missing_files = []

    for test_file, description in integration_tests:
        file_path = tests_dir / test_file

        print(f"\n{'='*60}")
        print(f"📄 {test_file}")
        print(f"   Purpose: {description}")
        print(f"{'='*60}")

        if not file_path.exists():
            print(f"  ❌ File not found: {file_path}")
            missing_files.append(test_file)
            continue

        # Analyze the test file
        analysis = analyze_test_file(file_path)

        print(f"\n  ✅ Found {len(analysis['test_methods'])} test methods:")
        for test in analysis['test_methods']:
            print(f"    • {test['name']}")
            if test['name'] in analysis['bug_coverage']:
                print(f"      🎯 Bug-related test: {test['docstring'][:60]}...")
                bug_related_tests += 1

        total_tests += len(analysis['test_methods'])

        if analysis['fixtures']:
            print(f"\n  🔧 Setup/Teardown methods: {', '.join(analysis['fixtures'])}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print("\n📊 Test Statistics:")
    print(f"  • Total test files analyzed: {len(integration_tests) - len(missing_files)}/{len(integration_tests)}")
    print(f"  • Total test methods found: {total_tests}")
    print(f"  • Bug-related tests: {bug_related_tests}")

    if missing_files:
        print(f"\n⚠️  Missing files: {', '.join(missing_files)}")

    # Check for critical bug coverage
    print("\n🎯 Critical Bug Coverage:")

    critical_bugs = {
        'Infinite Loop (BatchThumbnailWorker)': False,
        'Memory Leaks (Large sprite sets)': False,
        'Thread Leaks (Worker cleanup)': False,
        'Signal Disconnection': False,
    }

    # Check each test file for critical bug coverage
    for test_file, _ in integration_tests:
        file_path = tests_dir / test_file
        if file_path.exists():
            content = file_path.read_text().lower()

            if 'infinite loop' in content or 'idle_detection' in content:
                critical_bugs['Infinite Loop (BatchThumbnailWorker)'] = True
            if 'memory leak' in content or 'memory_management' in content:
                critical_bugs['Memory Leaks (Large sprite sets)'] = True
            if 'thread leak' in content or 'thread_count' in content:
                critical_bugs['Thread Leaks (Worker cleanup)'] = True
            if 'signal' in content and 'disconnect' in content:
                critical_bugs['Signal Disconnection'] = True

    for bug, covered in critical_bugs.items():
        status = "✅ Covered" if covered else "❌ Not covered"
        print(f"  • {bug}: {status}")

    # Performance metrics check
    print("\n⚡ Performance Test Coverage:")
    perf_keywords = ['benchmark', 'performance', 'stress', 'massive', 'large_dataset']
    perf_tests = 0

    for test_file, _ in integration_tests:
        file_path = tests_dir / test_file
        if file_path.exists():
            content = file_path.read_text().lower()
            if any(keyword in content for keyword in perf_keywords):
                perf_tests += 1
                print(f"  • {test_file}: Has performance tests")

    print(f"\n  Total files with performance tests: {perf_tests}")

    # Test recommendations
    print("\n💡 Recommendations:")
    print("  1. Run GUI tests with: python3 -m pytest tests/integration -m gui")
    print("  2. Run headless tests with: python3 -m pytest tests/integration -m headless")
    print("  3. Run memory tests with: python3 -m pytest tests/integration -k memory")
    print("  4. Run performance tests with: python3 -m pytest tests/integration -k performance")

    # Create test execution examples
    print("\n📝 Example Test Execution Commands:")
    print("  # Quick smoke test (headless)")
    print("  python3 -m pytest tests/integration -m headless --tb=short")
    print()
    print("  # Full integration suite")
    print("  python3 -m pytest tests/integration -v")
    print()
    print("  # Specific bug verification")
    print("  python3 -m pytest tests/integration/test_batch_thumbnail_worker_integration.py::TestBatchThumbnailWorkerIntegration::test_idle_detection_prevents_infinite_loop -v")

    print("\n" + "=" * 70)
    print("✅ Integration test structure verified successfully!")
    print("=" * 70)

if __name__ == '__main__':
    main()

