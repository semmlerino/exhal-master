#!/usr/bin/env python3
"""Fix all remaining type errors in row_arrangement_dialog.py."""

import re
from pathlib import Path

def fix_row_arrangement():
    """Fix all None-check issues in row_arrangement_dialog.py."""
    filepath = Path("ui/row_arrangement_dialog.py")
    content = filepath.read_text()
    
    # Fix sprite_path None check at line 95
    content = re.sub(
        r'(\s+)self\.original_image, self\.tile_rows = \(\s*\n\s+self\.image_processor\.process_sprite_sheet\(\s*\n\s+self\.sprite_path, self\.tiles_per_row\s*\n\s+\)\s*\n\s+\)',
        r'\1if self.sprite_path:\n\1    self.original_image, self.tile_rows = (\n\1        self.image_processor.process_sprite_sheet(\n\1            self.sprite_path, self.tiles_per_row\n\1        )\n\1    )',
        content,
        flags=re.MULTILINE
    )
    
    # Fix line 252: self.available_list.setItemWidget
    content = re.sub(
        r'(\s+)self\.available_list\.setItemWidget\(item, thumbnail\)',
        r'\1if self.available_list:\n\1    self.available_list.setItemWidget(item, thumbnail)',
        content
    )
    
    # Fix line 280: self.arranged_list.setItemWidget
    content = re.sub(
        r'(\s+)self\.arranged_list\.setItemWidget\(item, widget\)',
        r'\1if self.arranged_list:\n\1    self.arranged_list.setItemWidget(item, widget)',
        content
    )
    
    # Fix selectedItems() calls - lines 332, 343
    content = re.sub(
        r'selected_items = self\.available_list\.selectedItems\(\)',
        r'selected_items = self.available_list.selectedItems() if self.available_list else []',
        content
    )
    
    content = re.sub(
        r'selected_items = self\.arranged_list\.selectedItems\(\)',
        r'selected_items = self.arranged_list.selectedItems() if self.arranged_list else []',
        content
    )
    
    # Fix loop iterations over None lists
    content = re.sub(
        r'(\s+)for i in range\(self\.available_list\.count\(\)\):',
        r'\1if self.available_list:\n\1    for i in range(self.available_list.count()):',
        content
    )
    
    content = re.sub(
        r'(\s+)for i in range\(self\.arranged_list\.count\(\)\):',
        r'\1if self.arranged_list:\n\1    for i in range(self.arranged_list.count()):',
        content
    )
    
    # Fix the indentation of the loop bodies
    # This is tricky - need to indent everything inside the loop
    lines = content.split('\n')
    new_lines = []
    in_fixed_loop = False
    indent_level = 0
    
    for i, line in enumerate(lines):
        if 'if self.available_list:' in line and i + 1 < len(lines) and 'for i in range' in lines[i + 1]:
            new_lines.append(line)
            in_fixed_loop = True
            indent_level = len(line) - len(line.lstrip())
        elif 'if self.arranged_list:' in line and i + 1 < len(lines) and 'for i in range' in lines[i + 1]:
            new_lines.append(line)
            in_fixed_loop = True
            indent_level = len(line) - len(line.lstrip())
        elif in_fixed_loop:
            # Check if we're still in the loop body
            current_indent = len(line) - len(line.lstrip())
            if line.strip() and current_indent <= indent_level + 4:
                # End of loop body
                in_fixed_loop = False
                new_lines.append(line)
            else:
                # Add extra indentation for being inside the if block
                if line.strip():
                    new_lines.append('    ' + line)
                else:
                    new_lines.append(line)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    # Fix RowPreviewWidget constructor calls with None image
    content = re.sub(
        r'(\s+)thumbnail = RowPreviewWidget\(\s*\n(\s+)row_index,\s*\n(\s+)display_image,',
        r'\1if display_image:\n\1    thumbnail = RowPreviewWidget(\n\2    row_index,\n\3    display_image,',
        content,
        flags=re.MULTILINE
    )
    
    # Fix Path(self.output_path) with None
    content = re.sub(
        r'Path\(self\.output_path\)\.stem',
        r'Path(self.output_path).stem if self.output_path else "untitled"',
        content
    )
    
    # Write back
    filepath.write_text(content)
    print("Fixed row_arrangement_dialog.py")

if __name__ == "__main__":
    fix_row_arrangement()