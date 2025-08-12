#!/usr/bin/env python3
"""
Fix builtin-open (PTH123) issues by replacing open() with Path.open().
"""

import ast
import re
from pathlib import Path
from typing import List, Tuple

def fix_open_in_file(file_path: Path) -> bool:
    """Fix open() calls in a single file."""
    try:
        content = file_path.read_text()
        original_content = content
        
        # Check if pathlib is imported
        has_pathlib_import = (
            'from pathlib import' in content or 
            'import pathlib' in content
        )
        
        # Pattern to match open() calls with file path as first argument
        # This matches: open(something, mode) or open(something)
        open_pattern = r'\bopen\s*\(\s*([^,\)]+?)(?:\s*,\s*["\']([^"\']+)["\']\s*)?\)'
        
        replacements = []
        for match in re.finditer(open_pattern, content):
            file_arg = match.group(1).strip()
            mode = match.group(2) if match.group(2) else 'r'
            
            # Skip if it's already using Path
            if 'Path(' in file_arg or '.open(' in match.group(0):
                continue
                
            # Build replacement
            if mode in ('r', 'rb'):
                # Read mode - default, can be omitted
                if mode == 'r':
                    replacement = f'Path({file_arg}).open()'
                else:
                    replacement = f'Path({file_arg}).open("{mode}")'
            else:
                # Write/append mode - must be specified
                replacement = f'Path({file_arg}).open("{mode}")'
            
            replacements.append((match.group(0), replacement))
        
        # Apply replacements
        for old, new in replacements:
            content = content.replace(old, new)
        
        # Add pathlib import if needed and changes were made
        if replacements and not has_pathlib_import:
            # Find the right place to add import
            lines = content.split('\n')
            import_added = False
            
            for i, line in enumerate(lines):
                # Add after other imports
                if line.startswith('from ') or line.startswith('import '):
                    # Find the last import line
                    j = i
                    while j < len(lines) - 1 and (lines[j+1].startswith('from ') or 
                                                   lines[j+1].startswith('import ')):
                        j += 1
                    # Insert after last import
                    lines.insert(j + 1, 'from pathlib import Path')
                    import_added = True
                    break
            
            if not import_added:
                # Add at the beginning after docstring and comments
                for i, line in enumerate(lines):
                    if line and not line.startswith('#') and not line.startswith('"""'):
                        lines.insert(i, 'from pathlib import Path\n')
                        break
            
            content = '\n'.join(lines)
        
        # Write back if changed
        if content != original_content:
            file_path.write_text(content)
            return True
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to fix builtin-open issues."""
    # Files to fix (from ruff output)
    files_to_fix = [
        'core/extractor.py',
        'core/injector.py',
        'core/managers/extraction_manager.py',
        'core/navigation/caching.py',
        'core/navigation/region_map.py',
        'core/palette_manager.py',
        'core/parallel_sprite_finder.py',
        'core/rom_palette_extractor.py',
        'core/thumbnail_cache.py',
        'test_critical_bug_fixes.py',
        'verify_integration_tests.py',
    ]
    
    fixed_count = 0
    for file_str in files_to_fix:
        file_path = Path(file_str)
        if file_path.exists():
            if fix_open_in_file(file_path):
                print(f"✅ Fixed: {file_str}")
                fixed_count += 1
            else:
                print(f"⏭️  No changes: {file_str}")
        else:
            print(f"❌ Not found: {file_str}")
    
    print(f"\n📊 Fixed {fixed_count} files")
    
    # Run ruff to check remaining issues
    import subprocess
    result = subprocess.run(
        ['../venv/bin/ruff', 'check', '.', '--select=PTH123', '--statistics'],
        capture_output=True,
        text=True
    )
    
    lines = result.stdout.strip().split('\n')
    for line in lines:
        if 'PTH123' in line:
            remaining = line.split()[0]
            print(f"📈 Remaining PTH123 issues: {remaining}")
            break


if __name__ == '__main__':
    main()