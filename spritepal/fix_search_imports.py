#!/usr/bin/env python3
"""
Script to fix import issues in search feature files.
"""

from pathlib import Path


def fix_imports():
    """Fix all known import issues in search feature files."""

    fixes = [
        # Fix sprite_search_worker.py imports
        {
            "file": "ui/rom_extraction/workers/sprite_search_worker.py",
            "replacements": [
                ("from ui.common.worker_manager import handle_worker_errors",
                 "from core.workers.base import handle_worker_errors"),
                ("from ui.rom_extraction.workers.base import BaseWorker",
                 "from core.workers.base import BaseWorker"),
            ]
        },

        # Fix advanced_search_dialog.py imports
        {
            "file": "ui/dialogs/advanced_search_dialog.py",
            "additions": [
                ("import json", "import re\nimport mmap\nimport json"),  # Add after json import
            ],
            "replacements": [
                # Comment out the missing dialog import for now
                ("from ui.dialogs.similarity_results_dialog import show_similarity_results",
                 "# TODO: Create similarity_results_dialog.py\n# from ui.dialogs.similarity_results_dialog import show_similarity_results\nshow_similarity_results = lambda *args, **kwargs: None  # Temporary stub"),
            ]
        },

        # Fix search_worker.py if needed
        {
            "file": "ui/rom_extraction/workers/search_worker.py",
            "replacements": [
                # This one seems to have the correct import already
            ]
        }
    ]

    project_root = Path(__file__).parent

    for fix in fixes:
        file_path = project_root / fix["file"]
        if not file_path.exists():
            print(f"❌ File not found: {fix['file']}")
            continue

        with open(file_path) as f:
            content = f.read()

        original_content = content

        # Apply replacements
        for old, new in fix.get("replacements", []):
            if old in content:
                content = content.replace(old, new)
                print(f"✅ Fixed import in {fix['file']}: {old} -> {new}")

        # Apply additions
        for marker, new_content in fix.get("additions", []):
            if marker in content and new_content.split("\n")[0] not in content:
                content = content.replace(marker, new_content)
                print(f"✅ Added imports in {fix['file']}: {new_content.split('\\n')[0]}")

        # Write back if changed
        if content != original_content:
            with open(file_path, "w") as f:
                f.write(content)
            print(f"✅ Updated {fix['file']}")
        else:
            print(f"ℹ️  No changes needed in {fix['file']}")

    print("\n✅ Import fixes complete!")

    # Create a stub similarity results dialog
    stub_dialog_path = project_root / "ui" / "dialogs" / "similarity_results_dialog.py"
    if not stub_dialog_path.exists():
        stub_content = '''"""
Similarity results dialog for displaying visual search results.

TODO: Implement full dialog with sprite previews and similarity scores.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel

def show_similarity_results(matches, reference_offset, parent=None):
    """
    Show similarity search results in a dialog.

    Args:
        matches: List of SimilarityMatch objects
        reference_offset: Offset of reference sprite
        parent: Parent widget

    Returns:
        Dialog instance
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle("Visual Search Results")
    dialog.setMinimumSize(600, 400)

    layout = QVBoxLayout(dialog)

    # Temporary implementation
    label = QLabel(f"Found {len(matches)} similar sprites to 0x{reference_offset:X}")
    layout.addWidget(label)

    # Add placeholder for results
    for i, match in enumerate(matches[:10]):  # Show first 10
        result_label = QLabel(
            f"Sprite at 0x{match.offset:X} - "
            f"Similarity: {match.similarity_score:.1%}"
        )
        layout.addWidget(result_label)

    return dialog
'''
        stub_dialog_path.parent.mkdir(exist_ok=True)
        with open(stub_dialog_path, "w") as f:
            f.write(stub_content)
        print("\n✅ Created stub similarity_results_dialog.py")


if __name__ == "__main__":
    fix_imports()
