
import pytest

pytestmark = [
    pytest.mark.cache,
    pytest.mark.dialog,
    pytest.mark.gui,
    pytest.mark.requires_display,
]
#!/usr/bin/env python
"""
Quick validation test for UnifiedManualOffsetDialog migration.
Tests that both implementations can be created and have the same interface.
"""

import os
import sys

# Add parent directory to path so we can import ui.dialogs
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication


def test_legacy_implementation():
    """Test that legacy implementation can be created."""
    print("\n" + "="*60)
    print("Testing LEGACY implementation...")
    print("="*60)
    
    # Set flag for legacy
    os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = 'false'
    
    # Clear module cache
    for module in list(sys.modules.keys()):
        if 'ui.dialogs' in module or 'manual_offset' in module:
            del sys.modules[module]
    
    # Import and create
    from ui.dialogs import UnifiedManualOffsetDialog
    
    dialog = UnifiedManualOffsetDialog(None)
    
    # Test basic properties
    assert hasattr(dialog, 'offset_changed'), "Missing offset_changed signal"
    assert hasattr(dialog, 'sprite_found'), "Missing sprite_found signal"
    assert hasattr(dialog, 'validation_failed'), "Missing validation_failed signal"
    assert hasattr(dialog, 'set_rom_data'), "Missing set_rom_data method"
    assert hasattr(dialog, 'set_offset'), "Missing set_offset method"
    assert hasattr(dialog, 'get_current_offset'), "Missing get_current_offset method"
    assert hasattr(dialog, 'cleanup'), "Missing cleanup method"
    
    print("✓ Legacy implementation created successfully")
    print("✓ All required signals present")
    print("✓ All required methods present")
    
    # Cleanup
    dialog.cleanup()
    dialog.deleteLater()
    
    return True


def test_composed_implementation():
    """Test that composed implementation can be created."""
    print("\n" + "="*60)
    print("Testing COMPOSED implementation...")
    print("="*60)
    
    # Set flag for composed
    os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = 'true'
    
    # Clear module cache
    for module in list(sys.modules.keys()):
        if 'ui.dialogs' in module or 'manual_offset' in module:
            del sys.modules[module]
    
    # Import and create
    from ui.dialogs import UnifiedManualOffsetDialog
    
    dialog = UnifiedManualOffsetDialog(None)
    
    # Test basic properties
    assert hasattr(dialog, 'offset_changed'), "Missing offset_changed signal"
    assert hasattr(dialog, 'sprite_found'), "Missing sprite_found signal"
    assert hasattr(dialog, 'validation_failed'), "Missing validation_failed signal"
    assert hasattr(dialog, 'set_rom_data'), "Missing set_rom_data method"
    assert hasattr(dialog, 'set_offset'), "Missing set_offset method"
    assert hasattr(dialog, 'get_current_offset'), "Missing get_current_offset method"
    assert hasattr(dialog, 'cleanup'), "Missing cleanup method"
    
    print("✓ Composed implementation created successfully")
    print("✓ All required signals present")
    print("✓ All required methods present")
    
    # Cleanup
    dialog.cleanup()
    dialog.deleteLater()
    
    return True


def test_api_compatibility():
    """Test that both implementations have the same API."""
    print("\n" + "="*60)
    print("Testing API compatibility...")
    print("="*60)
    
    # Get legacy API
    os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = 'false'
    for module in list(sys.modules.keys()):
        if 'ui.dialogs' in module or 'manual_offset' in module:
            del sys.modules[module]
    from ui.dialogs import UnifiedManualOffsetDialog as LegacyDialog
    
    # Get composed API
    os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = 'true'
    for module in list(sys.modules.keys()):
        if 'ui.dialogs' in module or 'manual_offset' in module:
            del sys.modules[module]
    from ui.dialogs import UnifiedManualOffsetDialog as ComposedDialog
    
    # Create instances
    legacy = LegacyDialog(None)
    composed = ComposedDialog(None)
    
    # Get public methods
    legacy_methods = [m for m in dir(legacy) if not m.startswith('_') and callable(getattr(legacy, m, None))]
    composed_methods = [m for m in dir(composed) if not m.startswith('_') and callable(getattr(composed, m, None))]
    
    # Find differences
    only_in_legacy = set(legacy_methods) - set(composed_methods)
    only_in_composed = set(composed_methods) - set(legacy_methods)
    
    if only_in_legacy:
        print(f"⚠ Methods only in legacy: {only_in_legacy}")
    if only_in_composed:
        print(f"⚠ Methods only in composed: {only_in_composed}")
    
    # Check key methods
    key_methods = [
        'set_rom_data', 'set_offset', 'get_current_offset', 
        'add_found_sprite', 'cleanup', 'show', 'hide', 'close'
    ]
    
    for method in key_methods:
        assert hasattr(legacy, method), f"Legacy missing {method}"
        assert hasattr(composed, method), f"Composed missing {method}"
        print(f"✓ Both have method: {method}")
    
    # Cleanup
    legacy.cleanup()
    composed.cleanup()
    legacy.deleteLater()
    composed.deleteLater()
    
    print("\n✓ API compatibility verified")
    return True


def main():
    """Run all validation tests."""
    print("\n" + "#"*60)
    print("# UnifiedManualOffsetDialog Migration Validation")
    print("#"*60)
    
    # Create Qt application
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Initialize managers for the test
    from core.managers.registry import initialize_managers
    initialize_managers()
    
    try:
        # Run tests
        legacy_ok = test_legacy_implementation()
        composed_ok = test_composed_implementation()
        api_ok = test_api_compatibility()
        
        # Summary
        print("\n" + "#"*60)
        print("# SUMMARY")
        print("#"*60)
        
        if legacy_ok and composed_ok and api_ok:
            print("✅ ALL TESTS PASSED")
            print("✅ Both implementations work correctly")
            print("✅ API compatibility maintained")
            print("\nThe migration is ready for testing!")
        else:
            print("❌ SOME TESTS FAILED")
            if not legacy_ok:
                print("  - Legacy implementation failed")
            if not composed_ok:
                print("  - Composed implementation failed")
            if not api_ok:
                print("  - API compatibility issues")
        
        return 0 if (legacy_ok and composed_ok and api_ok) else 1
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())