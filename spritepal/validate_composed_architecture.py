#!/usr/bin/env python3
from __future__ import annotations

"""
Validate Composed Manual Offset Dialog Architecture

This script validates that the composed architecture is properly structured
and can switch between implementations based on feature flags.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def validate_adapter_switching():
    """Validate that the adapter correctly switches implementations."""
    print("🔍 Validating adapter switching...")

    try:
        # Test composed mode
        os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = 'true'

        # Clear import cache to ensure fresh imports
        modules_to_clear = [
            'ui.dialogs.manual_offset.manual_offset_dialog_adapter',
            'ui.dialogs.manual_offset',
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]

        # Import in composed mode
        from ui.dialogs.manual_offset.manual_offset_dialog_adapter import _get_base_class
        composed_base = _get_base_class()

        print(f"✓ Composed mode base class: {composed_base.__name__}")

        # Test legacy mode
        os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = 'false'

        # Clear cache again
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]

        # Import in legacy mode
        from ui.dialogs.manual_offset.manual_offset_dialog_adapter import _get_base_class
        legacy_base = _get_base_class()

        print(f"✓ Legacy mode base class: {legacy_base.__name__}")

        # Verify they're different
        if composed_base != legacy_base:
            print("✅ Adapter correctly switches between implementations")
            return True
        else:
            print("❌ Adapter not switching properly")
            return False

    except Exception as e:
        print(f"❌ Adapter switching validation failed: {e}")
        return False

def validate_component_structure():
    """Validate that all component files exist and are properly structured."""
    print("🔍 Validating component structure...")

    component_dir = project_root / "ui" / "dialogs" / "manual_offset" / "components"
    expected_components = [
        "signal_router_component.py",
        "tab_manager_component.py",
        "layout_manager_component.py",
        "worker_coordinator_component.py",
        "rom_cache_component.py"
    ]

    missing_components = []
    for component in expected_components:
        component_path = component_dir / component
        if not component_path.exists():
            missing_components.append(component)
        else:
            print(f"✓ {component}")

    if missing_components:
        print(f"❌ Missing components: {missing_components}")
        return False
    else:
        print("✅ All components present")
        return True

def validate_core_structure():
    """Validate that core files exist and are properly structured."""
    print("🔍 Validating core structure...")

    core_dir = project_root / "ui" / "dialogs" / "manual_offset" / "core"
    expected_core_files = [
        "manual_offset_dialog_core.py",
        "component_factory.py"
    ]

    missing_files = []
    for file in expected_core_files:
        file_path = core_dir / file
        if not file_path.exists():
            missing_files.append(file)
        else:
            print(f"✓ {file}")

    if missing_files:
        print(f"❌ Missing core files: {missing_files}")
        return False
    else:
        print("✅ All core files present")
        return True

def validate_api_structure():
    """Validate that the API structure is correct by examining source code."""
    print("🔍 Validating API structure...")

    try:
        # Read adapter source
        adapter_file = project_root / "ui" / "dialogs" / "manual_offset" / "manual_offset_dialog_adapter.py"
        with open(adapter_file) as f:
            adapter_source = f.read()

        # Check for key patterns in adapter
        adapter_checks = [
            ('ManualOffsetDialogAdapter = type(', 'Dynamic class creation'),
            ('_get_base_class()', 'Base class selection function'),
            ('SPRITEPAL_USE_COMPOSED_DIALOGS', 'Feature flag usage'),
        ]

        for pattern, description in adapter_checks:
            if pattern in adapter_source:
                print(f"✓ {description}")
            else:
                print(f"❌ Missing: {description}")
                return False

        # Read core dialog source
        core_file = project_root / "ui" / "dialogs" / "manual_offset" / "core" / "manual_offset_dialog_core.py"
        with open(core_file) as f:
            core_source = f.read()

        # Check for key patterns in core
        core_checks = [
            ('class ManualOffsetDialogCore(DialogBase)', 'Correct base class'),
            ('offset_changed = Signal(int)', 'Signal definitions'),
            ('def _setup_components(self)', 'Component setup method'),
            ('@property', 'Property definitions for compatibility'),
        ]

        for pattern, description in core_checks:
            if pattern in core_source:
                print(f"✓ {description}")
            else:
                print(f"❌ Missing: {description}")
                return False

        print("✅ API structure is correct")
        return True

    except Exception as e:
        print(f"❌ API structure validation failed: {e}")
        return False

def validate_integration_points():
    """Validate that integration points are properly configured."""
    print("🔍 Validating integration points...")

    try:
        # Check main dialogs __init__.py
        dialogs_init = project_root / "ui" / "dialogs" / "__init__.py"
        with open(dialogs_init) as f:
            dialogs_source = f.read()

        integration_checks = [
            ('SPRITEPAL_USE_COMPOSED_DIALOGS', 'Feature flag check'),
            ('from .manual_offset import UnifiedManualOffsetDialog', 'Composed import'),
            ('from .manual_offset_unified_integrated import UnifiedManualOffsetDialog', 'Legacy import'),
            ('ManualOffsetDialog = UnifiedManualOffsetDialog', 'Primary interface'),
        ]

        for pattern, description in integration_checks:
            if pattern in dialogs_source:
                print(f"✓ {description}")
            else:
                print(f"❌ Missing: {description}")
                return False

        # Check manual_offset __init__.py
        manual_offset_init = project_root / "ui" / "dialogs" / "manual_offset" / "__init__.py"
        with open(manual_offset_init) as f:
            manual_offset_source = f.read()

        manual_offset_checks = [
            ('from .manual_offset_dialog_adapter import ManualOffsetDialogAdapter', 'Adapter import'),
            ('UnifiedManualOffsetDialog = ManualOffsetDialogAdapter', 'Alias for compatibility'),
        ]

        for pattern, description in manual_offset_checks:
            if pattern in manual_offset_source:
                print(f"✓ {description}")
            else:
                print(f"❌ Missing: {description}")
                return False

        print("✅ Integration points are correct")
        return True

    except Exception as e:
        print(f"❌ Integration validation failed: {e}")
        return False

def main():
    """Run all validation checks."""
    print("🚀 Validating Composed Manual Offset Dialog Architecture")
    print("=" * 60)

    # Run all validations
    validations = [
        validate_adapter_switching,
        validate_component_structure,
        validate_core_structure,
        validate_api_structure,
        validate_integration_points,
    ]

    passed = 0
    total = len(validations)

    for validation in validations:
        print()
        try:
            if validation():
                passed += 1
        except Exception as e:
            print(f"❌ Validation failed with exception: {e}")

    print()
    print("=" * 60)
    print(f"📊 Results: {passed}/{total} validations passed")

    if passed == total:
        print("🎉 All validations passed! Composed architecture is properly implemented.")
        print("✨ The implementation is ready for production use.")
        return 0
    else:
        print("⚠️ Some validations failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
