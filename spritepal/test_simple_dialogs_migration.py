#!/usr/bin/env python3
"""
Comprehensive test suite for simple dialogs migration.

This test suite validates the migration of SettingsDialog and UserErrorDialog
to support both legacy and composed implementations via feature flags.

Test Strategy:
- Test both implementations (legacy and composed) independently
- Verify feature flag system controls which implementation is used
- Test dialog creation, UI components, and functionality
- Compare behavior between implementations to ensure compatibility
- Use real Qt components when possible, fallback gracefully when Qt unavailable
- Provide comprehensive coverage reporting

Usage:
    pytest test_simple_dialogs_migration.py -v
    pytest test_simple_dialogs_migration.py -v --qt-log-level=DEBUG
    pytest test_simple_dialogs_migration.py -v -k "settings" # Only SettingsDialog tests
    pytest test_simple_dialogs_migration.py -v -k "error" # Only UserErrorDialog tests
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Test framework availability flags
HAS_QT = True
QT_IMPORT_ERROR = None
try:
    from PySide6.QtCore import Qt, QTimer, Signal
    from PySide6.QtWidgets import (
        QApplication, QDialog, QDialogButtonBox, QLabel, QLineEdit,
        QCheckBox, QSpinBox, QPushButton, QTabWidget, QStatusBar,
        QWidget, QVBoxLayout, QHBoxLayout, QMessageBox
    )
    from PySide6.QtTest import QTest
    
except ImportError as e:
    HAS_QT = False
    QT_IMPORT_ERROR = str(e)
    
    # Create mock Qt classes for import-only testing
    class MockQtClass:
        """Mock Qt class for testing without Qt"""
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, *args, **kwargs):
            return self
        def __getattr__(self, name):
            return MockQtClass()
    
    # Set up mock Qt classes
    for name in ['QApplication', 'QDialog', 'QDialogButtonBox', 'QLabel', 
                'QLineEdit', 'QCheckBox', 'QSpinBox', 'QPushButton', 'QTabWidget',
                'QStatusBar', 'QWidget', 'QVBoxLayout', 'QHBoxLayout', 'QMessageBox',
                'QTest', 'Qt', 'Signal']:
        globals()[name] = MockQtClass()


class DialogTestResult:
    """Store and track test results for comparison between implementations"""
    
    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
        self.errors: List[str] = []
        self.implementation_type = "unknown"
    
    def record_result(self, test_name: str, **kwargs):
        """Record a test result"""
        self.results[test_name] = kwargs
        
    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)
        
    def set_implementation(self, impl_type: str):
        """Set the implementation type being tested"""
        self.implementation_type = impl_type
    
    def has_errors(self) -> bool:
        """Check if any errors were recorded"""
        return len(self.errors) > 0
    
    def compare_with(self, other: 'DialogTestResult') -> List[str]:
        """Compare results with another test result instance"""
        differences = []
        
        # Compare result keys
        my_keys = set(self.results.keys())
        other_keys = set(other.results.keys())
        
        if my_keys != other_keys:
            missing_in_other = my_keys - other_keys
            missing_in_self = other_keys - my_keys
            if missing_in_other:
                differences.append(f"Tests in {self.implementation_type} but not {other.implementation_type}: {missing_in_other}")
            if missing_in_self:
                differences.append(f"Tests in {other.implementation_type} but not {self.implementation_type}: {missing_in_self}")
        
        # Compare specific test results
        for key in my_keys & other_keys:
            if self.results[key] != other.results[key]:
                differences.append(f"Different results for {key}: {self.implementation_type}={self.results[key]} vs {other.implementation_type}={other.results[key]}")
        
        return differences


class TestDialogMigrationFramework:
    """Base class providing common test infrastructure for dialog migration testing"""
    
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
        app.processEvents()
        for widget in app.allWidgets():
            widget.close()
            widget.deleteLater()
        app.processEvents()
    
    @pytest.fixture
    def legacy_implementation(self):
        """Force legacy dialog implementation"""
        # Set environment variable for this test
        original_value = os.environ.get("SPRITEPAL_USE_COMPOSED_DIALOGS", "0")
        os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = "0"
        
        yield "legacy"
        
        # Restore original value
        os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = original_value
    
    @pytest.fixture
    def composed_implementation(self):
        """Force composed dialog implementation"""
        # Set environment variable for this test  
        original_value = os.environ.get("SPRITEPAL_USE_COMPOSED_DIALOGS", "0")
        os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = "1"
        
        yield "composed"
        
        # Restore original value
        os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = original_value
    
    def safe_import_dialog_class(self, dialog_module: str, dialog_class: str):
        """Safely import dialog class with error handling"""
        try:
            module = __import__(dialog_module, fromlist=[dialog_class])
            return getattr(module, dialog_class)
        except ImportError as e:
            pytest.skip(f"Could not import {dialog_class} from {dialog_module}: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error importing {dialog_class}: {e}")
    
    def create_dialog_safely(self, dialog_class, *args, **kwargs):
        """Create dialog with comprehensive error handling"""
        try:
            dialog = dialog_class(*args, **kwargs)
            return dialog
        except Exception as e:
            if HAS_QT:
                pytest.fail(f"Failed to create {dialog_class.__name__}: {e}")
            else:
                # In mock mode, return a mock object
                return Mock(spec=dialog_class)


class TestFeatureFlagSystem(TestDialogMigrationFramework):
    """Test the feature flag system for dialog implementation selection"""
    
    def test_feature_flag_environment_variable(self):
        """Test that environment variable controls implementation selection"""
        # Import the selector module
        try:
            from utils.dialog_feature_flags import (
                get_dialog_implementation,
                set_dialog_implementation,
                is_composed_dialogs_enabled
            )
        except ImportError:
            pytest.skip("Feature flag utilities not available")
        
        # Test default (legacy)
        original_value = os.environ.get("SPRITEPAL_USE_COMPOSED_DIALOGS", "0")
        
        try:
            os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = "0"
            assert get_dialog_implementation() == "legacy"
            assert not is_composed_dialogs_enabled()
            
            os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = "1" 
            assert get_dialog_implementation() == "composed"
            assert is_composed_dialogs_enabled()
            
        finally:
            os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = original_value
    
    def test_set_implementation_function(self):
        """Test programmatic setting of implementation"""
        try:
            from utils.dialog_feature_flags import (
                set_dialog_implementation,
                get_dialog_implementation
            )
        except ImportError:
            pytest.skip("Feature flag utilities not available")
        
        original_value = os.environ.get("SPRITEPAL_USE_COMPOSED_DIALOGS", "0")
        
        try:
            set_dialog_implementation(True)
            assert get_dialog_implementation() == "composed"
            
            set_dialog_implementation(False) 
            assert get_dialog_implementation() == "legacy"
            
        finally:
            os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = original_value


class TestSettingsDialogMigration(TestDialogMigrationFramework):
    """Comprehensive tests for SettingsDialog migration"""
    
    def get_settings_dialog_class(self):
        """Get SettingsDialog class with error handling"""
        return self.safe_import_dialog_class(
            "ui.dialogs.settings_dialog", 
            "SettingsDialog"
        )
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_settings_dialog_legacy_creation(self, qt_app, legacy_implementation):
        """Test SettingsDialog creation with legacy implementation"""
        SettingsDialog = self.get_settings_dialog_class()
        result = DialogTestResult()
        result.set_implementation("legacy")
        
        try:
            dialog = self.create_dialog_safely(SettingsDialog, parent=None)
            
            # Test basic properties
            assert dialog is not None
            result.record_result("dialog_created", success=True)
            
            # Test title
            expected_title = "SpritePal Settings"
            if hasattr(dialog, 'windowTitle'):
                title = dialog.windowTitle()
                assert title == expected_title
                result.record_result("window_title", title=title)
            
            # Test modal property
            if hasattr(dialog, 'isModal'):
                assert dialog.isModal() == True
                result.record_result("modal", is_modal=True)
            
            # Cleanup
            if hasattr(dialog, 'close'):
                dialog.close()
            if hasattr(dialog, 'deleteLater'):
                dialog.deleteLater()
                
        except Exception as e:
            result.add_error(f"Legacy creation failed: {e}")
            raise
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")  
    def test_settings_dialog_composed_creation(self, qt_app, composed_implementation):
        """Test SettingsDialog creation with composed implementation"""
        SettingsDialog = self.get_settings_dialog_class()
        result = DialogTestResult()
        result.set_implementation("composed")
        
        try:
            dialog = self.create_dialog_safely(SettingsDialog, parent=None)
            
            # Test basic properties
            assert dialog is not None
            result.record_result("dialog_created", success=True)
            
            # Test title
            expected_title = "SpritePal Settings"
            if hasattr(dialog, 'windowTitle'):
                title = dialog.windowTitle()
                assert title == expected_title
                result.record_result("window_title", title=title)
            
            # Test modal property
            if hasattr(dialog, 'isModal'):
                assert dialog.isModal() == True
                result.record_result("modal", is_modal=True)
                
            # Test composed-specific features if available
            if hasattr(dialog, 'get_component'):
                components = []
                for comp_name in ['status_bar', 'button_box']:
                    comp = dialog.get_component(comp_name)
                    if comp is not None:
                        components.append(comp_name)
                result.record_result("composed_components", components=components)
            
            # Cleanup
            if hasattr(dialog, 'close'):
                dialog.close()
            if hasattr(dialog, 'deleteLater'):
                dialog.deleteLater()
                
        except Exception as e:
            result.add_error(f"Composed creation failed: {e}")
            raise
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_settings_dialog_tab_functionality(self, qt_app, legacy_implementation):
        """Test SettingsDialog tab creation and switching"""
        SettingsDialog = self.get_settings_dialog_class()
        
        dialog = self.create_dialog_safely(SettingsDialog, parent=None)
        
        try:
            # Test tab widget existence
            if hasattr(dialog, 'tab_widget'):
                tab_widget = dialog.tab_widget
                assert tab_widget is not None, "Tab widget should exist"
                
                if hasattr(tab_widget, 'count'):
                    tab_count = tab_widget.count()
                    assert tab_count == 2, f"Expected 2 tabs, got {tab_count}"
                
                # Test tab switching
                if hasattr(tab_widget, 'setCurrentIndex') and hasattr(tab_widget, 'currentIndex'):
                    tab_widget.setCurrentIndex(1)
                    assert tab_widget.currentIndex() == 1, "Tab switching should work"
                    
                    tab_widget.setCurrentIndex(0)
                    assert tab_widget.currentIndex() == 0, "Tab switching back should work"
            
        finally:
            if hasattr(dialog, 'close'):
                dialog.close()
            if hasattr(dialog, 'deleteLater'):
                dialog.deleteLater()
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_settings_dialog_components_exist(self, qt_app, legacy_implementation):
        """Test that all required SettingsDialog components exist"""
        SettingsDialog = self.get_settings_dialog_class()
        
        dialog = self.create_dialog_safely(SettingsDialog, parent=None)
        
        expected_components = [
            'tab_widget', 'restore_window_check', 'auto_save_session_check',
            'dumps_dir_edit', 'dumps_dir_button', 'cache_enabled_check',
            'cache_location_edit', 'cache_location_button', 'cache_size_spin',
            'cache_expiry_spin', 'auto_cleanup_check', 'show_indicators_check'
        ]
        
        try:
            missing_components = []
            for component in expected_components:
                if not hasattr(dialog, component) or getattr(dialog, component) is None:
                    missing_components.append(component)
            
            if missing_components:
                pytest.fail(f"Missing components: {missing_components}")
                
        finally:
            if hasattr(dialog, 'close'):
                dialog.close()
            if hasattr(dialog, 'deleteLater'):
                dialog.deleteLater()
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_settings_dialog_status_bar_functionality(self, qt_app, legacy_implementation):
        """Test SettingsDialog status bar functionality"""
        SettingsDialog = self.get_settings_dialog_class()
        
        dialog = self.create_dialog_safely(SettingsDialog, parent=None)
        
        try:
            # Test status bar exists
            if hasattr(dialog, 'status_bar'):
                status_bar = dialog.status_bar
                assert status_bar is not None, "Status bar should exist"
                
                # Test status message update
                if hasattr(status_bar, 'showMessage'):
                    test_message = "Test status message"
                    status_bar.showMessage(test_message)
                    # Note: Can't easily test the actual display without complex Qt event processing
                    
        finally:
            if hasattr(dialog, 'close'):
                dialog.close()
            if hasattr(dialog, 'deleteLater'):
                dialog.deleteLater()
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_settings_dialog_button_box_functionality(self, qt_app, legacy_implementation):
        """Test SettingsDialog button box functionality"""
        SettingsDialog = self.get_settings_dialog_class()
        
        dialog = self.create_dialog_safely(SettingsDialog, parent=None)
        
        try:
            # Test button box exists
            if hasattr(dialog, 'button_box'):
                button_box = dialog.button_box
                assert button_box is not None, "Button box should exist"
                
                # Test standard buttons
                if hasattr(button_box, 'standardButtons'):
                    std_buttons = button_box.standardButtons()
                    # Should have OK and Cancel buttons
                    ok_button = QDialogButtonBox.StandardButton.Ok if HAS_QT else None
                    cancel_button = QDialogButtonBox.StandardButton.Cancel if HAS_QT else None
                    
                    if ok_button and cancel_button:
                        assert std_buttons & ok_button, "Should have OK button"
                        assert std_buttons & cancel_button, "Should have Cancel button"
                
        finally:
            if hasattr(dialog, 'close'):
                dialog.close()
            if hasattr(dialog, 'deleteLater'):
                dialog.deleteLater()
    
    def test_settings_dialog_change_detection(self, qt_app, legacy_implementation):
        """Test settings change detection logic"""
        if not HAS_QT:
            pytest.skip("Qt not available")
            
        SettingsDialog = self.get_settings_dialog_class()
        
        dialog = self.create_dialog_safely(SettingsDialog, parent=None)
        
        try:
            # Test initial state (no changes)
            if hasattr(dialog, '_has_settings_changed'):
                assert not dialog._has_settings_changed(), "Initial state should show no changes"
            
            # Make a change
            if hasattr(dialog, 'restore_window_check'):
                original_state = dialog.restore_window_check.isChecked() if hasattr(dialog.restore_window_check, 'isChecked') else False
                new_state = not original_state
                
                if hasattr(dialog.restore_window_check, 'setChecked'):
                    dialog.restore_window_check.setChecked(new_state)
                
                # Check if change is detected
                if hasattr(dialog, '_has_settings_changed'):
                    assert dialog._has_settings_changed(), "Should detect setting changes"
                
                # Revert change
                if hasattr(dialog.restore_window_check, 'setChecked'):
                    dialog.restore_window_check.setChecked(original_state)
                
                # Should no longer detect changes
                if hasattr(dialog, '_has_settings_changed'):
                    assert not dialog._has_settings_changed(), "Should not detect changes after revert"
                
        finally:
            if hasattr(dialog, 'close'):
                dialog.close()
            if hasattr(dialog, 'deleteLater'):
                dialog.deleteLater()


class TestUserErrorDialogMigration(TestDialogMigrationFramework):
    """Comprehensive tests for UserErrorDialog migration"""
    
    def get_user_error_dialog_class(self):
        """Get UserErrorDialog class with error handling"""
        return self.safe_import_dialog_class(
            "ui.dialogs.user_error_dialog",
            "UserErrorDialog"
        )
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_user_error_dialog_legacy_creation(self, qt_app, legacy_implementation):
        """Test UserErrorDialog creation with legacy implementation"""
        UserErrorDialog = self.get_user_error_dialog_class()
        
        dialog = self.create_dialog_safely(
            UserErrorDialog, 
            "Test error message",
            "Technical details"
        )
        
        try:
            assert dialog is not None
            
            # Test modal behavior
            if hasattr(dialog, 'isModal'):
                assert dialog.isModal() == True
                
        finally:
            if hasattr(dialog, 'close'):
                dialog.close()
            if hasattr(dialog, 'deleteLater'):
                dialog.deleteLater()
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_user_error_dialog_composed_creation(self, qt_app, composed_implementation):
        """Test UserErrorDialog creation with composed implementation"""
        UserErrorDialog = self.get_user_error_dialog_class()
        
        dialog = self.create_dialog_safely(
            UserErrorDialog,
            "Test error message", 
            "Technical details"
        )
        
        try:
            assert dialog is not None
            
            # Test modal behavior
            if hasattr(dialog, 'isModal'):
                assert dialog.isModal() == True
                
        finally:
            if hasattr(dialog, 'close'):
                dialog.close()
            if hasattr(dialog, 'deleteLater'):
                dialog.deleteLater()
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_user_error_dialog_error_mapping(self, qt_app, legacy_implementation):
        """Test UserErrorDialog error message mapping"""
        UserErrorDialog = self.get_user_error_dialog_class()
        
        # Test known error types
        known_errors = [
            ("no hal compressed data", "Invalid Sprite Data"),
            ("file not found", "File Not Found"),
            ("permission denied", "Access Denied"),
            ("invalid rom", "Invalid ROM File"),
        ]
        
        for error_msg, expected_title in known_errors:
            dialog = self.create_dialog_safely(UserErrorDialog, error_msg)
            
            try:
                if hasattr(dialog, 'windowTitle'):
                    title = dialog.windowTitle()
                    assert title == expected_title, f"Expected title '{expected_title}' for error '{error_msg}', got '{title}'"
                    
            finally:
                if hasattr(dialog, 'close'):
                    dialog.close()
                if hasattr(dialog, 'deleteLater'):
                    dialog.deleteLater()
    
    @pytest.mark.skipif(not HAS_QT, reason="Qt not available")
    def test_user_error_dialog_details_toggle(self, qt_app, legacy_implementation):
        """Test UserErrorDialog details button functionality"""
        UserErrorDialog = self.get_user_error_dialog_class()
        
        dialog = self.create_dialog_safely(
            UserErrorDialog,
            "Test error with details",
            "Technical details here"
        )
        
        try:
            # Test details button exists
            if hasattr(dialog, 'details_button'):
                details_button = dialog.details_button
                assert details_button is not None, "Details button should exist"
                
                # Test initial state
                if hasattr(details_button, 'text'):
                    initial_text = details_button.text()
                    assert "Show" in initial_text, f"Initial button text should contain 'Show', got '{initial_text}'"
                
                # Test toggle functionality
                if hasattr(details_button, 'setChecked') and hasattr(details_button, 'text'):
                    details_button.setChecked(True)
                    toggled_text = details_button.text() 
                    assert "Hide" in toggled_text, f"Toggled button text should contain 'Hide', got '{toggled_text}'"
                
        finally:
            if hasattr(dialog, 'close'):
                dialog.close()
            if hasattr(dialog, 'deleteLater'):
                dialog.deleteLater()
    
    def test_user_error_dialog_static_method(self, qt_app, legacy_implementation):
        """Test UserErrorDialog static show_error method"""
        if not HAS_QT:
            pytest.skip("Qt not available")
            
        UserErrorDialog = self.get_user_error_dialog_class()
        
        # Test static method exists and can be called
        if hasattr(UserErrorDialog, 'show_error'):
            # This should not raise an exception
            # Note: In a real test environment, this would show a dialog
            # For automated testing, we'd need to mock or patch the dialog display
            try:
                with patch('PySide6.QtWidgets.QMessageBox.exec'):
                    UserErrorDialog.show_error(None, "test error", "technical details")
            except Exception as e:
                pytest.fail(f"Static show_error method failed: {e}")


class TestImplementationComparison(TestDialogMigrationFramework):
    """Test to compare behavior between legacy and composed implementations"""
    
    def test_settings_dialog_implementation_compatibility(self, qt_app):
        """Test that both implementations produce compatible results"""
        if not HAS_QT:
            pytest.skip("Qt not available")
            
        SettingsDialog = self.safe_import_dialog_class("ui.dialogs.settings_dialog", "SettingsDialog")
        
        # Test legacy implementation
        os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = "0"
        legacy_result = DialogTestResult()
        legacy_result.set_implementation("legacy")
        
        try:
            dialog = self.create_dialog_safely(SettingsDialog)
            
            # Record key properties
            legacy_result.record_result("tab_count", 
                count=dialog.tab_widget.count() if hasattr(dialog, 'tab_widget') and dialog.tab_widget else 0)
            legacy_result.record_result("has_status_bar", 
                has_bar=hasattr(dialog, 'status_bar') and dialog.status_bar is not None)
            legacy_result.record_result("has_button_box",
                has_box=hasattr(dialog, 'button_box') and dialog.button_box is not None)
                
            if hasattr(dialog, 'close'):
                dialog.close()
            if hasattr(dialog, 'deleteLater'):
                dialog.deleteLater()
                
        except Exception as e:
            legacy_result.add_error(f"Legacy test failed: {e}")
        
        # Test composed implementation  
        os.environ["SPRITEPAL_USE_COMPOSED_DIALOGS"] = "1"
        composed_result = DialogTestResult()
        composed_result.set_implementation("composed")
        
        try:
            dialog = self.create_dialog_safely(SettingsDialog)
            
            # Record key properties
            composed_result.record_result("tab_count",
                count=dialog.tab_widget.count() if hasattr(dialog, 'tab_widget') and dialog.tab_widget else 0)
            composed_result.record_result("has_status_bar",
                has_bar=hasattr(dialog, 'status_bar') and dialog.status_bar is not None)
            composed_result.record_result("has_button_box", 
                has_box=hasattr(dialog, 'button_box') and dialog.button_box is not None)
                
            if hasattr(dialog, 'close'):
                dialog.close()
            if hasattr(dialog, 'deleteLater'):
                dialog.deleteLater()
                
        except Exception as e:
            composed_result.add_error(f"Composed test failed: {e}")
        
        # Compare results
        differences = legacy_result.compare_with(composed_result)
        
        if differences:
            pytest.fail(f"Implementation differences detected: {differences}")
        
        # Check for errors
        if legacy_result.has_errors():
            pytest.fail(f"Legacy implementation errors: {legacy_result.errors}")
        if composed_result.has_errors():
            pytest.fail(f"Composed implementation errors: {composed_result.errors}")


class TestImportOnlyFallback:
    """Test imports work correctly even when Qt is not available"""
    
    def test_dialog_imports_without_qt(self):
        """Test that dialog classes can be imported even without Qt"""
        # This test specifically tests the import-only capability
        
        try:
            from ui.dialogs.settings_dialog import SettingsDialog
            assert SettingsDialog is not None, "SettingsDialog class should be importable"
            
        except ImportError as e:
            pytest.fail(f"Failed to import SettingsDialog: {e}")
        
        try:
            from ui.dialogs.user_error_dialog import UserErrorDialog
            assert UserErrorDialog is not None, "UserErrorDialog class should be importable"
            
        except ImportError as e:
            pytest.fail(f"Failed to import UserErrorDialog: {e}")
    
    def test_base_dialog_import_without_qt(self):
        """Test that BaseDialog can be imported without Qt"""
        try:
            from ui.components.base import BaseDialog
            assert BaseDialog is not None, "BaseDialog should be importable"
            
        except ImportError as e:
            # This might fail if Qt is required - that's acceptable
            pytest.skip(f"BaseDialog requires Qt: {e}")
    
    def test_feature_flag_utilities_import(self):
        """Test that feature flag utilities can be imported"""
        try:
            from utils.dialog_feature_flags import (
                get_dialog_implementation,
                set_dialog_implementation,
                is_composed_dialogs_enabled
            )
            
            # These should be callable even without Qt
            assert callable(get_dialog_implementation)
            assert callable(set_dialog_implementation)
            assert callable(is_composed_dialogs_enabled)
            
        except ImportError as e:
            pytest.fail(f"Failed to import feature flag utilities: {e}")


# Test summary and reporting functions
def pytest_runtest_setup(item):
    """pytest hook to set up each test"""
    if hasattr(item, 'function'):
        print(f"\n{'='*60}")
        print(f"Starting test: {item.function.__name__}")
        print(f"Description: {item.function.__doc__ or 'No description'}")
        print(f"Qt Available: {HAS_QT}")
        if not HAS_QT and QT_IMPORT_ERROR:
            print(f"Qt Import Error: {QT_IMPORT_ERROR}")
        print('='*60)


def pytest_runtest_teardown(item, nextitem):
    """pytest hook to clean up after each test"""
    if HAS_QT:
        app = QApplication.instance()
        if app:
            # Clean up any remaining widgets
            app.processEvents()
            for widget in app.allWidgets():
                if widget.isVisible():
                    widget.close()
                widget.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    """Run tests when executed directly"""
    import pytest
    
    print("Simple Dialogs Migration Test Suite")
    print("=" * 60)
    print(f"Qt Available: {HAS_QT}")
    if not HAS_QT:
        print(f"Qt Import Error: {QT_IMPORT_ERROR}")
        print("Running in import-only mode")
    print("=" * 60)
    
    # Run with verbose output and detailed reporting
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--no-header",
        "-x",  # Stop on first failure for easier debugging
    ])
    
    sys.exit(exit_code)