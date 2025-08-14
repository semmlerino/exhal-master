#!/usr/bin/env python3
"""
Fix missing commas in pytestmark lists in test files.
This script finds and fixes syntax errors caused by missing commas.
"""

import re
import sys
from pathlib import Path

def fix_pytestmark_commas(file_path):
    """Fix missing commas in pytestmark lists."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    fixed = False
    in_pytestmark = False
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if we're starting a pytestmark list
        if 'pytestmark' in line and '[' in line:
            in_pytestmark = True
        
        # If we're in a pytestmark list
        if in_pytestmark:
            # Check if this line ends the list
            if ']' in line:
                in_pytestmark = False
            # Check if this line has a pytest.mark but no comma at the end
            elif 'pytest.mark' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                # If the current line doesn't end with a comma and the next line also has pytest.mark
                if not line.rstrip().endswith(',') and not line.rstrip().endswith('[') and 'pytest.mark' in next_line:
                    # Add comma
                    lines[i] = line.rstrip() + ',\n'
                    fixed = True
                    print(f"  Fixed line {i+1}: added comma after {line.strip()}")
        
        i += 1
    
    if fixed:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        return True
    return False

def main():
    """Find and fix all test files with missing commas."""
    test_dir = Path('tests')
    
    # Find all Python test files
    test_files = list(test_dir.glob('**/*.py'))
    
    print(f"Checking {len(test_files)} test files for missing commas...")
    
    fixed_count = 0
    for test_file in test_files:
        # Try to compile the file to check for syntax errors
        try:
            with open(test_file, 'r') as f:
                compile(f.read(), test_file, 'exec')
        except SyntaxError as e:
            if 'forgot a comma' in str(e):
                print(f"\nFixing {test_file}...")
                if fix_pytestmark_commas(test_file):
                    fixed_count += 1
                    # Verify the fix
                    try:
                        with open(test_file, 'r') as f:
                            compile(f.read(), test_file, 'exec')
                        print(f"  ✓ Fixed successfully")
                    except SyntaxError:
                        print(f"  ✗ Still has syntax errors")
    
    print(f"\n{'='*60}")
    print(f"Fixed {fixed_count} files")
    
    # Now check for any remaining syntax errors
    print(f"\nChecking for remaining syntax errors...")
    error_count = 0
    for test_file in test_files:
        try:
            with open(test_file, 'r') as f:
                compile(f.read(), test_file, 'exec')
        except SyntaxError as e:
            print(f"  {test_file}: {e}")
            error_count += 1
    
    if error_count == 0:
        print("  ✓ No syntax errors found!")
    else:
        print(f"  ✗ {error_count} files still have syntax errors")
    
    return 0 if error_count == 0 else 1

if __name__ == '__main__':
    sys.exit(main())