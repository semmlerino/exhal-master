#!/usr/bin/env python3
from __future__ import annotations

"""Fix Mock parent issues in test files by replacing Mock() with proper test helpers."""

import re
from pathlib import Path

def fix_mock_parent_issues(filepath: Path) -> None:
    """Fix Mock parent issues in a test file."""
    content = filepath.read_text()

    # Track if we need to add the import
    needs_import = False

    # Pattern to find mock_window = Mock() followed by ExtractionController
    pattern = re.compile(
        r"(\s*)mock_window = Mock\(\)\n"
        r"(\s*)controller = ExtractionController\(mock_window\)",
        re.MULTILINE
    )

    # Check if we have any matches
    if pattern.search(content):
        needs_import = True

        # Replace with proper test helper
        replacement = (
            r"\1# Use proper test helper instead of Mock\n"
            r"\1window_helper = TestMainWindowHelperSimple()\n"
            r"\2controller = ExtractionController(window_helper)"
        )

        content = pattern.sub(replacement, content)

        # Also need to add cleanup calls after controller usage
        # Find test method boundaries to add cleanup
        re.findall(r"def (test_\w+)\(.*?\):", content)

        # Add import if needed
        if needs_import and "TestMainWindowHelperSimple" not in content:
            # Find the imports section
            import_match = re.search(r"(from unittest\.mock import.*?\n)", content)
            if import_match:
                import_line = import_match.group(1)
                new_import = (
                    import_line +
                    "from tests.fixtures.test_main_window_helper_simple import TestMainWindowHelperSimple\n"
                )
                content = content.replace(import_line, new_import)
            else:
                # Add at the top after other imports
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    if line.startswith(("import ", "from ")):
                        continue
                    if not line.strip():
                        continue
                    # Found first non-import line
                    lines.insert(i, "from tests.fixtures.test_main_window_helper_simple import TestMainWindowHelperSimple")
                    lines.insert(i+1, "")
                    break
                content = "\n".join(lines)

        # Add cleanup calls where needed
        # This is more complex - for now just add a note
        if "window_helper.cleanup()" not in content:
            print("Note: Remember to add window_helper.cleanup() calls at the end of test methods that use window_helper")

    # Write back the fixed content
    filepath.write_text(content)
    print(f"Fixed {filepath}")

def add_cleanups_to_test(content: str) -> str:
    """Add cleanup calls to test methods that use window_helper."""
    # This is a more complex transformation that would require AST parsing
    # For now, we'll just ensure the one we manually fixed has cleanup
    return content

def main():
    """Main function to fix Mock parent issues."""
    test_file = Path("tests/test_cross_dialog_integration.py")

    if not test_file.exists():
        print(f"Error: {test_file} not found")
        return

    print(f"Fixing Mock parent issues in {test_file}")
    fix_mock_parent_issues(test_file)

    # Also check for other test files with similar issues
    test_dir = Path("tests")
    for test_file in test_dir.glob("test_*.py"):
        content = test_file.read_text()
        if "mock_window = Mock()" in content and "ExtractionController(mock_window)" in content:
            print(f"\nFound Mock parent issues in {test_file}")
            fix_mock_parent_issues(test_file)

if __name__ == "__main__":
    main()
