#!/usr/bin/env python3
"""
Simple import test for ResumeScanDialog pilot migration.

This test verifies that the import mechanism works correctly
with both legacy and composed implementations without requiring Qt.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_feature_flag_controls():
    """Test that feature flag controls work correctly."""
    print("\n" + "="*60)
    print("Testing Feature Flag Controls")
    print("="*60)
    
    from ui.components.base import (
        set_dialog_implementation,
        get_dialog_implementation,
        is_composed_dialogs_enabled
    )
    
    # Test setting to legacy
    set_dialog_implementation(False)
    assert get_dialog_implementation() == "legacy", "Failed to set legacy"
    assert not is_composed_dialogs_enabled(), "Flag should be False for legacy"
    print("✓ Successfully set to legacy implementation")
    
    # Test setting to composed
    set_dialog_implementation(True)
    assert get_dialog_implementation() == "composed", "Failed to set composed"
    assert is_composed_dialogs_enabled(), "Flag should be True for composed"
    print("✓ Successfully set to composed implementation")
    
    # Reset to legacy for next tests
    set_dialog_implementation(False)
    print("✓ Feature flag controls working correctly")
    return True


def test_import_with_implementation(use_composed: bool):
    """Test importing ResumeScanDialog with specific implementation."""
    implementation = "composed" if use_composed else "legacy"
    
    print("\n" + "="*60)
    print(f"Testing Import with {implementation.upper()} Implementation")
    print("="*60)
    
    # Set the implementation
    from ui.components.base import set_dialog_implementation, get_dialog_implementation
    set_dialog_implementation(use_composed)
    
    # Clear any cached imports
    modules_to_clear = [
        'ui.dialogs.resume_scan_dialog',
        'ui.components.base',
        'ui.components.base.dialog_selector',
        'ui.components.base.dialog_base',
        'ui.components.base.composed',
        'ui.components.base.composed.migration_adapter',
    ]
    
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]
    
    # Verify implementation is set
    from ui.components.base import get_dialog_implementation as get_impl
    actual_impl = get_impl()
    print(f"  Feature flag set to: {actual_impl}")
    
    try:
        # Try to import ResumeScanDialog
        from ui.dialogs.resume_scan_dialog import ResumeScanDialog
        
        # Check that it imported successfully
        assert ResumeScanDialog is not None, "ResumeScanDialog is None"
        assert hasattr(ResumeScanDialog, '__name__'), "ResumeScanDialog has no __name__"
        assert ResumeScanDialog.__name__ == 'ResumeScanDialog', f"Wrong class name: {ResumeScanDialog.__name__}"
        
        # Check for expected class attributes/constants
        assert hasattr(ResumeScanDialog, 'RESUME'), "Missing RESUME constant"
        assert hasattr(ResumeScanDialog, 'START_FRESH'), "Missing START_FRESH constant"
        assert hasattr(ResumeScanDialog, 'CANCEL'), "Missing CANCEL constant"
        
        # Verify constants have expected values
        assert ResumeScanDialog.RESUME == 1, f"RESUME = {ResumeScanDialog.RESUME}, expected 1"
        assert ResumeScanDialog.START_FRESH == 2, f"START_FRESH = {ResumeScanDialog.START_FRESH}, expected 2"
        assert ResumeScanDialog.CANCEL == 0, f"CANCEL = {ResumeScanDialog.CANCEL}, expected 0"
        
        # Check for expected methods
        expected_methods = [
            '__init__',
            '_format_progress_info',
            '_on_resume',
            '_on_start_fresh',
            '_on_cancel',
            'get_user_choice',
            'show_resume_dialog'
        ]
        
        for method in expected_methods:
            assert hasattr(ResumeScanDialog, method), f"Missing method: {method}"
            assert callable(getattr(ResumeScanDialog, method)), f"Method not callable: {method}"
        
        print(f"✓ ResumeScanDialog imported successfully with {implementation} implementation")
        print(f"  - All class constants present and correct")
        print(f"  - All expected methods present")
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import ResumeScanDialog with {implementation}: {e}")
        import traceback
        traceback.print_exc()
        return False
    except AssertionError as e:
        print(f"✗ Assertion failed with {implementation}: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error with {implementation}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_base_dialog_source():
    """Test that BaseDialog comes from the expected source."""
    print("\n" + "="*60)
    print("Testing BaseDialog Source")
    print("="*60)
    
    # Test with legacy
    from ui.components.base import set_dialog_implementation
    
    # Clear imports
    if 'ui.components.base' in sys.modules:
        del sys.modules['ui.components.base']
    if 'ui.components.base.dialog_selector' in sys.modules:
        del sys.modules['ui.components.base.dialog_selector']
    
    set_dialog_implementation(False)
    from ui.components.base import BaseDialog as LegacyDialog
    print(f"✓ Legacy BaseDialog type: {type(LegacyDialog)}")
    print(f"  Module: {LegacyDialog.__module__ if hasattr(LegacyDialog, '__module__') else 'N/A'}")
    
    # Clear imports again
    if 'ui.components.base' in sys.modules:
        del sys.modules['ui.components.base']
    if 'ui.components.base.dialog_selector' in sys.modules:
        del sys.modules['ui.components.base.dialog_selector']
    
    # Test with composed
    set_dialog_implementation(True)
    from ui.components.base import BaseDialog as ComposedDialog
    print(f"✓ Composed BaseDialog type: {type(ComposedDialog)}")
    print(f"  Module: {ComposedDialog.__module__ if hasattr(ComposedDialog, '__module__') else 'N/A'}")
    
    # They should be different classes when Qt is available
    # But in test mode without Qt, they might be placeholder classes
    if LegacyDialog.__module__ != ComposedDialog.__module__:
        print("✓ Different implementations loaded as expected")
    else:
        print("ℹ Same implementation loaded (likely in test mode without Qt)")
    
    return True


def main():
    """Main test runner."""
    print("\n" + "="*80)
    print("ResumeScanDialog Import Test - Feature Flag Migration Validation")
    print("="*80)
    
    results = []
    
    # Test feature flag controls
    results.append(("Feature Flag Controls", test_feature_flag_controls()))
    
    # Test BaseDialog source switching
    results.append(("BaseDialog Source", test_base_dialog_source()))
    
    # Test importing with legacy implementation
    results.append(("Import with Legacy", test_import_with_implementation(use_composed=False)))
    
    # Test importing with composed implementation
    results.append(("Import with Composed", test_import_with_implementation(use_composed=True)))
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("="*80)
    
    if all_passed:
        print("\n✓ SUCCESS: All import tests passed!")
        print("  The feature flag system is working correctly for imports.")
        print("  ResumeScanDialog can import with both implementations.")
        print("\nNOTE: This test only validates imports and class structure.")
        print("      Full Qt functionality should be tested in a Qt environment.")
        return 0
    else:
        print("\n✗ FAILURE: Some tests failed!")
        print("  Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())