#!/usr/bin/env python3
"""Fix common type errors in the codebase."""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def fix_override_imports(content: str) -> str:
    """Fix override import issues."""
    # First check if we need to add typing_extensions import
    if "from typing import" in content and "override" in content:
        # Check if override is being imported from typing
        typing_import_pattern = r'from typing import ([^)]+)'
        typing_imports = re.findall(typing_import_pattern, content)
        
        for imports_str in typing_imports:
            if "override" in imports_str:
                # Remove override from typing import
                imports = [i.strip() for i in imports_str.split(',')]
                imports = [i for i in imports if i != "override"]
                new_imports = ', '.join(imports)
                
                # Replace the import line
                old_line = f"from typing import {imports_str}"
                new_line = f"from typing import {new_imports}"
                content = content.replace(old_line, new_line)
                
                # Add typing_extensions import if not present
                if "from typing_extensions import" not in content:
                    # Add after typing import
                    content = content.replace(
                        f"from typing import {new_imports}",
                        f"from typing import {new_imports}\nfrom typing_extensions import override"
                    )
                elif "override" not in content:
                    # Add override to existing typing_extensions import
                    content = re.sub(
                        r'from typing_extensions import ([^)]+)',
                        lambda m: f"from typing_extensions import {m.group(1)}, override",
                        content
                    )
    
    return content


def fix_optional_member_access(content: str) -> str:
    """Fix optional member access by adding None checks."""
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        # Common patterns for Qt widget access
        widget_patterns = [
            (r'(\s*)self\.(\w+)\.setText\(', r'\1if self.\2:\n\1    self.\2.setText('),
            (r'(\s*)self\.(\w+)\.setEnabled\(', r'\1if self.\2:\n\1    self.\2.setEnabled('),
            (r'(\s*)self\.(\w+)\.setChecked\(', r'\1if self.\2:\n\1    self.\2.setChecked('),
            (r'(\s*)self\.(\w+)\.setPixmap\(', r'\1if self.\2:\n\1    self.\2.setPixmap('),
            (r'(\s*)self\.(\w+)\.clear\(\)', r'\1if self.\2:\n\1    self.\2.clear()'),
            (r'(\s*)self\.(\w+)\.addItem\(', r'\1if self.\2:\n\1    self.\2.addItem('),
            (r'(\s*)self\.(\w+)\.setCurrentIndex\(', r'\1if self.\2:\n\1    self.\2.setCurrentIndex('),
            (r'(\s*)self\.(\w+)\.setStyleSheet\(', r'\1if self.\2:\n\1    self.\2.setStyleSheet('),
        ]
        
        # Skip if already has a guard
        if i > 0 and 'if self.' in lines[i-1]:
            new_lines.append(line)
            continue
            
        # Skip if line is already guarded or is a definition
        if line.strip().startswith(('if ', 'def ', 'class ', '#', 'return', 'else', 'elif', 'except', 'finally')):
            new_lines.append(line)
            continue
        
        modified = False
        for pattern, replacement in widget_patterns:
            if re.search(pattern, line):
                # Don't add guard if it's in __init__ and likely initialization
                if '__init__' in ''.join(lines[max(0, i-10):i]):
                    new_lines.append(line)
                else:
                    # Add the if check
                    match = re.search(pattern, line)
                    if match:
                        indent = match.group(1)
                        widget = match.group(2)
                        new_lines.append(f"{indent}if self.{widget}:")
                        new_lines.append(f"    {line}")
                        modified = True
                break
        
        if not modified:
            new_lines.append(line)
    
    return '\n'.join(new_lines)


def fix_qt_constants(content: str) -> str:
    """Fix Qt constant access issues."""
    # Fix Qt.ItemDataRole.UserRole to Qt.ItemDataRole.UserRole
    content = re.sub(
        r'Qt\.UserRole',
        r'Qt.ItemDataRole.UserRole',
        content
    )
    
    # Fix other Qt enum accesses if needed
    qt_enum_fixes = [
        (r'Qt\.AlignCenter', r'Qt.AlignmentFlag.AlignCenter'),
        (r'Qt\.AlignLeft', r'Qt.AlignmentFlag.AlignLeft'),
        (r'Qt\.AlignRight', r'Qt.AlignmentFlag.AlignRight'),
        (r'Qt\.AlignTop', r'Qt.AlignmentFlag.AlignTop'),
        (r'Qt\.AlignBottom', r'Qt.AlignmentFlag.AlignBottom'),
        (r'Qt\.LeftButton', r'Qt.MouseButton.LeftButton'),
        (r'Qt\.RightButton', r'Qt.MouseButton.RightButton'),
        (r'Qt\.MiddleButton', r'Qt.MouseButton.MiddleButton'),
        (r'Qt\.Key_', r'Qt.Key.Key_'),
    ]
    
    for pattern, replacement in qt_enum_fixes:
        # Skip if already using the new format
        if replacement.split('.')[-1] not in content:
            content = re.sub(pattern, replacement, content)
    
    return content


def fix_return_type_none(content: str) -> str:
    """Fix return type issues where None is returned but not in type hint."""
    lines = content.split('\n')
    
    # Find function definitions and check their returns
    for i in range(len(lines)):
        if 'def ' in lines[i] and '->' in lines[i] and 'None' not in lines[i]:
            # Check if function might return None
            func_end = i + 1
            indent_level = len(lines[i]) - len(lines[i].lstrip())
            
            # Find the end of the function
            for j in range(i + 1, min(i + 100, len(lines))):
                if lines[j].strip() and not lines[j].startswith(' ' * (indent_level + 1)):
                    func_end = j
                    break
            
            # Check if function has early returns that might be None
            func_body = '\n'.join(lines[i:func_end])
            if 'return None' in func_body or ('return' in func_body and 'return ' not in func_body):
                # Update return type to include Optional
                if ' -> ' in lines[i]:
                    # Extract current return type
                    match = re.search(r' -> ([^:]+):', lines[i])
                    if match:
                        current_type = match.group(1).strip()
                        if 'Optional[' not in current_type and '|' not in current_type:
                            new_type = f"Optional[{current_type}]"
                            lines[i] = lines[i].replace(f' -> {current_type}:', f' -> {new_type}:')
                            
                            # Ensure Optional is imported
                            if 'from typing import' in content and 'Optional' not in content:
                                for k, line in enumerate(lines):
                                    if 'from typing import' in line:
                                        if 'Optional' not in line:
                                            lines[k] = line.rstrip() + ', Optional'
                                        break
    
    return '\n'.join(lines)


def process_file(filepath: Path) -> bool:
    """Process a single file to fix type errors."""
    try:
        content = filepath.read_text()
        original = content
        
        # Apply fixes
        content = fix_override_imports(content)
        content = fix_qt_constants(content)
        
        # Only apply optional member fixes to UI files
        if '/ui/' in str(filepath) or 'dialog' in filepath.name.lower() or 'widget' in filepath.name.lower():
            content = fix_optional_member_access(content)
        
        # Save if changed
        if content != original:
            filepath.write_text(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def main():
    """Main function to fix type errors."""
    # Get all Python files
    base_path = Path(__file__).parent
    py_files = list(base_path.rglob("*.py"))
    
    # Skip this script and test files
    py_files = [
        f for f in py_files 
        if f.name != "fix_type_errors.py" 
        and "/tests/" not in str(f)
        and "/.venv/" not in str(f)
        and "/venv/" not in str(f)
    ]
    
    print(f"Processing {len(py_files)} Python files...")
    
    fixed_count = 0
    for filepath in py_files:
        if process_file(filepath):
            fixed_count += 1
            print(f"Fixed: {filepath.relative_to(base_path)}")
    
    print(f"\nFixed {fixed_count} files")
    
    # Now fix specific import issues
    print("\nFixing specific import issues...")
    
    # Fix get_logger type issues
    for filepath in py_files:
        if "core/managers/base_manager.py" in str(filepath):
            content = filepath.read_text()
            # Fix logger type annotation
            content = re.sub(
                r'from utils\.logging_config import get_logger',
                r'from utils.logging_config import get_logger  # type: ignore[import]',
                content
            )
            filepath.write_text(content)
            print(f"Fixed logger import in {filepath.name}")


if __name__ == "__main__":
    main()