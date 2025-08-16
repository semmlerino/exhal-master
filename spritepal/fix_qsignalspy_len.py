#!/usr/bin/env python3
"""Fix QSignalSpy len() usage to use count() instead."""

import re
from pathlib import Path

def fix_qsignalspy_len(file_path: Path) -> bool:
    """Fix len(xxx_spy) to xxx_spy.count() in a file."""
    content = file_path.read_text()
    original_content = content
    
    # Pattern to match len(something_spy) where something_spy is likely a QSignalSpy
    pattern = r'len\(([a-zA-Z_][a-zA-Z0-9_]*_spy)\)'
    replacement = r'\1.count()'
    
    # Replace all occurrences
    modified_content = re.sub(pattern, replacement, content)
    
    if modified_content != original_content:
        file_path.write_text(modified_content)
        return True
    return False

def main():
    """Find and fix all QSignalSpy len() issues in test files."""
    test_dir = Path("/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master/spritepal/tests")
    
    fixed_files = []
    
    # Find all Python test files
    for file_path in test_dir.rglob("*.py"):
        if fix_qsignalspy_len(file_path):
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