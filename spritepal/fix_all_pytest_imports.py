#!/usr/bin/env python3
"""
Fix all missing pytest imports in test files.
"""

import os
import re
from pathlib import Path

def needs_pytest_import(file_path):
    """Check if file uses pytest but doesn't import it."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if pytest is used but not imported
    uses_pytest = 'pytest.' in content or 'pytestmark' in content
    has_import = 'import pytest' in content
    
    return uses_pytest and not has_import

def add_pytest_import(file_path):
    """Add pytest import to a file."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Find the best place to add the import
    # After docstring, before pytestmark, or at the beginning
    
    import_added = False
    new_lines = []
    in_docstring = False
    docstring_end = -1
    
    for i, line in enumerate(lines):
        # Track docstrings
        if '"""' in line or "'''" in line:
            if not in_docstring:
                in_docstring = True
            else:
                in_docstring = False
                docstring_end = i
        
        # If we just finished a docstring and haven't added import yet
        if docstring_end == i and not import_added:
            new_lines.append(line)
            new_lines.append('\nimport pytest\n')
            import_added = True
        # If we hit pytestmark and haven't added import yet
        elif 'pytestmark' in line and not import_added:
            new_lines.append('import pytest\n\n')
            new_lines.append(line)
            import_added = True
        else:
            new_lines.append(line)
    
    # If we didn't add it yet, add at the beginning
    if not import_added:
        new_lines.insert(0, 'import pytest\n\n')
    
    with open(file_path, 'w') as f:
        f.writelines(new_lines)
    
    return True

def main():
    """Fix all test files missing pytest imports."""
    test_dir = Path('tests')
    
    # Find all Python test files
    test_files = list(test_dir.glob('**/*.py'))
    
    fixed_count = 0
    error_files = []
    
    for test_file in test_files:
        if needs_pytest_import(test_file):
            try:
                add_pytest_import(test_file)
                print(f"Fixed: {test_file}")
                fixed_count += 1
            except Exception as e:
                print(f"Error fixing {test_file}: {e}")
                error_files.append(test_file)
    
    print(f"\n{'='*60}")
    print(f"Fixed {fixed_count} files")
    
    if error_files:
        print(f"\nFailed to fix {len(error_files)} files:")
        for f in error_files:
            print(f"  - {f}")
    
    return 0 if not error_files else 1

if __name__ == '__main__':
    import sys
    sys.exit(main())