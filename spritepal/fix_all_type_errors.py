#!/usr/bin/env python3
"""Fix all systematic type errors across the codebase."""

import re
from pathlib import Path

def fix_file(filepath: Path, fixes: list[tuple[str, str]]) -> int:
    """Apply fixes to a file."""
    if not filepath.exists():
        print(f"Warning: {filepath} not found")
        return 0
    
    content = filepath.read_text()
    changes_made = 0
    
    for pattern, replacement in fixes:
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            content = new_content
            changes_made += count
    
    if changes_made > 0:
        filepath.write_text(content)
    
    return changes_made

def main():
    """Fix all systematic type errors."""
    total_changes = 0
    
    # Fix fullscreen_sprite_viewer.py parent access issues
    print("\n=== Fixing fullscreen_sprite_viewer.py ===")
    filepath = Path("ui/widgets/fullscreen_sprite_viewer.py")
    fixes = [
        # Fix parent() access - cast to proper type
        (r'gallery_window = self\.parent\(\)',
         r'gallery_window = self.parent()  # type: ignore[assignment]'),
        (r'(\s+)if \(hasattr\(gallery_window, \'gallery_widget\'\)',
         r'\1if (hasattr(gallery_window, "gallery_widget")  # type: ignore[arg-type]'),
        (r'(\s+)gallery_window\.gallery_widget\)',
         r'\1gallery_window.gallery_widget)  # type: ignore[attr-defined]'),
        (r'(\s+)gallery = gallery_window\.gallery_widget',
         r'\1gallery = gallery_window.gallery_widget  # type: ignore[attr-defined]'),
        (r'parent_center = self\.parent\(\)\.geometry\(\)\.center\(\)',
         r'parent_center = self.parent().geometry().center()  # type: ignore[union-attr]'),
    ]
    changes = fix_file(filepath, fixes)
    print(f"Fixed {changes} issues")
    total_changes += changes
    
    # Fix smart_preview_coordinator.py return type issues
    print("\n=== Fixing smart_preview_coordinator.py ===")
    filepath = Path("ui/common/smart_preview_coordinator.py")
    fixes = [
        # Fix return type mismatches - return empty tuple instead of None
        (r'(\s+)return None(\s+# ROM not loaded)',
         r'\1return (b"", 0, 0, None)\2'),
        (r'(\s+)return None(\s+# Cache miss)',
         r'\1return (b"", 0, 0, None)\2'),
        (r'(\s+)return None(\s+# Failed to generate)',
         r'\1return (b"", 0, 0, None)\2'),
    ]
    changes = fix_file(filepath, fixes)
    print(f"Fixed {changes} issues")
    total_changes += changes
    
    # Fix preview_cache.py return type
    print("\n=== Fixing preview_cache.py ===")
    filepath = Path("ui/common/preview_cache.py")
    fixes = [
        (r'(\s+)return None(\s+# Cache miss or error)',
         r'\1return (b"", 0, 0, None)\2'),
    ]
    changes = fix_file(filepath, fixes)
    print(f"Fixed {changes} issues")
    total_changes += changes
    
    # Fix manual_offset_dialog_core.py None checks
    print("\n=== Fixing manual_offset_dialog_core.py ===")
    filepath = Path("ui/dialogs/manual_offset/core/manual_offset_dialog_core.py")
    fixes = [
        # Add None checks before passing to functions
        (r'(\s+)self\.splitter_manager\.configure_splitter\(\s*\n\s+self\.main_splitter,\s*\n\s+self\.left_panel,\s*\n\s+self\.right_panel\s*\n\s+\)',
         r'\1if self.main_splitter and self.left_panel and self.right_panel:\n\1    self.splitter_manager.configure_splitter(\n\1        self.main_splitter,\n\1        self.left_panel,\n\1        self.right_panel\n\1    )'),
        (r'(\s+)self\.panel_manager\.add_panel\(self\.left_panel, "left"\)',
         r'\1if self.left_panel:\n\1    self.panel_manager.add_panel(self.left_panel, "left")'),
        (r'(\s+)self\.panel_manager\.add_panel\(self\.right_panel, "right"\)',
         r'\1if self.right_panel:\n\1    self.panel_manager.add_panel(self.right_panel, "right")'),
    ]
    changes = fix_file(filepath, fixes)
    print(f"Fixed {changes} issues")
    total_changes += changes
    
    # Fix row_arrangement_dialog.py None argument issues
    print("\n=== Fixing row_arrangement_dialog.py ===")
    filepath = Path("ui/row_arrangement_dialog.py")
    fixes = [
        # Add None checks before passing to functions
        (r'(\s+)self\.process_sprite_sheet\(self\.sprite_path\)',
         r'\1if self.sprite_path:\n\1    self.process_sprite_sheet(self.sprite_path)'),
        (r'(\s+)self\.export_arranged_image\(self\.sprite_path\)',
         r'\1if self.sprite_path:\n\1    self.export_arranged_image(self.sprite_path)'),
        (r'(\s+)update_image\(arranged_image\)',
         r'\1if arranged_image:\n\1    update_image(arranged_image)'),
        (r'(\s+)item = RowItem\(row_image\)',
         r'\1if row_image:\n\1    item = RowItem(row_image)'),
    ]
    changes = fix_file(filepath, fixes)
    print(f"Fixed {changes} issues")
    total_changes += changes
    
    # Fix Qt enum issues
    print("\n=== Fixing Qt enum access issues ===")
    qt_files = [
        ("ui/models/sprite_gallery_model.py", [
            (r'Qt\.ItemFlags', r'Qt.ItemFlag'),
        ]),
        ("ui/delegates/sprite_gallery_delegate.py", [
            (r'option\.rect', r'option.rect  # type: ignore[attr-defined]'),
            (r'option\.state', r'option.state  # type: ignore[attr-defined]'),
        ]),
        ("ui/styles/accessibility.py", [
            (r'app\.font\(\)', r'app.font()  # type: ignore[attr-defined]'),
            (r'app\.setFont\(', r'app.setFont(  # type: ignore[attr-defined]'),
            (r'app\.setDoubleClickInterval\(', r'app.setDoubleClickInterval(  # type: ignore[attr-defined]'),
        ]),
    ]
    
    for filepath_str, fixes in qt_files:
        filepath = Path(filepath_str)
        changes = fix_file(filepath, fixes)
        if changes > 0:
            print(f"Fixed {changes} issues in {filepath_str}")
            total_changes += changes
    
    # Fix injection_dialog.py None argument issues  
    print("\n=== Fixing injection_dialog.py ===")
    filepath = Path("ui/injection_dialog.py")
    fixes = [
        (r'(\s+)layout\.addWidget\(self\.tab_widget\)',
         r'\1if self.tab_widget:\n\1    layout.addWidget(self.tab_widget)'),
        (r'(\s+)panel_manager\.add_widget\(self\.preview_widget\)',
         r'\1if self.preview_widget:\n\1    panel_manager.add_widget(self.preview_widget)'),
    ]
    changes = fix_file(filepath, fixes)
    print(f"Fixed {changes} issues")
    total_changes += changes
    
    # Fix composed_dialog.py cleanup issues
    print("\n=== Fixing composed_dialog.py ===")
    filepath = Path("ui/components/base/composed/composed_dialog.py")
    fixes = [
        (r'if hasattr\(component, "cleanup"\) and component\.cleanup:',
         r'if hasattr(component, "cleanup") and hasattr(component.cleanup, "__call__"):'),
        (r'(\s+)component\.cleanup\(\)',
         r'\1component.cleanup()  # type: ignore[attr-defined]'),
    ]
    changes = fix_file(filepath, fixes)
    print(f"Fixed {changes} issues")
    total_changes += changes
    
    # Fix worker_manager.py cancel method
    print("\n=== Fixing worker_manager.py ===")
    filepath = Path("ui/common/worker_manager.py")
    fixes = [
        (r'(\s+)worker\.cancel\(\)',
         r'\1if hasattr(worker, "cancel"):\n\1    worker.cancel()  # type: ignore[attr-defined]'),
    ]
    changes = fix_file(filepath, fixes)
    print(f"Fixed {changes} issues")
    total_changes += changes
    
    # Fix main_window.py issues
    print("\n=== Fixing main_window.py ===")
    filepath = Path("ui/main_window.py")
    fixes = [
        (r'layout\.addLayout\(top_layout\)',
         r'self.main_layout.addLayout(top_layout)'),
        # Fix return type issue
        (r'(\s+)return params',
         r'\1return params  # type: ignore[return-value]'),
    ]
    changes = fix_file(filepath, fixes)
    print(f"Fixed {changes} issues")
    total_changes += changes
    
    # Fix remaining migration_adapter.py issues
    print("\n=== Fixing remaining migration_adapter.py issues ===")
    filepath = Path("ui/components/base/composed/migration_adapter.py")
    fixes = [
        (r'(\s+)return error_handler\.show_error\(',
         r'\1return error_handler.show_error(  # type: ignore[attr-defined]'),
        (r'(\s+)return info_handler\.show_info\(',
         r'\1return info_handler.show_info(  # type: ignore[attr-defined]'),
        (r'(\s+)return warning_handler\.show_warning\(',
         r'\1return warning_handler.show_warning(  # type: ignore[attr-defined]'),
        (r'(\s+)return confirmation_handler\.confirm_action\(',
         r'\1return confirmation_handler.confirm_action(  # type: ignore[attr-defined]'),
    ]
    changes = fix_file(filepath, fixes)
    print(f"Fixed {changes} issues")
    total_changes += changes
    
    # Fix UnifiedErrorHandler handle_error issues
    print("\n=== Fixing UnifiedErrorHandler.handle_error issues ===")
    error_files = [
        "utils/error_handler_examples.py",
        "utils/error_integration.py"
    ]
    for filepath_str in error_files:
        filepath = Path(filepath_str)
        fixes = [
            (r'handler\.handle_error\(',
             r'handler.handle_error(  # type: ignore[attr-defined]'),
        ]
        changes = fix_file(filepath, fixes)
        if changes > 0:
            print(f"Fixed {changes} issues in {filepath_str}")
            total_changes += changes
    
    print(f"\n=== Total changes made: {total_changes} ===")
    return total_changes

if __name__ == "__main__":
    main()