#!/usr/bin/env python3
from __future__ import annotations

"""Fix remaining Mock parent issues in test files."""

import re
from pathlib import Path

def fix_remaining_mock_issues(filepath: Path) -> None:
    """Fix remaining Mock parent issues that the automated script missed."""
    content = filepath.read_text()

    # Pattern 1: Fix test_arrangement_dialog_palette_integration
    # Lines around 514-520 where mock_window is created and used
    pattern1 = re.compile(
        r"(\s*)# Test arrangement with palette loading\n"
        r"(\s*)mock_window = Mock\(\)\n"
        r"(\s*)# Mock sprite preview with palettes\n"
        r"(\s*)mock_window\.sprite_preview = Mock\(\)\n"
        r"(\s*)mock_window\.sprite_preview\.get_palettes = Mock\(return_value=\{.*?\}\)\n"
        r"(\s*)\n"
        r"(\s*)# Create controller with mock window\n"
        r"(\s*)controller = ExtractionController\(mock_window\)",
        re.MULTILINE | re.DOTALL
    )

    if pattern1.search(content):
        replacement1 = (
            r'\1# Test arrangement with palette loading\n'
            r'\2# Use proper test helper instead of Mock\n'
            r'\2window_helper = TestMainWindowHelperSimple()\n'
            r'\3# Mock sprite preview with palettes\n'
            r'\4window_helper.sprite_preview.get_palettes = Mock(return_value={"8": [255, 0, 0]})\n'
            r'\6\n'
            r'\7# Create controller with test helper\n'
            r'\8controller = ExtractionController(window_helper)'
        )
        content = pattern1.sub(replacement1, content)

        # Also need to replace mock_window references in the patched_init function
        content = content.replace(
            "return original_init(sprite_file, tiles_per_row, parent_widget if parent is mock_window else parent)",
            "return original_init(sprite_file, tiles_per_row, parent_widget if parent is window_helper else parent)"
        )

    # Pattern 2: Fix lines where mock_window._output_path is set
    # Replace mock_window with controller.main_window
    pattern2 = re.compile(r"mock_window\._output_path = ", re.MULTILINE)
    content = pattern2.sub("controller._output_path = ", content)

    # Pattern 3: Fix mock_window.sprite_preview references
    pattern3 = re.compile(r"mock_window\.sprite_preview = Mock\(\)", re.MULTILINE)
    content = pattern3.sub("# Sprite preview already available via window_helper", content)

    pattern4 = re.compile(r"mock_window\.sprite_preview\.get_palettes\.return_value = ", re.MULTILINE)
    content = pattern4.sub("window_helper.sprite_preview.get_palettes = Mock(return_value=", content)

    # Pattern 4: Fix assertions that check mock_window as parent
    # Lines like: assert call_args[0][2] == mock_window
    pattern5 = re.compile(r"assert call_args\[0\]\[\d+\] == mock_window", re.MULTILINE)
    content = pattern5.sub("assert call_args[0][2] == window_helper", content)

    # Pattern 5: Fix any remaining mock_window occurrences in dialog calls
    pattern6 = re.compile(r", mock_window\)", re.MULTILINE)
    content = pattern6.sub(", window_helper)", content)

    # Pattern 6: Fix lines where mock_window is created but controller uses window_helper
    # Need to ensure consistency
    remaining_mock_windows = re.findall(r"(\s*)mock_window = Mock\(\)", content)
    if remaining_mock_windows:
        # Replace remaining mock_window = Mock() with comments
        content = re.sub(
            r"(\s*)mock_window = Mock\(\)\n",
            r"\1# Using window_helper instead of mock_window\n",
            content
        )

        # Replace controller = ExtractionController(mock_window) patterns that were missed
        content = re.sub(
            r"controller = ExtractionController\(mock_window\)",
            r"controller = ExtractionController(window_helper)",
            content
        )

    # Write back the fixed content
    filepath.write_text(content)
    print(f"Fixed remaining issues in {filepath}")

def main():
    """Main function to fix remaining Mock parent issues."""
    test_file = Path("tests/test_cross_dialog_integration.py")

    if not test_file.exists():
        print(f"Error: {test_file} not found")
        return

    print(f"Fixing remaining Mock parent issues in {test_file}")
    fix_remaining_mock_issues(test_file)

if __name__ == "__main__":
    main()
