#!/usr/bin/env python3
"""
Fix Qt boolean evaluation issues throughout the codebase.

This script automatically fixes patterns like:
    if self.widget:
to:
    if self.widget is not None:

to prevent crashes when Qt containers evaluate to False when empty.
"""

import re
from pathlib import Path

# Pattern to match problematic boolean evaluations
# Matches: if self.something: or if not self.something:
BOOLEAN_PATTERN = re.compile(
    r"^(\s*)if\s+(not\s+)?self\.([a-zA-Z_][a-zA-Z0-9_]*)\s*:"
)

# Pattern to check if already uses "is None" or "is not None"
NONE_CHECK_PATTERN = re.compile(
    r"if\s+.*\s+is\s+(not\s+)?None"
)

# Qt types that can evaluate to False when empty
QT_TYPES = {
    "layout", "widget", "button", "label", "combo", "list", "tree",
    "table", "text", "edit", "browser", "view", "model", "menu",
    "action", "toolbar", "status", "dock", "dialog", "window",
    "splitter", "tab", "stack", "scroll", "frame", "group",
    "check", "radio", "spin", "slider", "progress", "lcd"
}

def is_likely_qt_object(var_name: str) -> bool:
    """Check if variable name suggests it's a Qt object."""
    var_lower = var_name.lower()

    # Check for common Qt suffixes/prefixes
    for qt_type in QT_TYPES:
        if qt_type in var_lower:
            return True

    # Check for common naming patterns
    return bool(var_lower.endswith(("_widget", "_layout", "_dialog", "_view", "_model")))

def fix_boolean_evaluation(line: str, line_num: int, file_path: Path) -> tuple[str, bool]:
    """Fix a single line if it contains problematic boolean evaluation."""
    # Skip if already has None check
    if NONE_CHECK_PATTERN.search(line):
        return line, False

    match = BOOLEAN_PATTERN.match(line)
    if not match:
        return line, False

    indent = match.group(1)
    negation = match.group(2) or ""
    var_name = match.group(3)

    # Only fix if it looks like a Qt object
    if not is_likely_qt_object(var_name):
        return line, False

    # Construct the fixed line
    if negation:
        # if not self.widget: -> if self.widget is None:
        fixed = f"{indent}if self.{var_name} is None:\n"
    else:
        # if self.widget: -> if self.widget is not None:
        fixed = f"{indent}if self.{var_name} is not None:\n"

    print(f"  {file_path}:{line_num}: Fixed '{var_name}' boolean check")
    return fixed, True

def process_file(file_path: Path) -> int:
    """Process a single Python file and fix boolean evaluations."""
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

    fixed_count = 0
    modified_lines = []

    for i, line in enumerate(lines, 1):
        fixed_line, was_fixed = fix_boolean_evaluation(line, i, file_path)
        modified_lines.append(fixed_line)
        if was_fixed:
            fixed_count += 1

    # Write back if any changes were made
    if fixed_count > 0:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(modified_lines)
            print(f"✓ Fixed {fixed_count} issues in {file_path}")
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return 0

    return fixed_count

def main():
    """Main entry point."""
    print("Qt Boolean Evaluation Fixer")
    print("==========================")
    print()

    # Files with known issues from the validation report
    priority_files = [
        "ui/managers/status_bar_manager.py",
        "ui/components/navigation/region_jump_widget.py",
        "ui/dialogs/manual_offset_unified_integrated.py",
        "ui/components/navigation/sprite_navigator.py",
    ]

    total_fixed = 0

    # First process priority files
    print("Processing priority files with known issues...")
    for file_path in priority_files:
        path = Path(file_path)
        if path.exists():
            count = process_file(path)
            total_fixed += count

    print()
    print("Scanning all UI files for additional issues...")

    # Then scan all UI files
    ui_dir = Path("ui")
    if ui_dir.exists():
        for py_file in ui_dir.rglob("*.py"):
            # Skip if already processed
            if str(py_file) not in priority_files:
                count = process_file(py_file)
                total_fixed += count

    print()
    print(f"Total issues fixed: {total_fixed}")

    if total_fixed > 0:
        print("\nIMPORTANT: Please review the changes and run tests to ensure correctness.")
        print("Some boolean checks might be intentional and may need manual review.")

if __name__ == "__main__":
    main()
