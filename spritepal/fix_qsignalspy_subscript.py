#!/usr/bin/env python3
"""Fix QSignalSpy subscript access to be compatible with PySide6."""

import re
from pathlib import Path

def fix_qsignalspy_subscript(file_path: Path) -> bool:
    """Fix QSignalSpy subscript access to use list() conversion."""
    content = file_path.read_text()
    original_content = content
    
    # Find all lines that use spy subscript access
    lines = content.split('\n')
    modified_lines = []
    changed = False
    
    for line in lines:
        # Pattern to match spy[index] where spy is a QSignalSpy variable
        if re.search(r'([a-zA-Z_][a-zA-Z0-9_]*_spy)\[[-\d]+\]', line):
            # Check if this line already has list() conversion
            if 'list(' not in line:
                # Replace spy[index] with list(spy)[index]
                modified_line = re.sub(
                    r'(?<!\blist\()(\b[a-zA-Z_][a-zA-Z0-9_]*_spy)\[',
                    r'list(\1)[',
                    line
                )
                modified_lines.append(modified_line)
                changed = True
            else:
                modified_lines.append(line)
        else:
            modified_lines.append(line)
    
    if changed:
        modified_content = '\n'.join(modified_lines)
        file_path.write_text(modified_content)
        return True
    return False

def main():
    """Find and fix all QSignalSpy subscript issues in test files."""
    test_dir = Path("/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master/spritepal/tests")
    
    fixed_files = []
    
    # Find all Python test files
    for file_path in test_dir.rglob("*.py"):
        if fix_qsignalspy_subscript(file_path):
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