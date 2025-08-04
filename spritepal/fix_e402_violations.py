#!/usr/bin/env python3
"""
Fix E402 violations: Move imports to the top of files.
"""

import os

# Files with E402 violations identified by ruff
E402_FILES = [
    "debug_duplicate_slider.py",
    "scripts/analysis/analyze_vram_dump.py",
    "scripts/analysis/find_sprites_in_rom.py",
    "scripts/test_runners/test_simple_real_integration.py",
    "test_preview_performance.py",
    "tests/test_controller_fix_validation.py",
    "tests/test_controller_real_manager_integration.py",
    "tests/test_dialog_real_integration.py",
    "tests/test_main_window_state_integration_real.py",
    "tests/test_no_duplicate_sliders_validation.py",
]


def fix_file(file_path: str) -> bool:
    """Fix E402 violations in a single file."""
    print(f"\nProcessing: {file_path}")

    if not os.path.exists(file_path):
        print(f"  Warning: File not found: {file_path}")
        return False

    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    # Find the shebang, docstring, and existing imports
    shebang_lines = []
    docstring_lines = []
    import_lines = []
    path_setup_lines = []
    other_lines = []

    in_docstring = False
    docstring_quotes = None
    found_path_setup = False
    import_start_line = None

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Handle shebang
        if i == 0 and line.startswith("#!"):
            shebang_lines.append(line)
            i += 1
            continue

        # Handle module docstring
        if not in_docstring and not import_lines and not other_lines:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_quotes = '"""' if stripped.startswith('"""') else "'''"
                in_docstring = True
                docstring_lines.append(line)
                # Check if docstring ends on same line
                if stripped.count(docstring_quotes) >= 2:
                    in_docstring = False
                i += 1
                continue

        # Continue collecting docstring
        if in_docstring:
            docstring_lines.append(line)
            if docstring_quotes in line:
                in_docstring = False
            i += 1
            continue

        # Handle path setup (sys.path manipulations)
        if not found_path_setup and ("sys.path" in line or "parent_dir" in line or "__file__" in line):
            path_setup_lines.append(line)
            # Look for complete path setup block
            if "sys.path" in line:
                found_path_setup = True
            i += 1
            continue

        # If we found path setup, continue collecting until we find imports or other code
        if found_path_setup and not stripped:
            path_setup_lines.append(line)
            i += 1
            continue

        # Handle imports
        if (stripped.startswith("import ") or stripped.startswith("from ") or
            (stripped and any(line.strip().startswith(imp) for imp in ["import ", "from "]))):
            if import_start_line is None:
                import_start_line = i
            import_lines.append(line)
            i += 1
            continue

        # Handle comments between imports
        if import_lines and (stripped.startswith("#") or not stripped):
            import_lines.append(line)
            i += 1
            continue

        # Everything else is other code
        other_lines.extend(lines[i:])
        break

    # Now reorganize the file
    new_lines = []

    # Add shebang
    new_lines.extend(shebang_lines)

    # Add docstring
    new_lines.extend(docstring_lines)

    # Add blank line after docstring if needed
    if docstring_lines and not docstring_lines[-1].strip() == "":
        new_lines.append("\n")

    # Add path setup if exists
    if path_setup_lines:
        # Ensure blank line before path setup if there's a docstring
        if docstring_lines:
            new_lines.append("\n")
        new_lines.extend(path_setup_lines)
        # Ensure blank line after path setup
        if not path_setup_lines[-1].strip() == "":
            new_lines.append("\n")

    # Sort and organize imports
    stdlib_imports = []
    third_party_imports = []
    local_imports = []

    for line in import_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Determine import type
        if stripped.startswith("from .") or stripped.startswith("from core") or stripped.startswith("from ui") or stripped.startswith("from utils"):
            local_imports.append(line)
        elif any(stripped.startswith(f"from {pkg}") or stripped.startswith(f"import {pkg}")
                for pkg in ["PyQt6", "PySide6", "numpy", "PIL", "pytest"]):
            third_party_imports.append(line)
        # Check if it's a known stdlib module
        elif any(stripped.startswith(f"import {mod}") or stripped.startswith(f"from {mod}")
              for mod in ["os", "sys", "time", "datetime", "pathlib", "tempfile", "traceback", "json", "re", "typing", "collections", "itertools", "functools"]):
            stdlib_imports.append(line)
        else:
            # Default to third party if unsure
            third_party_imports.append(line)

    # Add organized imports
    if stdlib_imports:
        new_lines.extend(sorted(set(stdlib_imports)))
        new_lines.append("\n")

    if third_party_imports:
        new_lines.extend(sorted(set(third_party_imports)))
        new_lines.append("\n")

    if local_imports:
        new_lines.extend(sorted(set(local_imports)))
        new_lines.append("\n")

    # Add the rest of the code
    new_lines.extend(other_lines)

    # Write back
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"  Fixed: {file_path}")
    return True


def main():
    """Fix all E402 violations."""
    print("Fixing E402 violations (imports not at top of file)")
    print("=" * 60)

    fixed_count = 0
    for file_path in E402_FILES:
        if fix_file(file_path):
            fixed_count += 1

    print(f"\nFixed {fixed_count}/{len(E402_FILES)} files")

    # Run ruff to verify
    print("\nVerifying fixes with ruff...")
    os.system("source venv/bin/activate && ruff check --select E402 | grep E402 | wc -l")


if __name__ == "__main__":
    main()
