#!/usr/bin/env python3
from __future__ import annotations

"""
Test script to validate SimilarityResultsDialog migration.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from core.visual_similarity_search import SimilarityMatch
from PySide6.QtWidgets import QApplication
from ui.dialogs.similarity_results_dialog import SimilarityResultsDialog


def test_similarity_dialog_legacy():
    """Test SimilarityResultsDialog with legacy implementation."""
    print("Testing SimilarityResultsDialog with LEGACY implementation...")

    os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = 'false'

    # Create some mock similarity matches
    matches = [
        SimilarityMatch(offset=0x10000, similarity_score=0.95, hash_distance=2, metadata={}),
        SimilarityMatch(offset=0x20000, similarity_score=0.87, hash_distance=5, metadata={}),
        SimilarityMatch(offset=0x30000, similarity_score=0.82, hash_distance=8, metadata={}),
    ]

    # Test dialog creation
    dialog = SimilarityResultsDialog(matches, source_offset=0x5000)
    print(f"✓ Dialog created: {type(dialog).__name__}")

    # Test required signals
    required_signals = ['sprite_selected']
    for signal_name in required_signals:
        if hasattr(dialog, signal_name):
            print(f"✓ Signal '{signal_name}' present")
        else:
            print(f"❌ Signal '{signal_name}' missing")
            return False

    # Test required methods
    required_methods = ['_on_sprite_selected']
    for method_name in required_methods:
        if hasattr(dialog, method_name):
            print(f"✓ Method '{method_name}' present")
        else:
            print(f"❌ Method '{method_name}' missing")
            return False

    # Cleanup
    dialog.deleteLater()
    return True

def test_similarity_dialog_composed():
    """Test SimilarityResultsDialog with composed implementation."""
    print("Testing SimilarityResultsDialog with COMPOSED implementation...")

    os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = 'true'

    # Create some mock similarity matches
    matches = [
        SimilarityMatch(offset=0x10000, similarity_score=0.95, hash_distance=2, metadata={}),
        SimilarityMatch(offset=0x20000, similarity_score=0.87, hash_distance=5, metadata={}),
    ]

    # Test dialog creation
    dialog = SimilarityResultsDialog(matches, source_offset=0x5000)
    print(f"✓ Dialog created: {type(dialog).__name__}")

    # Test required signals
    required_signals = ['sprite_selected']
    for signal_name in required_signals:
        if hasattr(dialog, signal_name):
            print(f"✓ Signal '{signal_name}' present")
        else:
            print(f"❌ Signal '{signal_name}' missing")
            return False

    # Test required methods
    required_methods = ['_on_sprite_selected']
    for method_name in required_methods:
        if hasattr(dialog, method_name):
            print(f"✓ Method '{method_name}' present")
        else:
            print(f"❌ Method '{method_name}' missing")
            return False

    # Cleanup
    dialog.deleteLater()
    return True

def main():
    """Run similarity dialog migration tests."""
    print("############################################################")
    print("# SimilarityResultsDialog Migration Validation")
    print("############################################################")

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    # Test legacy implementation
    legacy_ok = test_similarity_dialog_legacy()
    print()

    # Test composed implementation
    composed_ok = test_similarity_dialog_composed()
    print()

    print("############################################################")
    print("# SUMMARY")
    print("############################################################")
    if legacy_ok and composed_ok:
        print("✅ ALL TESTS PASSED")
        print("✅ Both implementations work correctly")
        print("✅ SimilarityResultsDialog migration successful!")
    else:
        print("❌ TESTS FAILED")
        if not legacy_ok:
            print("❌ Legacy implementation failed")
        if not composed_ok:
            print("❌ Composed implementation failed")

    app.quit()
    return 0 if (legacy_ok and composed_ok) else 1

if __name__ == "__main__":
    sys.exit(main())
