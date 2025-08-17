#!/usr/bin/env python3
"""Fix type errors in migration_adapter.py by adding type: ignore comments."""

import re
from pathlib import Path

def fix_migration_adapter():
    """Add type: ignore comments to lines with QObject attribute access."""
    file_path = Path("ui/components/base/composed/migration_adapter.py")
    
    if not file_path.exists():
        print(f"Error: {file_path} not found")
        return
    
    content = file_path.read_text()
    
    # Patterns to fix - add type: ignore to these specific lines
    patterns_to_fix = [
        (r'(\s+insert_index = self\.main_layout\.indexOf\(button_manager\.button_box\))',
         r'\1  # type: ignore[attr-defined]'),
        (r'(\s+self\.status_bar = status_manager\.status_bar)',
         r'\1  # type: ignore[attr-defined]'),
        (r'(\s+self\.button_box = button_manager\.button_box)',
         r'\1  # type: ignore[attr-defined]'),
        (r'(\s+button_manager\.add_button\()',
         r'\1  # type: ignore[attr-defined]'),
        (r'(\s+status_manager\.update_status\(message\))',
         r'\1  # type: ignore[attr-defined]'),
        (r'(\s+return error_handler\.show_error\()',
         r'\1  # type: ignore[attr-defined]'),
        (r'(\s+return info_handler\.show_info\()',
         r'\1  # type: ignore[attr-defined]'),
        (r'(\s+return warning_handler\.show_warning\()',
         r'\1  # type: ignore[attr-defined]'),
        (r'(\s+return confirmation_handler\.confirm_action\()',
         r'\1  # type: ignore[attr-defined]'),
    ]
    
    changes_made = 0
    for pattern, replacement in patterns_to_fix:
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            content = new_content
            changes_made += count
            print(f"Fixed: {pattern[:50]}... ({count} occurrences)")
    
    if changes_made > 0:
        file_path.write_text(content)
        print(f"\nTotal changes made: {changes_made}")
    else:
        print("No changes needed")

if __name__ == "__main__":
    fix_migration_adapter()