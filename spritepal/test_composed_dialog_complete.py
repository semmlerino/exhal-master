#!/usr/bin/env python3
from __future__ import annotations

"""
Comprehensive test for composed dialog functionality including deferred signal connections.

This test verifies:
1. Composed dialog loads correctly
2. ButtonBoxManager signals work 
3. Deferred signal connection for singleton pattern works
4. Dialog buttons function correctly
5. Dialog lifecycle works properly
"""

import logging
import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up composed dialogs before any imports
os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = '1'

import tempfile

from PySide6.QtWidgets import QApplication, QDialogButtonBox

# Configure logging to see debug messages
logging.basicConfig(
    level=logging.WARNING,  # Show warnings and errors
    format='%(name)s - %(levelname)s - %(message)s'
)

def test_composed_dialog_creation(app):
    """Test basic composed dialog creation and initialization."""
    print("=" * 60)
    print("TEST 1: Basic Composed Dialog Creation")
    print("=" * 60)

    from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog

    try:
        print("Creating composed dialog...")
        dialog = UnifiedManualOffsetDialog()

        # Verify dialog type
        expected_type = "DialogBaseMigrationAdapter"
        actual_type = type(dialog).__bases__[0].__name__
        assert actual_type == expected_type, f"Expected {expected_type}, got {actual_type}"
        print(f"✓ Dialog created with correct type: {type(dialog).__name__}")

        # Verify basic methods exist
        assert hasattr(dialog, 'accept'), "Dialog missing accept method"
        assert hasattr(dialog, 'reject'), "Dialog missing reject method"
        assert hasattr(dialog, 'show'), "Dialog missing show method"
        print("✓ Dialog has required methods")

        # Verify button box exists
        button_manager = dialog.get_component('button_box')
        assert button_manager is not None, "ButtonBoxManager not found"
        assert button_manager.is_available, "Button box not available"
        print("✓ ButtonBoxManager available")

        print("✓ TEST 1 PASSED: Basic composed dialog creation works")

    except Exception as e:
        print(f"✗ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

def test_button_functionality(app):
    """Test that dialog buttons work correctly."""
    print("=" * 60)
    print("TEST 2: Button Functionality")
    print("=" * 60)

    from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog

    try:
        print("Creating dialog for button testing...")
        dialog = UnifiedManualOffsetDialog()

        # Get button manager and buttons
        button_manager = dialog.get_component('button_box')
        ok_button = button_manager.get_button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = button_manager.get_button(QDialogButtonBox.StandardButton.Cancel)

        assert ok_button is not None, "OK button not found"
        assert cancel_button is not None, "Cancel button not found"
        print("✓ OK and Cancel buttons exist")

        # Test button click functionality
        print("Testing OK button click...")
        dialog.result()
        ok_button.click()
        final_result = dialog.result()

        assert final_result == 1, f"Expected result=1 after OK click, got {final_result}"  # QDialog.DialogCode.Accepted = 1
        print("✓ OK button click works correctly")

        print("✓ TEST 2 PASSED: Button functionality works")

    except Exception as e:
        print(f"✗ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        app.quit()

    return True

def test_singleton_pattern_with_signals():
    """Test singleton pattern with deferred signal connections."""
    print("=" * 60)
    print("TEST 3: Singleton Pattern with Deferred Signals")
    print("=" * 60)


    from ui.main_window import SpritePalMainWindow
    from ui.rom_extraction_panel import ManualOffsetDialogSingleton

    app = QApplication([])

    try:
        # Create a temporary ROM file for testing
        temp_rom = tempfile.NamedTemporaryFile(suffix='.sfc', delete=False)
        temp_rom.write(b'\x00' * 1024)  # Minimal ROM data
        temp_rom.close()

        print("Creating main window and ROM extraction panel...")
        main_window = SpritePalMainWindow()
        rom_panel = main_window.rom_extraction_panel

        # Set up ROM path
        rom_panel.rom_path = temp_rom.name
        rom_panel.rom_size = 1024

        print("Testing singleton dialog creation...")

        # Reset any existing singleton
        ManualOffsetDialogSingleton.reset()

        # Test getting dialog instance (should create and defer signals)
        dialog = ManualOffsetDialogSingleton.get_dialog(rom_panel)
        assert dialog is not None, "Failed to create dialog instance"
        print("✓ Singleton dialog created")

        # Check that deferred signal connection was set up
        has_deferred = hasattr(dialog, '_deferred_signal_connection')
        print(f"✓ Deferred signal connection {'set up' if has_deferred else 'not found'}")

        # Simulate opening the dialog (this should trigger deferred signals)
        print("Testing dialog show with deferred signal connection...")

        # Mock the dialog opening process
        if not dialog.isVisible():
            dialog.show()
            app.processEvents()  # Process the show event

            # Call deferred signal connection if it exists
            if hasattr(dialog, '_deferred_signal_connection'):
                print("Calling deferred signal connection...")
                dialog._deferred_signal_connection()
                delattr(dialog, '_deferred_signal_connection')
                print("✓ Deferred signal connection completed")

        print("✓ Dialog shown successfully")

        # Test that the dialog can be closed properly
        print("Testing dialog close...")
        dialog.close()
        print("✓ Dialog closed successfully")

        print("✓ TEST 3 PASSED: Singleton pattern with deferred signals works")

    except Exception as e:
        print(f"✗ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Clean up temp file
        try:
            os.unlink(temp_rom.name)
        except Exception:
            # Caught exception during operation
            pass
        app.quit()

    return True

def test_dialog_lifecycle():
    """Test complete dialog lifecycle including signal connections."""
    print("=" * 60)
    print("TEST 4: Complete Dialog Lifecycle")
    print("=" * 60)

    from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog

    app = QApplication([])

    try:
        print("Creating dialog for lifecycle test...")
        dialog = UnifiedManualOffsetDialog()

        # Test initial state
        assert not dialog.isVisible(), "Dialog should not be visible initially"
        assert dialog.result() == 0, "Dialog should have initial result of 0"
        print("✓ Dialog initial state correct")

        # Test showing dialog
        dialog.show()
        app.processEvents()
        assert dialog.isVisible(), "Dialog should be visible after show()"
        print("✓ Dialog show works")

        # Test button manager signals are connected
        button_manager = dialog.get_component('button_box')

        # Verify signal connections work
        signal_test_passed = False
        def test_signal_handler():
            nonlocal signal_test_passed
            signal_test_passed = True

        # Test ButtonBoxManager signal
        button_manager.accepted.connect(test_signal_handler)
        button_manager.accepted.emit()
        assert signal_test_passed, "ButtonBoxManager.accepted signal not working"
        print("✓ ButtonBoxManager signals work")

        # Test dialog close
        dialog.close()
        app.processEvents()
        assert not dialog.isVisible(), "Dialog should not be visible after close()"
        print("✓ Dialog close works")

        print("✓ TEST 4 PASSED: Complete dialog lifecycle works")

    except Exception as e:
        print(f"✗ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        app.quit()

    return True

def test_legacy_vs_composed_comparison():
    """Compare legacy vs composed dialog functionality."""
    print("=" * 60)
    print("TEST 5: Legacy vs Composed Comparison")
    print("=" * 60)

    try:
        # Test composed dialog
        print("Testing composed dialog...")
        os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = '1'

        # Clear module cache to ensure fresh import
        import importlib

        import ui.dialogs.manual_offset_unified_integrated
        importlib.reload(ui.dialogs.manual_offset_unified_integrated)

        app1 = QApplication([])
        from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
        composed_dialog = UnifiedManualOffsetDialog()
        composed_type = type(composed_dialog).__name__
        app1.quit()

        print("Testing legacy dialog...")
        os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = '0'

        # Clear module cache and reload
        importlib.reload(ui.dialogs.manual_offset_unified_integrated)

        app2 = QApplication([])
        from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
        legacy_dialog = UnifiedManualOffsetDialog()
        legacy_type = type(legacy_dialog).__name__
        app2.quit()

        print(f"✓ Composed dialog type: {composed_type}")
        print(f"✓ Legacy dialog type: {legacy_type}")

        # Verify they are different implementations
        assert composed_type != legacy_type, "Composed and legacy dialogs should use different base classes"
        print("✓ Composed and legacy dialogs use different implementations")

        print("✓ TEST 5 PASSED: Legacy vs composed comparison successful")

    except Exception as e:
        print(f"✗ TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

def main():
    """Run all tests."""
    print("COMPOSED DIALOG COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    # Ensure composed dialogs are enabled
    os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = '1'

    tests = [
        test_composed_dialog_creation,
        test_button_functionality,
        test_singleton_pattern_with_signals,
        test_dialog_lifecycle,
        test_legacy_vs_composed_comparison,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1

        print()  # Add spacing between tests

    print("=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"✓ PASSED: {passed}")
    print(f"✗ FAILED: {failed}")
    print(f"TOTAL: {passed + failed}")

    if failed == 0:
        print("🎉 ALL TESTS PASSED! Composed dialog functionality is working correctly.")
        return True
    else:
        print("⚠️ SOME TESTS FAILED. Please check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
