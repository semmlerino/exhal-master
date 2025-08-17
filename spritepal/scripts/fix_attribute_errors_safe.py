#!/usr/bin/env python3
"""Fix common attribute access issues automatically.

This script addresses the 131 reportAttributeAccessIssue errors found by basedpyright.
It handles:
1. Qt enum access patterns (PySide6 compatibility)
2. Import path corrections
3. Adding type: ignore comments where appropriate
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Set

# Qt Enum fixes - PySide6 uses different enum access patterns
QT_ENUM_REPLACEMENTS = [
    # Qt ItemDataRole enums
    (r'\bQt\.DisplayRole\b', 'Qt.ItemDataRole.DisplayRole'),
    (r'\bQt\.EditRole\b', 'Qt.ItemDataRole.EditRole'),
    (r'\bQt\.DecorationRole\b', 'Qt.ItemDataRole.DecorationRole'),
    (r'\bQt\.UserRole\b', 'Qt.ItemDataRole.UserRole'),
    
    # QDialog result codes
    (r'\bQDialog\.Accepted\b', 'QDialog.DialogCode.Accepted'),
    (r'\bQDialog\.Rejected\b', 'QDialog.DialogCode.Rejected'),
    
    # Qt ScrollBarPolicy
    (r'\bQt\.ScrollPerPixel\b', 'Qt.ScrollBarPolicy.ScrollPerPixel'),
    (r'\bQt\.ScrollPerItem\b', 'Qt.ScrollBarPolicy.ScrollPerItem'),
    
    # Qt ItemFlags
    (r'\bQt\.ItemIsEnabled\b', 'Qt.ItemFlag.ItemIsEnabled'),
    (r'\bQt\.ItemIsSelectable\b', 'Qt.ItemFlag.ItemIsSelectable'),
    (r'\bQt\.ItemIsEditable\b', 'Qt.ItemFlag.ItemIsEditable'),
    (r'\bQt\.NoItemFlags\b', 'Qt.ItemFlag.NoItemFlags'),
    
    # Qt Mouse buttons
    (r'\bQt\.LeftButton\b', 'Qt.MouseButton.LeftButton'),
    (r'\bQt\.RightButton\b', 'Qt.MouseButton.RightButton'),
    (r'\bQt\.MiddleButton\b', 'Qt.MouseButton.MiddleButton'),
    
    # Qt Transformations
    (r'\bQt\.SmoothTransformation\b', 'Qt.TransformationMode.SmoothTransformation'),
    (r'\bQt\.FastTransformation\b', 'Qt.TransformationMode.FastTransformation'),
    
    # QStyle State flags
    (r'\bQStyle\.State_MouseOver\b', 'QStyle.StateFlag.State_MouseOver'),
    (r'\bQStyle\.State_Selected\b', 'QStyle.StateFlag.State_Selected'),
    
    # Qt Alignment
    (r'\bQt\.AlignCenter\b', 'Qt.AlignmentFlag.AlignCenter'),
    (r'\bQt\.AlignLeft\b', 'Qt.AlignmentFlag.AlignLeft'),
    (r'\bQt\.AlignRight\b', 'Qt.AlignmentFlag.AlignRight'),
    
    # Qt Application attributes
    (r'\bQt\.AA_DisableWindowContextHelpButton\b', 
     'Qt.ApplicationAttribute.AA_DisableWindowContextHelpButton'),
    
    # Qt AspectRatioMode
    (r'\bQt\.KeepAspectRatio\b', 'Qt.AspectRatioMode.KeepAspectRatio'),
    
    # Qt Selection behaviors
    (r'\bQt\.NoSelection\b', 'Qt.SelectionMode.NoSelection'),
    
    # QListView modes
    (r'\bQListView\.IconMode\b', 'QListView.ViewMode.IconMode'),
    (r'\bQListView\.ListMode\b', 'QListView.ViewMode.ListMode'),
    (r'\bQListView\.Batched\b', 'QListView.LayoutMode.Batched'),
    (r'\bQListView\.Adjust\b', 'QListView.ResizeMode.Adjust'),
]

def fix_qt_enums(content: str) -> Tuple[str, int]:
    """Fix Qt enum access patterns for PySide6 compatibility.
    
    Returns:
        Tuple of (modified content, number of replacements made)
    """
    total_replacements = 0
    
    for pattern, replacement in QT_ENUM_REPLACEMENTS:
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            total_replacements += count
            content = new_content
    
    return content, total_replacements

def add_type_ignores_for_tests(content: str, file_path: Path) -> Tuple[str, int]:
    """Add type: ignore comments for known test infrastructure issues.
    
    Only applies to test files.
    
    Returns:
        Tuple of (modified content, number of replacements made)
    """
    if not ('test' in file_path.name or 'test' in str(file_path.parent)):
        return content, 0
    
    replacements = 0
    lines = content.split('\n')
    modified_lines = []
    
    patterns_to_ignore = [
        'test_results',
        'qt_tracker',
        'take_memory_snapshot',
        'MEMORY_LIMIT_MB',
    ]
    
    for line in lines:
        modified_line = line
        for pattern in patterns_to_ignore:
            if pattern in line and '# type: ignore' not in line:
                # Add type: ignore at the end of the line
                modified_line = line.rstrip() + '  # type: ignore[attr-defined]'
                replacements += 1
                break
        modified_lines.append(modified_line)
    
    return '\n'.join(modified_lines), replacements

def process_file(file_path: Path, dry_run: bool = False) -> bool:
    """Process a single Python file to fix attribute errors.
    
    Args:
        file_path: Path to the Python file
        dry_run: If True, only report what would be changed without modifying
        
    Returns:
        True if file was modified (or would be in dry_run)
    """
    # Skip the fix scripts themselves
    if file_path.name.startswith('fix_attribute_errors'):
        return False
        
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        total_changes = 0
        
        # Apply Qt enum fixes
        content, enum_changes = fix_qt_enums(content)
        total_changes += enum_changes
        
        # Apply type: ignore for test files
        content, ignore_changes = add_type_ignores_for_tests(content, file_path)
        total_changes += ignore_changes
        
        if content != original_content:
            if dry_run:
                print(f"Would modify: {file_path} ({total_changes} changes)")
                if enum_changes:
                    print(f"  - Qt enum fixes: {enum_changes}")
                if ignore_changes:
                    print(f"  - Type ignore additions: {ignore_changes}")
            else:
                file_path.write_text(content, encoding='utf-8')
                print(f"Modified: {file_path} ({total_changes} changes)")
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return False

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fix common attribute access issues in Python code'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be changed without modifying files'
    )
    parser.add_argument(
        '--path',
        type=Path,
        default=Path('.'),
        help='Path to process (default: current directory)'
    )
    parser.add_argument(
        '--specific-files',
        nargs='+',
        type=Path,
        help='Process only these specific files'
    )
    
    args = parser.parse_args()
    
    # Determine which files to process
    if args.specific_files:
        files_to_process = args.specific_files
    else:
        # Find all Python files, excluding virtual environments
        files_to_process = []
        for pattern in ['**/*.py']:
            for file_path in args.path.glob(pattern):
                # Skip virtual environment directories and test venvs
                if any(part in ['.venv', 'venv', '__pycache__', '.venv_temp', 'venv_temp'] 
                       for part in file_path.parts):
                    continue
                # Also skip if path contains /venv/ anywhere
                if '/venv/' in str(file_path) or '\\venv\\' in str(file_path):
                    continue
                files_to_process.append(file_path)
    
    # Process files
    modified_count = 0
    total_files = len(files_to_process)
    
    print(f"Processing {total_files} Python files...")
    if args.dry_run:
        print("DRY RUN MODE - No files will be modified\n")
    
    for file_path in sorted(files_to_process):
        if process_file(file_path, dry_run=args.dry_run):
            modified_count += 1
    
    # Summary
    print(f"\nSummary:")
    print(f"  Files scanned: {total_files}")
    if args.dry_run:
        print(f"  Files that would be modified: {modified_count}")
        print("\nRun without --dry-run to apply changes.")
    else:
        print(f"  Files modified: {modified_count}")
        print("\nRun 'basedpyright .' to verify fixes.")

if __name__ == '__main__':
    main()