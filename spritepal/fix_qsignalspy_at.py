#!/usr/bin/env python3
"""Fix QSignalSpy access to use .at() method instead of list() or subscript."""

import re
from pathlib import Path

def fix_qsignalspy_at(file_path: Path) -> bool:
    """Fix QSignalSpy access to use .at() method."""
    content = file_path.read_text()
    original_content = content
    
    # Pattern 1: list(spy)[index] -> spy.at(index)
    content = re.sub(
        r'list\(([a-zA-Z_][a-zA-Z0-9_]*_spy)\)\[(\d+)\]',
        r'\1.at(\2)',
        content
    )
    
    # Pattern 2: list(spy)[-1] -> spy.at(spy.count() - 1)
    content = re.sub(
        r'list\(([a-zA-Z_][a-zA-Z0-9_]*_spy)\)\[-1\]',
        r'\1.at(\1.count() - 1)',
        content
    )
    
    # Pattern 3: for accessing parts of signal data
    # spy.at(0)[0] for first element of first signal
    # This pattern is already correct, just ensuring
    
    if content != original_content:
        file_path.write_text(content)
        return True
    return False

def main():
    """Find and fix all QSignalSpy access issues in test files."""
    test_dir = Path("/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master/spritepal/tests")
    
    fixed_files = []
    
    # Find all Python test files
    for file_path in test_dir.rglob("*.py"):
        if fix_qsignalspy_at(file_path):
            fixed_files.append(file_path)
    
    if fixed_files:
        print(f"Fixed {len(fixed_files)} files:")
        for file_path in fixed_files:
            print(f"  - {file_path.relative_to(test_dir.parent)}")
    else:
        print("No files needed fixing")
    
    return len(fixed_files)

if __name__ == "__main__":
    exit(0 if main() > 0 else 1)