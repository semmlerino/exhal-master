#!/usr/bin/env python3
"""
Analyze PLC0415 violations to understand why imports are inside functions.
"""

import subprocess
from collections import defaultdict
from pathlib import Path

# Categories of imports that might be inside functions
CATEGORIES = {
    "circular_import": ["get_settings_manager", "get_rom_cache", "get_extraction_manager", "ManagerRegistry"],
    "lazy_loading": ["PIL", "numpy", "matplotlib", "psutil"],
    "multiprocessing": ["signal", "multiprocessing", "concurrent"],
    "optional_dependency": ["pytest", "coverage", "benchmark"],
    "platform_specific": ["winreg", "pwd", "grp"],
}


def analyze_violations():
    """Analyze all PLC0415 violations and categorize them."""

    # Get all violations
    result = subprocess.run(
        ["./venv/bin/ruff", "check", "--select", "PLC0415", "--output-format", "json"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0 and result.stdout:
        import json
        violations = json.loads(result.stdout)
    else:
        print("No violations found or error running ruff")
        return

    # Categorize violations
    categorized = defaultdict(list)
    uncategorized = []

    for violation in violations:
        file_path = violation["filename"]
        line_num = violation["location"]["row"]

        # Read the line to see what's being imported
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()
                if line_num <= len(lines):
                    import_line = lines[line_num - 1].strip()

                    # Try to categorize
                    categorized_flag = False
                    for category, patterns in CATEGORIES.items():
                        for pattern in patterns:
                            if pattern.lower() in import_line.lower():
                                categorized[category].append({
                                    "file": file_path,
                                    "line": line_num,
                                    "import": import_line
                                })
                                categorized_flag = True
                                break
                        if categorized_flag:
                            break

                    if not categorized_flag:
                        # Check if it's in a test file
                        if "/test" in file_path or file_path.startswith("test"):
                            categorized["test_imports"].append({
                                "file": file_path,
                                "line": line_num,
                                "import": import_line
                            })
                        else:
                            uncategorized.append({
                                "file": file_path,
                                "line": line_num,
                                "import": import_line
                            })
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    # Generate report
    print("PLC0415 VIOLATION ANALYSIS")
    print("=" * 60)
    print(f"Total violations: {len(violations)}")
    print()

    # Show categorized violations
    for category, items in sorted(categorized.items()):
        print(f"\n{category.upper().replace('_', ' ')} ({len(items)} violations):")
        print("-" * 40)

        # Show first 5 examples
        for item in items[:5]:
            file_path = Path(item['file']).name if '/' in item['file'] else item['file']
            print(f"  {file_path} L{item['line']}")
            print(f"    {item['import']}")

        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")

    # Show uncategorized
    if uncategorized:
        print(f"\nUNCATEGORIZED ({len(uncategorized)} violations):")
        print("-" * 40)
        for item in uncategorized[:10]:
            file_path = Path(item['file']).name if '/' in item['file'] else item['file']
            print(f"  {file_path} L{item['line']}")
            print(f"    {item['import']}")

        if len(uncategorized) > 10:
            print(f"  ... and {len(uncategorized) - 10} more")

    # Summary recommendations
    print("\n\nRECOMMENDATIONS:")
    print("=" * 60)
    print("1. CIRCULAR IMPORTS: Keep these inside functions to prevent import cycles")
    print("2. TEST IMPORTS: Can be moved to top-level in most cases")
    print("3. LAZY LOADING: Keep for performance if importing heavy libraries")
    print("4. MULTIPROCESSING: Keep inside worker functions for process isolation")
    print("5. OPTIONAL DEPENDENCIES: Keep inside functions to handle missing packages gracefully")


if __name__ == "__main__":
    analyze_violations()