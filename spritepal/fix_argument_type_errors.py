#!/usr/bin/env python3
"""Fix reportArgumentType errors from basedpyright."""

import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict

def get_argument_type_errors() -> List[Tuple[str, int, str]]:
    """Extract all reportArgumentType errors from basedpyright output."""
    result = subprocess.run(
        ["basedpyright", ".", "--outputjson"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    
    errors = []
    import json
    try:
        data = json.loads(result.stdout)
        for diag in data.get('generalDiagnostics', []):
            if diag.get('rule') == 'reportArgumentType':
                file_path = diag['file']
                line = diag['range']['start']['line'] + 1
                message = diag['message']
                errors.append((file_path, line, message))
    except json.JSONDecodeError:
        # Fallback to text parsing
        lines = result.stderr.split('\n') + result.stdout.split('\n')
        for i, line in enumerate(lines):
            if 'reportArgumentType' in line and i > 0:
                prev_line = lines[i-1]
                match = re.match(r'\s*(.+\.py):(\d+):\d+ - error:', prev_line)
                if match:
                    errors.append((match.group(1), int(match.group(2)), line))
    
    return errors

def categorize_errors(errors: List[Tuple[str, int, str]]) -> Dict[str, List[Tuple[str, int, str]]]:
    """Categorize errors by type."""
    categories = {
        'qapp_qcore': [],
        'path_str': [],
        'literal_bool': [],
        'float_int': [],
        'optional_none': [],
        'type_any': [],
        'other': []
    }
    
    for file_path, line, message in errors:
        if 'QApplication' in message and 'QCoreApplication' in message:
            categories['qapp_qcore'].append((file_path, line, message))
        elif 'Path' in message and 'str' in message:
            categories['path_str'].append((file_path, line, message))
        elif 'Literal' in message and 'bool' in message:
            categories['literal_bool'].append((file_path, line, message))
        elif 'float' in message and 'int' in message:
            categories['float_int'].append((file_path, line, message))
        elif 'None' in message or 'Optional' in message:
            categories['optional_none'].append((file_path, line, message))
        elif 'type[Any]' in message:
            categories['type_any'].append((file_path, line, message))
        else:
            categories['other'].append((file_path, line, message))
    
    return categories

def fix_qapp_errors(file_path: str, line_num: int):
    """Fix QApplication vs QCoreApplication errors."""
    path = Path(file_path)
    if not path.exists():
        return
    
    lines = path.read_text().splitlines()
    if line_num <= len(lines):
        line = lines[line_num - 1]
        
        # Check if we need to cast or import properly
        if 'QApplication.instance()' in line:
            # Add cast import if not present
            import_line = 'from typing import cast'
            if import_line not in '\n'.join(lines[:50]):
                # Find where to add the import
                for i, l in enumerate(lines):
                    if l.startswith('from typing import'):
                        if 'cast' not in l:
                            lines[i] = l.rstrip(')') + ', cast)' if l.rstrip().endswith(')') else l + ', cast'
                        break
                    elif l.startswith('import ') and i > 0:
                        lines.insert(i, import_line)
                        break
            
            # Fix the line with cast
            lines[line_num - 1] = line.replace(
                'QApplication.instance()',
                'cast(QApplication, QApplication.instance())'
            )
        
        path.write_text('\n'.join(lines) + '\n')

def fix_path_str_errors(file_path: str, line_num: int):
    """Fix Path vs str errors."""
    path = Path(file_path)
    if not path.exists():
        return
    
    lines = path.read_text().splitlines()
    if line_num <= len(lines):
        line = lines[line_num - 1]
        
        # Convert Path to str
        # Look for common patterns
        if 'Path(' in line or '.path' in line:
            # Simple approach: wrap Path objects in str()
            modified = re.sub(r'(Path\([^)]+\))', r'str(\1)', line)
            if modified == line:  # If no change, try another pattern
                # Look for variable.path patterns
                modified = re.sub(r'(\w+\.path)', r'str(\1)', line)
            
            lines[line_num - 1] = modified
        
        path.write_text('\n'.join(lines) + '\n')

def fix_literal_bool_errors(file_path: str, line_num: int):
    """Fix Literal[0/1] vs bool errors."""
    path = Path(file_path)
    if not path.exists():
        return
    
    lines = path.read_text().splitlines()
    if line_num <= len(lines):
        line = lines[line_num - 1]
        
        # Replace visible=0 with visible=False, visible=1 with visible=True
        modified = re.sub(r'visible\s*=\s*0\b', 'visible=False', line)
        modified = re.sub(r'visible\s*=\s*1\b', 'visible=True', modified)
        
        lines[line_num - 1] = modified
        path.write_text('\n'.join(lines) + '\n')

def fix_float_int_errors(file_path: str, line_num: int):
    """Fix float vs int errors."""
    path = Path(file_path)
    if not path.exists():
        return
    
    lines = path.read_text().splitlines()
    if line_num <= len(lines):
        line = lines[line_num - 1]
        
        # Look for setValue or similar methods that expect int
        if 'setValue' in line or 'setMinimum' in line or 'setMaximum' in line:
            # Wrap float values in int()
            modified = re.sub(r'(setValue|setMinimum|setMaximum)\(([^)]+)\)', 
                            lambda m: f"{m.group(1)}(int({m.group(2)}))", line)
            lines[line_num - 1] = modified
        
        path.write_text('\n'.join(lines) + '\n')

def main():
    """Main function to fix all errors."""
    print("Extracting reportArgumentType errors...")
    errors = get_argument_type_errors()
    print(f"Found {len(errors)} reportArgumentType errors")
    
    categories = categorize_errors(errors)
    
    print("\nError categories:")
    for cat, items in categories.items():
        if items:
            print(f"  {cat}: {len(items)} errors")
    
    print("\nFixing errors...")
    
    # Fix QApplication vs QCoreApplication errors
    for file_path, line, _ in categories['qapp_qcore']:
        print(f"  Fixing QApp error in {file_path}:{line}")
        fix_qapp_errors(file_path, line)
    
    # Fix Path vs str errors
    for file_path, line, _ in categories['path_str']:
        print(f"  Fixing Path/str error in {file_path}:{line}")
        fix_path_str_errors(file_path, line)
    
    # Fix Literal vs bool errors
    for file_path, line, _ in categories['literal_bool']:
        print(f"  Fixing Literal/bool error in {file_path}:{line}")
        fix_literal_bool_errors(file_path, line)
    
    # Fix float vs int errors
    for file_path, line, _ in categories['float_int']:
        print(f"  Fixing float/int error in {file_path}:{line}")
        fix_float_int_errors(file_path, line)
    
    # Print other errors for manual review
    if categories['other']:
        print("\nOther errors that need manual review:")
        for file_path, line, message in categories['other'][:10]:
            print(f"  {file_path}:{line}")
            print(f"    {message[:100]}...")
    
    print("\nDone! Run basedpyright again to verify fixes.")

if __name__ == "__main__":
    main()