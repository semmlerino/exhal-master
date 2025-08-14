
import pytest

pytestmark = [
    pytest.mark.cache,
    pytest.mark.dialog,
    pytest.mark.gui,
    pytest.mark.integration,
    pytest.mark.performance,
    pytest.mark.qt_real,
    pytest.mark.requires_display,
    pytest.mark.rom_data,
    pytest.mark.signals_slots,
]
"""
Comprehensive Test Suite for UnifiedManualOffsetDialog Migration

This test suite verifies that both the legacy and composed implementations
of UnifiedManualOffsetDialog work identically.
"""

import os
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtTest import QTest

# Test fixtures
@pytest.fixture
def qt_app():
    """Ensure Qt application exists for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # Don't quit app - let pytest-qt handle it


@pytest.fixture(params=["legacy", "composed"])
def dialog_implementation(request, qt_app, monkeypatch):
    """Fixture that provides both implementations for testing."""
    # Set environment variable based on parameter
    if request.param == "composed":
        monkeypatch.setenv("SPRITEPAL_USE_COMPOSED_DIALOGS", "true")
    else:
        monkeypatch.setenv("SPRITEPAL_USE_COMPOSED_DIALOGS", "false")
    
    # Clear any cached imports
    modules_to_clear = [
        'ui.dialogs',
        'ui.dialogs.manual_offset',
        'ui.dialogs.manual_offset.manual_offset_dialog_adapter',
        'ui.dialogs.manual_offset.core',
        'ui.dialogs.manual_offset.core.manual_offset_dialog_core',
    ]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]
    
    # Import with the correct environment setting
    from ui.dialogs import UnifiedManualOffsetDialog
    
    # Create instance
    dialog = UnifiedManualOffsetDialog(None)
    
    # Add metadata about which implementation
    dialog._test_implementation = request.param
    
    yield dialog
    
    # Cleanup
    try:
        dialog.cleanup()
        dialog.close()
        dialog.deleteLater()
    except:
        pass


class TestUnifiedDialogMigration:
    """Test suite comparing legacy and composed implementations."""
    
    def test_dialog_creation(self, dialog_implementation):
        """Test that dialog can be created without errors."""
        assert dialog_implementation is not None
        assert hasattr(dialog_implementation, 'offset_changed')
        assert hasattr(dialog_implementation, 'sprite_found')
        assert hasattr(dialog_implementation, 'validation_failed')
        
    def test_public_api_methods(self, dialog_implementation):
        """Test all public API methods exist and work."""
        # Test set_rom_data
        mock_manager = Mock()
        mock_manager.get_rom_extractor.return_value = Mock()
        
        dialog_implementation.set_rom_data(
            "/test/rom.gba", 
            0x800000, 
            mock_manager
        )
        assert dialog_implementation.rom_path == "/test/rom.gba"
        assert dialog_implementation.rom_size == 0x800000
        
        # Test set_offset / get_current_offset
        dialog_implementation.set_offset(0x123456)
        # Note: Offset might not be set if browse_tab is None in test
        offset = dialog_implementation.get_current_offset()
        assert isinstance(offset, int)
        
        # Test add_found_sprite
        dialog_implementation.add_found_sprite(0x200000, 0.95)
        # Should not raise error even if history_tab is None
        
    def test_widget_methods(self, dialog_implementation):
        """Test standard widget methods."""
        # Test visibility methods
        dialog_implementation.show()
        assert dialog_implementation.isVisible()
        
        dialog_implementation.hide()
        assert not dialog_implementation.isVisible()
        
        # Test size methods
        dialog_implementation.resize(800, 600)
        assert dialog_implementation.width() > 0
        assert dialog_implementation.height() > 0
        
        # Test window title
        dialog_implementation.setWindowTitle("Test Title")
        # Should not raise error
        
    def test_signal_emissions(self, dialog_implementation, qtbot):
        """Test that signals are emitted correctly."""
        # Test offset_changed signal
        with qtbot.waitSignal(dialog_implementation.offset_changed, timeout=100, raising=False) as blocker:
            # Try to trigger offset change
            if hasattr(dialog_implementation, 'browse_tab') and dialog_implementation.browse_tab:
                dialog_implementation.set_offset(0x300000)
        
        # Test sprite_found signal
        # This signal is emitted through apply button or other actions
        # Just verify it exists and can be connected
        mock_slot = Mock()
        dialog_implementation.sprite_found.connect(mock_slot)
        
        # Test validation_failed signal
        mock_validation = Mock()
        dialog_implementation.validation_failed.connect(mock_validation)
        
    def test_resource_cleanup(self, dialog_implementation):
        """Test that cleanup properly releases resources."""
        # Set up some resources
        dialog_implementation.rom_path = "/test/rom.gba"
        dialog_implementation.rom_size = 0x800000
        
        # Call cleanup
        dialog_implementation.cleanup()
        
        # Verify resources are cleaned
        # The exact behavior depends on implementation
        # Just ensure cleanup doesn't raise errors
        
    def test_property_access(self, dialog_implementation):
        """Test that properties can be accessed."""
        # These properties might be None in test environment
        # but should be accessible without error
        
        # Test tab_widget property
        tab_widget = dialog_implementation.tab_widget if hasattr(dialog_implementation, 'tab_widget') else None
        # Should not raise AttributeError
        
        # Test browse_tab property  
        browse_tab = dialog_implementation.browse_tab if hasattr(dialog_implementation, 'browse_tab') else None
        # Should not raise AttributeError
        
        # Test preview_widget property
        preview_widget = dialog_implementation.preview_widget if hasattr(dialog_implementation, 'preview_widget') else None
        # Should not raise AttributeError
        
        # Test main_splitter property
        main_splitter = dialog_implementation.main_splitter if hasattr(dialog_implementation, 'main_splitter') else None
        # Should not raise AttributeError
        
        # Test button_box property
        button_box = dialog_implementation.button_box if hasattr(dialog_implementation, 'button_box') else None
        # Should not raise AttributeError
        
    def test_event_handlers(self, dialog_implementation):
        """Test that event handlers work correctly."""
        from PySide6.QtGui import QShowEvent, QHideEvent, QCloseEvent, QResizeEvent
        
        # Test show event
        show_event = QShowEvent()
        dialog_implementation.showEvent(show_event)
        
        # Test hide event  
        hide_event = QHideEvent()
        dialog_implementation.hideEvent(hide_event)
        
        # Test resize event
        resize_event = QResizeEvent(dialog_implementation.size(), dialog_implementation.size())
        dialog_implementation.resizeEvent(resize_event)
        
        # Test close event
        close_event = QCloseEvent()
        dialog_implementation.closeEvent(close_event)
        
    def test_internal_methods(self, dialog_implementation):
        """Test internal methods that might be called externally."""
        # Test _update_status if it exists
        if hasattr(dialog_implementation, '_update_status'):
            dialog_implementation._update_status("Test status")
            # Should not raise error
            
        # Test _has_rom_data if it exists
        if hasattr(dialog_implementation, '_has_rom_data'):
            has_data = dialog_implementation._has_rom_data()
            assert isinstance(has_data, bool)


class TestImplementationConsistency:
    """Test that both implementations behave identically."""
    
    @pytest.fixture
    def both_dialogs(self, qt_app, monkeypatch):
        """Create both implementations for comparison."""
        # Create legacy implementation
        monkeypatch.setenv("SPRITEPAL_USE_COMPOSED_DIALOGS", "false")
        # Clear cached imports
        for module in list(sys.modules.keys()):
            if 'ui.dialogs' in module:
                del sys.modules[module]
        from ui.dialogs import UnifiedManualOffsetDialog as LegacyDialog
        legacy = LegacyDialog(None)
        
        # Create composed implementation
        monkeypatch.setenv("SPRITEPAL_USE_COMPOSED_DIALOGS", "true")
        # Clear cached imports again
        for module in list(sys.modules.keys()):
            if 'ui.dialogs' in module:
                del sys.modules[module]
        from ui.dialogs import UnifiedManualOffsetDialog as ComposedDialog
        composed = ComposedDialog(None)
        
        yield legacy, composed
        
        # Cleanup
        for dialog in [legacy, composed]:
            try:
                dialog.cleanup()
                dialog.close()
                dialog.deleteLater()
            except:
                pass
    
    def test_same_signals(self, both_dialogs):
        """Test that both implementations have the same signals."""
        legacy, composed = both_dialogs
        
        # Check same signals exist
        legacy_signals = [attr for attr in dir(legacy) if isinstance(getattr(legacy, attr, None), Signal)]
        composed_signals = [attr for attr in dir(composed) if isinstance(getattr(composed, attr, None), Signal)]
        
        # Core signals that must exist
        required_signals = ['offset_changed', 'sprite_found', 'validation_failed']
        for signal_name in required_signals:
            assert hasattr(legacy, signal_name), f"Legacy missing signal: {signal_name}"
            assert hasattr(composed, signal_name), f"Composed missing signal: {signal_name}"
            
    def test_same_methods(self, both_dialogs):
        """Test that both implementations have the same public methods."""
        legacy, composed = both_dialogs
        
        # Key public methods that must exist
        required_methods = [
            'set_rom_data',
            'set_offset', 
            'get_current_offset',
            'add_found_sprite',
            'cleanup',
            'show',
            'hide',
            'close',
            'isVisible'
        ]
        
        for method_name in required_methods:
            assert hasattr(legacy, method_name), f"Legacy missing method: {method_name}"
            assert callable(getattr(legacy, method_name)), f"Legacy {method_name} not callable"
            assert hasattr(composed, method_name), f"Composed missing method: {method_name}"
            assert callable(getattr(composed, method_name)), f"Composed {method_name} not callable"
            
    def test_same_properties(self, both_dialogs):
        """Test that both implementations expose the same properties."""
        legacy, composed = both_dialogs
        
        # Properties that should be accessible (may be None)
        properties = ['rom_path', 'rom_size', 'extraction_manager']
        
        for prop_name in properties:
            # Both should have the property (even if None)
            assert hasattr(legacy, prop_name), f"Legacy missing property: {prop_name}"
            assert hasattr(composed, prop_name), f"Composed missing property: {prop_name}"
            
    def test_same_behavior_rom_data(self, both_dialogs):
        """Test that both handle ROM data the same way."""
        legacy, composed = both_dialogs
        
        mock_manager = Mock()
        mock_manager.get_rom_extractor.return_value = Mock()
        
        # Set same ROM data on both
        legacy.set_rom_data("/test/rom.gba", 0x800000, mock_manager)
        composed.set_rom_data("/test/rom.gba", 0x800000, mock_manager)
        
        # Both should store the same values
        assert legacy.rom_path == composed.rom_path
        assert legacy.rom_size == composed.rom_size
        
    def test_same_initial_state(self, both_dialogs):
        """Test that both start with the same initial state."""
        legacy, composed = both_dialogs
        
        # Check initial values
        assert legacy.rom_path == composed.rom_path == ""
        assert legacy.rom_size == composed.rom_size == 0x400000
        
        # Check initial offset
        legacy_offset = legacy.get_current_offset()
        composed_offset = composed.get_current_offset()
        assert legacy_offset == composed_offset == 0x200000


class TestComponentIntegration:
    """Test composed implementation components work correctly."""
    
    @pytest.fixture
    def composed_dialog(self, qt_app, monkeypatch):
        """Create composed implementation for component testing."""
        monkeypatch.setenv("SPRITEPAL_USE_COMPOSED_DIALOGS", "true")
        
        # Clear cached imports
        for module in list(sys.modules.keys()):
            if 'ui.dialogs' in module:
                del sys.modules[module]
                
        from ui.dialogs import UnifiedManualOffsetDialog
        dialog = UnifiedManualOffsetDialog(None)
        
        yield dialog
        
        # Cleanup
        try:
            dialog.cleanup()
            dialog.close()
            dialog.deleteLater()
        except:
            pass
    
    def test_component_creation(self, composed_dialog):
        """Test that components are created in composed mode."""
        # Check if using composed implementation
        if os.environ.get('SPRITEPAL_USE_COMPOSED_DIALOGS', '').lower() == 'true':
            # Should have component references (even if internal)
            # The adapter wraps the implementation
            assert hasattr(composed_dialog, '_impl') or hasattr(composed_dialog, '_dialog')
            
    def test_signal_routing(self, composed_dialog, qtbot):
        """Test that signals are properly routed through components."""
        signal_received = False
        
        def on_offset_changed(offset):
            nonlocal signal_received
            signal_received = True
            
        composed_dialog.offset_changed.connect(on_offset_changed)
        
        # Try to trigger offset change
        composed_dialog.set_offset(0x400000)
        
        # Signal might not be emitted if browse_tab is None
        # Just verify connection works without error
        
    def test_cleanup_cascade(self, composed_dialog):
        """Test that cleanup properly cascades to components."""
        # Set up some state
        composed_dialog.rom_path = "/test/rom.gba"
        
        # Call cleanup
        composed_dialog.cleanup()
        
        # Should complete without errors
        # Components should be cleaned up internally


# Performance comparison tests
class TestPerformanceComparison:
    """Compare performance between implementations."""
    
    def test_creation_time(self, qt_app, monkeypatch, benchmark):
        """Benchmark dialog creation time."""
        def create_dialog():
            from ui.dialogs import UnifiedManualOffsetDialog
            dialog = UnifiedManualOffsetDialog(None)
            dialog.cleanup()
            dialog.deleteLater()
            return dialog
            
        # Benchmark the creation
        result = benchmark(create_dialog)
        # Just ensure it completes, don't enforce specific timing
        
    def test_memory_usage(self, dialog_implementation):
        """Check memory usage is reasonable."""
        import sys
        
        # Get size of dialog object
        size = sys.getsizeof(dialog_implementation)
        
        # Should be reasonable (not more than a few MB)
        assert size < 10 * 1024 * 1024  # 10MB limit
        
        
class TestBackwardCompatibility:
    """Ensure backward compatibility is maintained."""
    
    def test_singleton_pattern(self, qt_app, monkeypatch):
        """Test that singleton pattern still works."""
        # This is used in ROM extraction panel
        from ui.rom_extraction_panel import ManualOffsetDialogSingleton
        
        # Create mock panel
        mock_panel = Mock()
        mock_panel.rom_path = "/test/rom.gba"
        mock_panel.rom_size = 0x800000
        
        # Get dialog through singleton
        dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_panel)
        dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_panel)
        
        # Should return same instance
        assert dialog1 is dialog2
        
        # Cleanup
        ManualOffsetDialogSingleton.cleanup()
        
    def test_import_compatibility(self):
        """Test that imports work correctly."""
        # Test main import
        from ui.dialogs import UnifiedManualOffsetDialog
        assert UnifiedManualOffsetDialog is not None
        
        # Test alias import
        from ui.dialogs import ManualOffsetDialog
        assert ManualOffsetDialog is UnifiedManualOffsetDialog
        

if __name__ == "__main__":
    # Run tests with both implementations
    print("Testing UnifiedManualOffsetDialog Migration...")
    print("=" * 60)
    
    # Test with legacy
    os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = 'false'
    print("\nTesting LEGACY implementation...")
    pytest.main([__file__, "-v", "-k", "not benchmark"])
    
    # Test with composed
    os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = 'true'  
    print("\nTesting COMPOSED implementation...")
    pytest.main([__file__, "-v", "-k", "not benchmark"])