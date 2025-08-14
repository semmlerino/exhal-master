#!/usr/bin/env python3
"""
Script to fix common linting issues systematically.
"""

import re
import sys
from pathlib import Path


def fix_pathlib_usage(content: str) -> str:
    """Replace os.path functions with pathlib equivalents."""
    replacements = [
        # os.path.exists(x) -> Path(x).exists()
        (r'os\.path\.exists\(([^)]+)\)', r'Path(\1).exists()'),
        # os.path.join(a, b) -> Path(a) / b  (simple cases)
        (r'os\.path\.join\(([^,]+),\s*([^)]+)\)', r'(Path(\1) / \2)'),
        # os.path.dirname(x) -> Path(x).parent
        (r'os\.path\.dirname\(([^)]+)\)', r'Path(\1).parent'),
        # os.path.basename(x) -> Path(x).name
        (r'os\.path\.basename\(([^)]+)\)', r'Path(\1).name'),
        # os.path.splitext(x)[0] -> Path(x).stem
        (r'os\.path\.splitext\(([^)]+)\)\[0\]', r'Path(\1).stem'),
        # os.path.splitext(x)[1] -> Path(x).suffix
        (r'os\.path\.splitext\(([^)]+)\)\[1\]', r'Path(\1).suffix'),
    ]
    
    modified = content
    for pattern, replacement in replacements:
        modified = re.sub(pattern, replacement, modified)
    
    # Add Path import if needed and not present
    if 'Path(' in modified and 'from pathlib import Path' not in modified:
        # Add after other imports
        lines = modified.split('\n')
        import_added = False
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                # Find the last import line
                continue
            elif not import_added and i > 0:
                # Insert Path import after imports
                lines.insert(i, 'from pathlib import Path')
                import_added = True
                break
        modified = '\n'.join(lines)
    
    return modified


def fix_collapsible_ifs(content: str) -> str:
    """Combine collapsible if statements."""
    # This is complex to do reliably with regex, skip for now
    return content


def remove_unused_imports(content: str) -> str:
    """Remove clearly unused imports."""
    lines = content.split('\n')
    result = []
    
    # Track what's actually used in the file
    # This is a simplified check - not perfect but safe for obvious cases
    code_section = '\n'.join(line for line in lines if not line.strip().startswith(('import ', 'from ')))
    
    for line in lines:
        # Skip clearly unused typing imports
        if 'from typing import' in line:
            # Extract imported names
            match = re.search(r'from typing import (.+)', line)
            if match:
                imports = match.group(1)
                # Check each import
                import_list = [imp.strip() for imp in imports.split(',')]
                used_imports = []
                for imp in import_list:
                    # Clean up the import name
                    imp_name = imp.split(' as ')[0].strip()
                    # Check if it's used (simple check)
                    if imp_name in code_section:
                        used_imports.append(imp)
                
                if used_imports:
                    line = f"from typing import {', '.join(used_imports)}"
                else:
                    continue  # Skip this line entirely
        
        result.append(line)
    
    return '\n'.join(result)


def fix_file(file_path: Path) -> bool:
    """Fix linting issues in a single file."""
    try:
        content = file_path.read_text()
        original = content
        
        # Apply fixes
        content = fix_pathlib_usage(content)
        # content = fix_collapsible_ifs(content)  # Too complex for simple regex
        # content = remove_unused_imports(content)  # Too risky
        
        if content != original:
            file_path.write_text(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main entry point."""
    # Get all Python files
    base_dir = Path('/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master/spritepal')
    python_files = list(base_dir.rglob('*.py'))
    
    # Skip test files and this script
    python_files = [
        f for f in python_files 
        if 'test' not in f.name.lower() 
        and f.name != 'fix_linting_issues.py'
        and '__pycache__' not in str(f)
    ]
    
    fixed_count = 0
    for file_path in python_files[:10]:  # Start with just 10 files
        if fix_file(file_path):
            fixed_count += 1
            print(f"Fixed: {file_path.relative_to(base_dir)}")
    
    print(f"\nFixed {fixed_count} files")


if __name__ == '__main__':
    main()