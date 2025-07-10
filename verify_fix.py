#!/usr/bin/env python3
"""Quick verification that the progress dialog fix works."""

from pixel_editor_widgets import ProgressDialog
from PyQt6.QtWidgets import QApplication
import sys

def test_fix():
    app = QApplication(sys.argv)
    
    dialog = ProgressDialog("Testing Fix")
    
    # Test 1: Original usage (value only) - should work
    try:
        dialog.update_progress(50)
        print("✅ Test 1 PASSED: update_progress(value) works")
    except Exception as e:
        print(f"❌ Test 1 FAILED: {e}")
    
    # Test 2: New usage (value + message) - this was failing before
    try:
        dialog.update_progress(75, "Loading data...")
        print("✅ Test 2 PASSED: update_progress(value, message) works")
    except Exception as e:
        print(f"❌ Test 2 FAILED: {e}")
    
    # Test 3: Verify message was actually set
    if dialog.message_label.text() == "Loading data...":
        print("✅ Test 3 PASSED: Message was properly updated")
    else:
        print(f"❌ Test 3 FAILED: Message is '{dialog.message_label.text()}'")
    
    print("\nAll tests completed!")
    return 0

if __name__ == "__main__":
    sys.exit(test_fix())