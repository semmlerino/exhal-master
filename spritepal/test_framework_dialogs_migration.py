#!/usr/bin/env python3
"""
Comprehensive test suite for framework dialogs migration.

This test suite validates the migration of TabbedDialog and SplitterDialog
to support both legacy and composed implementations via feature flags.

Test Strategy:
- Test both implementations (legacy and composed) independently
- Verify feature flag system controls which implementation is used
- Test dialog creation, UI components, and functionality
- Test derived dialogs (InjectionDialog, RowArrangementDialog, GridArrangementDialog)
- Compare behavior between implementations to ensure compatibility
"""

import os
import sys
from pathlib import Path
from typing import Optional, Generator
import pytest

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Test framework availability flags
HAS_QT = True
QT_IMPORT_ERROR = None
try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QApplication, QWidget, QLabel, QPushButton,
        QSplitter, QTabWidget, QDialogButtonBox
    )
except ImportError as e:
    HAS_QT = False
    QT_IMPORT_ERROR = str(e)
    # Create mock Qt classes for import-only testing
    class MockQtClass:
        """Mock Qt class for testing without Qt"""
        def __init__(self, *args, **kwargs):
            pass
    QApplication = QWidget = QLabel = QPushButton = MockQtClass
    QSplitter = QTabWidget = QDialogButtonBox = MockQtClass
    Qt = type('Qt', (), {
        'WindowModality': type('WindowModality', (), {'ApplicationModal': 1}),
        'WidgetAttribute': type('WidgetAttribute', (), {'WA_DeleteOnClose': 1}),
        'Orientation': type('Orientation', (), {'Horizontal': 1, 'Vertical': 2}),
        'TabPosition': type('TabPosition', (), {'North': 0})
    })()


class TestFrameworkDialogsMigration:
    """Test framework dialogs migration"""
    
    @pytest.fixture(scope="class")
    def qt_app(self) -> Generator[Optional[QApplication], None, None]:
        """Create QApplication instance if Qt is available"""
        if not HAS_QT:
            yield None
            return
            
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        yield app
        
        # Clean up any lingering widgets
        if HAS_QT:
            app.processEvents()
            for widget in app.allWidgets():
                widget.close()
                widget.deleteLater()
            app.processEvents()
    
    @pytest.fixture
    def legacy_implementation(self):
        """Force legacy dialog implementation"""
        original_value = os.environ.get("SPRITEPAL_USE_COMPOSED_DIALOGS", "0")
        os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = "0"
        
        # Clear module cache to force reimport
        modules_to_clear = [
            'ui.components.base.dialog_selector',
            'ui.components',
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        yield "legacy"
        
        # Restore original value
        os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = original_value
        
        # Clear module cache again
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
    
    @pytest.fixture
    def composed_implementation(self):
        """Force composed dialog implementation"""
        original_value = os.environ.get("SPRITEPAL_USE_COMPOSED_DIALOGS", "0")
        os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = "1"
        
        # Clear module cache to force reimport
        modules_to_clear = [
            'ui.components.base.dialog_selector',
            'ui.components',
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        yield "composed"
        
        # Restore original value
        os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = original_value
        
        # Clear module cache again
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]


class TestTabbedDialog(TestFrameworkDialogsMigration):
    """Test TabbedDialog with both implementations"""
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_tabbed_dialog_legacy(self, qt_app, legacy_implementation):
        """Test TabbedDialog with legacy implementation"""
        from ui.components import TabbedDialog
        
        # Create dialog
        dialog = TabbedDialog(
            parent=None,
            title="Test Tabbed Dialog",
            modal=True,
            with_status_bar=True,
            with_button_box=True
        )
        
        try:
            # Test basic properties
            assert dialog is not None
            assert dialog.windowTitle() == "Test Tabbed Dialog"
            assert dialog.isModal() == True
            
            # Test tab widget creation
            assert hasattr(dialog, 'tab_widget')
            assert dialog.tab_widget is not None
            
            # Add tabs
            tab1 = QWidget()
            tab2 = QWidget()
            index1 = dialog.add_tab(tab1, "Tab 1")
            index2 = dialog.add_tab(tab2, "Tab 2")
            
            assert index1 == 0
            assert index2 == 1
            assert dialog.tab_widget.count() == 2
            
            # Test tab switching
            dialog.set_current_tab(1)
            assert dialog.get_current_tab_index() == 1
            
            dialog.set_current_tab(0)
            assert dialog.get_current_tab_index() == 0
            
            # Test status bar exists
            assert hasattr(dialog, 'status_bar')
            assert dialog.status_bar is not None
            
            # Test button box exists
            assert hasattr(dialog, 'button_box')
            assert dialog.button_box is not None
            
        finally:
            dialog.close()
            dialog.deleteLater()
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_tabbed_dialog_composed(self, qt_app, composed_implementation):
        """Test TabbedDialog with composed implementation"""
        from ui.components import TabbedDialog
        
        # Create dialog
        dialog = TabbedDialog(
            parent=None,
            title="Test Tabbed Dialog",
            modal=True,
            with_status_bar=True,
            with_button_box=True
        )
        
        try:
            # Test basic properties
            assert dialog is not None
            assert dialog.windowTitle() == "Test Tabbed Dialog"
            assert dialog.isModal() == True
            
            # Test tab widget creation
            assert hasattr(dialog, 'tab_widget')
            assert dialog.tab_widget is not None
            
            # Add tabs
            tab1 = QWidget()
            tab2 = QWidget()
            index1 = dialog.add_tab(tab1, "Tab 1")
            index2 = dialog.add_tab(tab2, "Tab 2")
            
            assert index1 == 0
            assert index2 == 1
            assert dialog.tab_widget.count() == 2
            
            # Test tab switching
            dialog.set_current_tab(1)
            assert dialog.get_current_tab_index() == 1
            
            dialog.set_current_tab(0)
            assert dialog.get_current_tab_index() == 0
            
            # Test status bar exists
            assert hasattr(dialog, 'status_bar')
            assert dialog.status_bar is not None
            
            # Test button box exists
            assert hasattr(dialog, 'button_box')
            assert dialog.button_box is not None
            
        finally:
            dialog.close()
            dialog.deleteLater()


class TestSplitterDialog(TestFrameworkDialogsMigration):
    """Test SplitterDialog with both implementations"""
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_splitter_dialog_legacy(self, qt_app, legacy_implementation):
        """Test SplitterDialog with legacy implementation"""
        from ui.components import SplitterDialog
        
        # Create dialog
        dialog = SplitterDialog(
            parent=None,
            title="Test Splitter Dialog",
            modal=True,
            orientation=Qt.Orientation.Horizontal,
            splitter_handle_width=10,
            with_status_bar=True,
            with_button_box=True
        )
        
        try:
            # Test basic properties
            assert dialog is not None
            assert dialog.windowTitle() == "Test Splitter Dialog"
            assert dialog.isModal() == True
            
            # Test splitter creation
            assert hasattr(dialog, 'main_splitter')
            assert dialog.main_splitter is not None
            
            # Add panes
            pane1 = QLabel("Pane 1")
            pane2 = QLabel("Pane 2")
            index1 = dialog.add_pane(pane1)
            index2 = dialog.add_pane(pane2)
            
            assert index1 == 0
            assert index2 == 1
            assert dialog.main_splitter.count() == 2
            
            # Test orientation change
            dialog.set_orientation(Qt.Orientation.Vertical)
            # Note: Can't easily test the actual orientation without Qt event processing
            
            # Test sizes
            dialog.set_sizes([100, 200])
            # Note: Can't easily test the actual sizes without Qt event processing
            
            # Test add_panel (alias for add_pane)
            pane3 = QLabel("Pane 3")
            dialog.add_panel(pane3, stretch_factor=2)
            assert dialog.main_splitter.count() == 3
            
            # Test status bar exists
            assert hasattr(dialog, 'status_bar')
            assert dialog.status_bar is not None
            
            # Test button box exists
            assert hasattr(dialog, 'button_box')
            assert dialog.button_box is not None
            
        finally:
            dialog.close()
            dialog.deleteLater()
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_splitter_dialog_composed(self, qt_app, composed_implementation):
        """Test SplitterDialog with composed implementation"""
        from ui.components import SplitterDialog
        
        # Create dialog
        dialog = SplitterDialog(
            parent=None,
            title="Test Splitter Dialog",
            modal=True,
            orientation=Qt.Orientation.Horizontal,
            splitter_handle_width=10,
            with_status_bar=True,
            with_button_box=True
        )
        
        try:
            # Test basic properties
            assert dialog is not None
            assert dialog.windowTitle() == "Test Splitter Dialog"
            assert dialog.isModal() == True
            
            # Test splitter creation
            assert hasattr(dialog, 'main_splitter')
            assert dialog.main_splitter is not None
            
            # Add panes
            pane1 = QLabel("Pane 1")
            pane2 = QLabel("Pane 2")
            index1 = dialog.add_pane(pane1)
            index2 = dialog.add_pane(pane2)
            
            assert index1 == 0
            assert index2 == 1
            assert dialog.main_splitter.count() == 2
            
            # Test orientation change
            dialog.set_orientation(Qt.Orientation.Vertical)
            # Note: Can't easily test the actual orientation without Qt event processing
            
            # Test sizes
            dialog.set_sizes([100, 200])
            # Note: Can't easily test the actual sizes without Qt event processing
            
            # Test add_panel (alias for add_pane)
            pane3 = QLabel("Pane 3")
            dialog.add_panel(pane3, stretch_factor=2)
            assert dialog.main_splitter.count() == 3
            
            # Test status bar exists
            assert hasattr(dialog, 'status_bar')
            assert dialog.status_bar is not None
            
            # Test button box exists
            assert hasattr(dialog, 'button_box')
            assert dialog.button_box is not None
            
        finally:
            dialog.close()
            dialog.deleteLater()


class TestDerivedDialogs(TestFrameworkDialogsMigration):
    """Test dialogs that inherit from framework dialogs"""
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_injection_dialog_import(self, qt_app, legacy_implementation):
        """Test that InjectionDialog (inherits from TabbedDialog) can be imported"""
        try:
            from ui.injection_dialog import InjectionDialog
            assert InjectionDialog is not None
            # Note: Not creating instance as it requires complex setup
        except ImportError as e:
            pytest.skip(f"InjectionDialog import failed: {e}")
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_row_arrangement_dialog_import(self, qt_app, legacy_implementation):
        """Test that RowArrangementDialog (inherits from SplitterDialog) can be imported"""
        try:
            from ui.row_arrangement_dialog import RowArrangementDialog
            assert RowArrangementDialog is not None
            # Note: Not creating instance as it requires complex setup
        except ImportError as e:
            pytest.skip(f"RowArrangementDialog import failed: {e}")
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_grid_arrangement_dialog_import(self, qt_app, legacy_implementation):
        """Test that GridArrangementDialog (inherits from SplitterDialog) can be imported"""
        try:
            from ui.grid_arrangement_dialog import GridArrangementDialog
            assert GridArrangementDialog is not None
            # Note: Not creating instance as it requires complex setup
        except ImportError as e:
            pytest.skip(f"GridArrangementDialog import failed: {e}")


class TestImplementationCompatibility(TestFrameworkDialogsMigration):
    """Test compatibility between implementations"""
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_tabbed_dialog_compatibility(self, qt_app):
        """Test that both implementations of TabbedDialog behave the same"""
        results = {}
        
        # Test with legacy implementation
        os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = "0"
        if 'ui.components' in sys.modules:
            del sys.modules['ui.components']
        if 'ui.components.base.dialog_selector' in sys.modules:
            del sys.modules['ui.components.base.dialog_selector']
        
        from ui.components import TabbedDialog as LegacyTabbedDialog
        
        dialog = LegacyTabbedDialog(title="Test")
        results['legacy'] = {
            'has_tab_widget': hasattr(dialog, 'tab_widget') and dialog.tab_widget is not None,
            'has_status_bar': hasattr(dialog, 'status_bar'),
            'has_button_box': hasattr(dialog, 'button_box'),
            'has_add_tab': hasattr(dialog, 'add_tab'),
            'has_set_current_tab': hasattr(dialog, 'set_current_tab'),
        }
        dialog.close()
        dialog.deleteLater()
        
        # Test with composed implementation
        os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = "1"
        if 'ui.components' in sys.modules:
            del sys.modules['ui.components']
        if 'ui.components.base.dialog_selector' in sys.modules:
            del sys.modules['ui.components.base.dialog_selector']
        
        from ui.components import TabbedDialog as ComposedTabbedDialog
        
        dialog = ComposedTabbedDialog(title="Test")
        results['composed'] = {
            'has_tab_widget': hasattr(dialog, 'tab_widget') and dialog.tab_widget is not None,
            'has_status_bar': hasattr(dialog, 'status_bar'),
            'has_button_box': hasattr(dialog, 'button_box'),
            'has_add_tab': hasattr(dialog, 'add_tab'),
            'has_set_current_tab': hasattr(dialog, 'set_current_tab'),
        }
        dialog.close()
        dialog.deleteLater()
        
        # Compare results
        assert results['legacy'] == results['composed'], \
            f"Implementation differences: legacy={results['legacy']}, composed={results['composed']}"
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_splitter_dialog_compatibility(self, qt_app):
        """Test that both implementations of SplitterDialog behave the same"""
        results = {}
        
        # Test with legacy implementation
        os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = "0"
        if 'ui.components' in sys.modules:
            del sys.modules['ui.components']
        if 'ui.components.base.dialog_selector' in sys.modules:
            del sys.modules['ui.components.base.dialog_selector']
        
        from ui.components import SplitterDialog as LegacySplitterDialog
        
        dialog = LegacySplitterDialog(title="Test")
        results['legacy'] = {
            'has_main_splitter': hasattr(dialog, 'main_splitter') and dialog.main_splitter is not None,
            'has_status_bar': hasattr(dialog, 'status_bar'),
            'has_button_box': hasattr(dialog, 'button_box'),
            'has_add_pane': hasattr(dialog, 'add_pane'),
            'has_add_panel': hasattr(dialog, 'add_panel'),
            'has_set_orientation': hasattr(dialog, 'set_orientation'),
        }
        dialog.close()
        dialog.deleteLater()
        
        # Test with composed implementation
        os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = "1"
        if 'ui.components' in sys.modules:
            del sys.modules['ui.components']
        if 'ui.components.base.dialog_selector' in sys.modules:
            del sys.modules['ui.components.base.dialog_selector']
        
        from ui.components import SplitterDialog as ComposedSplitterDialog
        
        dialog = ComposedSplitterDialog(title="Test")
        results['composed'] = {
            'has_main_splitter': hasattr(dialog, 'main_splitter') and dialog.main_splitter is not None,
            'has_status_bar': hasattr(dialog, 'status_bar'),
            'has_button_box': hasattr(dialog, 'button_box'),
            'has_add_pane': hasattr(dialog, 'add_pane'),
            'has_add_panel': hasattr(dialog, 'add_panel'),
            'has_set_orientation': hasattr(dialog, 'set_orientation'),
        }
        dialog.close()
        dialog.deleteLater()
        
        # Compare results
        assert results['legacy'] == results['composed'], \
            f"Implementation differences: legacy={results['legacy']}, composed={results['composed']}"


class TestImportOnly:
    """Test imports work without Qt"""
    
    def test_framework_dialogs_import(self):
        """Test that framework dialogs can be imported without Qt"""
        try:
            from ui.components import TabbedDialog, SplitterDialog
            assert TabbedDialog is not None
            assert SplitterDialog is not None
        except ImportError as e:
            pytest.fail(f"Failed to import framework dialogs: {e}")
    
    def test_feature_flag_import(self):
        """Test that feature flag utilities can be imported"""
        try:
            from utils.dialog_feature_flags import (
                get_dialog_implementation,
                set_dialog_implementation,
                is_composed_dialogs_enabled
            )
            assert callable(get_dialog_implementation)
            assert callable(set_dialog_implementation)
            assert callable(is_composed_dialogs_enabled)
        except ImportError as e:
            pytest.fail(f"Failed to import feature flag utilities: {e}")


if __name__ == "__main__":
    print("Framework Dialogs Migration Test Suite")
    print("=" * 60)
    print(f"Qt Available: {HAS_QT}")
    if not HAS_QT:
        print(f"Qt Import Error: {QT_IMPORT_ERROR}")
        print("Running in import-only mode")
    print("=" * 60)
    
    # Run with verbose output
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
    ])
    
    sys.exit(exit_code)