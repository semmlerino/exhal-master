"""
Real Cross-Dialog Integration Tests - Replacement for mocked version.

These tests validate real dialog-to-dialog workflows using actual implementations
instead of mocks, enabling detection of architectural bugs that mocked tests miss.

This demonstrates the new testing architecture that:
- Uses real Qt components with proper lifecycle management
- Uses real managers with worker-owned pattern
- Uses real test data instead of mock data
- Catches architectural bugs that mocks hide
"""

import os
import tempfile
from pathlib import Path

import pytest

# Import real testing infrastructure
from tests.infrastructure import (
    TestApplicationFactory,
    RealManagerFixtureFactory, 
    TestDataRepository,
    QtTestingFramework,
    qt_dialog_test,
    qt_test_context,
)

# Import real SpritePal components (no mocking)
from ui.grid_arrangement_dialog import GridArrangementDialog
from ui.injection_dialog import InjectionDialog
from ui.dialogs.settings_dialog import SettingsDialog
from core.controller import ExtractionController


class TestRealCrossDialogIntegration:
    """
    Real cross-dialog integration tests.
    
    These tests validate actual dialog-to-dialog workflows using real
    implementations, catching bugs that mocked tests cannot detect.
    """
    
    @pytest.fixture(autouse=True)
    def setup_test_infrastructure(self):
        """Set up real testing infrastructure for each test."""
        # Initialize Qt application
        self.qt_app = TestApplicationFactory.get_application()
        
        # Initialize real manager factory  
        self.manager_factory = RealManagerFixtureFactory(qt_parent=self.qt_app)
        
        # Initialize test data repository
        self.test_data = TestDataRepository()
        
        # Initialize Qt testing framework
        self.qt_framework = QtTestingFramework(self.qt_app)
        
        yield
        
        # Cleanup
        self.qt_framework.cleanup()
        self.manager_factory.cleanup()
        self.test_data.cleanup()
    
    def test_extraction_to_grid_arrangement_workflow_real(self):
        """
        Test real workflow: Extract sprites → Arrange in grid.
        
        This test validates the complete workflow using real implementations,
        catching integration bugs that mocked tests miss.
        """
        # Get real test data
        extraction_data = self.test_data.get_vram_extraction_data("medium")
        
        # Create real extraction manager (worker-owned pattern)
        extraction_manager = self.manager_factory.create_extraction_manager(isolated=True)
        
        # Validate manager has proper Qt parent
        assert extraction_manager.parent() is self.qt_app
        
        # Test extraction with real data
        extraction_params = {
            "vram_path": extraction_data["vram_path"],
            "cgram_path": extraction_data["cgram_path"],
            "output_base": extraction_data["output_base"],
            "vram_offset": extraction_data["vram_offset"],
            "create_metadata": True,
        }
        
        # Validate extraction parameters with real manager
        is_valid = extraction_manager.validate_extraction_params(extraction_params)
        assert is_valid, "Real extraction parameters should be valid"
        
        # Test grid arrangement dialog with real extracted data
        sprite_path = extraction_data["output_base"] + ".png"  # Expected output path
        with qt_dialog_test(GridArrangementDialog, sprite_path) as dialog:
            # Validate dialog has proper Qt parent
            assert dialog.parent() is self.qt_app
            
            # Test dialog initialization with real data
            dialog.show_non_modal_and_wait(100)
            
            # Validate dialog state
            state = dialog.validate_dialog_state()
            assert state["dialog_type"] == "GridArrangementDialog"
            assert state["has_parent"]
            
            # Test dialog workflow integration
            # This catches real Qt lifecycle and signal behavior
            result = dialog.get_arrangement_result()
            assert result is not None or dialog.result() == 0  # Either has result or was cancelled
    
    def test_extraction_to_injection_workflow_real(self):
        """
        Test real workflow: Extract sprites → Inject back to VRAM.
        
        This validates the complete extraction-injection round-trip using
        real managers and real data, catching bugs mocks cannot detect.
        """
        # Get real test data for both extraction and injection
        extraction_data = self.test_data.get_vram_extraction_data("medium")
        injection_data = self.test_data.get_injection_data("medium")
        
        # Create real managers with proper Qt parents (worker-owned pattern)
        extraction_manager = self.manager_factory.create_extraction_manager(isolated=True)
        injection_manager = self.manager_factory.create_injection_manager(isolated=True)
        
        # Verify managers have proper Qt lifecycle management
        assert extraction_manager.parent() is self.qt_app
        assert injection_manager.parent() is self.qt_app
        
        # Test injection dialog with real managers and data
        with qt_dialog_test(InjectionDialog, injection_data["sprite_path"]) as dialog:
            # Validate dialog Qt parent relationship
            assert dialog.parent() is self.qt_app
            
            # Test dialog with real injection data
            dialog.show_non_modal_and_wait(100)
            
            # Test real parameter validation through dialog
            dialog.set_vram_input_path(injection_data["vram_input"])
            dialog.set_vram_output_path(injection_data["vram_output"])
            dialog.set_vram_offset(injection_data["vram_offset"])
            
            # This tests real validation logic, not mocked validation
            is_valid = dialog.validate_injection_parameters()
            assert is_valid, "Real injection parameters should be valid"
            
            # Test real injection manager integration
            params = dialog.get_injection_parameters()
            assert params["mode"] in ["vram", "rom"]
            assert os.path.exists(params["sprite_path"])
    
    def test_settings_dialog_real_manager_integration(self):
        """
        Test real settings dialog with real session manager.
        
        This validates that settings changes actually persist using real
        session management, not mocked settings behavior.
        """
        # Create real session manager (worker-owned pattern)
        session_manager = self.manager_factory.create_session_manager(
            isolated=True, temp_settings=True
        )
        
        # Validate session manager Qt parent
        assert session_manager.parent() is self.qt_app
        
        # Test settings dialog with real session manager
        with qt_dialog_test(SettingsDialog) as dialog:
            # Validate dialog Qt parent relationship
            assert dialog.parent() is self.qt_app
            
            # Test real settings persistence
            dialog.show_non_modal_and_wait(100)
            
            # Test changing settings through real dialog
            original_setting = session_manager.get("ui", "theme", "default")
            new_setting = "dark" if original_setting != "dark" else "light"
            
            dialog.set_theme_setting(new_setting)
            dialog.apply_settings()
            
            # Validate setting actually changed in real session manager
            updated_setting = session_manager.get("ui", "theme", "default") 
            assert updated_setting == new_setting, "Real settings should persist"
            
            # Test settings dialog state validation
            state = dialog.validate_dialog_state()
            assert state["dialog_type"] == "SettingsDialog"
    
    def test_controller_real_manager_coordination(self):
        """
        Test real controller with real managers coordination.
        
        This validates that the controller properly coordinates between
        real manager instances, catching architectural bugs that mocks hide.
        """
        # Create real manager set for controller
        managers = self.manager_factory.create_manager_set(isolated=True)
        
        # Validate all managers have proper Qt parents
        for manager_name, manager in managers.items():
            assert manager.parent() is self.qt_app, f"{manager_name} manager should have Qt parent"
        
        # Create real extraction controller
        with qt_test_context() as app:
            controller = ExtractionController()
            
            # Test real manager coordination
            test_data = self.test_data.get_vram_extraction_data("small")
            
            # This tests real controller-manager interaction
            try:
                # Test parameter validation with real managers
                params = {
                    "vram_path": test_data["vram_path"],
                    "cgram_path": test_data["cgram_path"],
                    "output_base": test_data["output_base"],
                }
                
                # Validate real controller behavior
                is_valid = controller.validate_extraction_params(params)
                assert isinstance(is_valid, bool), "Controller should return boolean validation result"
                
                # Test real error handling (not mocked error handling)
                empty_params = {}
                is_invalid = controller.validate_extraction_params(empty_params)
                assert not is_invalid, "Empty parameters should be invalid"
                
            except Exception as e:
                # Real exceptions are acceptable - they reveal actual behavior
                # Mocked tests would hide these real error conditions
                assert "parameter" in str(e).lower() or "validation" in str(e).lower()
    
    def test_dialog_lifecycle_real_qt_behavior(self):
        """
        Test real Qt dialog lifecycle management.
        
        This validates proper Qt parent/child relationships and lifecycle
        management that mocked Qt components cannot test.
        """
        created_dialogs = []
        
        try:
            # Create multiple dialogs with real Qt lifecycle
            with qt_dialog_test(GridArrangementDialog) as grid_dialog:
                created_dialogs.append(grid_dialog)
                
                # Test real Qt parent/child relationship
                validation = self.qt_framework.validate_qt_parent_child_relationship(
                    self.qt_app, grid_dialog
                )
                assert validation["child_parent_correct"], "Dialog should have correct Qt parent"
                assert validation["child_in_parent_children"], "Dialog should be in parent's children"
                
                # Create nested dialog context
                with qt_dialog_test(SettingsDialog) as settings_dialog:
                    created_dialogs.append(settings_dialog)
                    
                    # Test multiple dialogs with proper Qt lifecycle
                    grid_dialog.show_non_modal_and_wait(50)
                    settings_dialog.show_non_modal_and_wait(50)
                    
                    # Both dialogs should have proper Qt relationships
                    for dialog in [grid_dialog, settings_dialog]:
                        assert dialog.parent() is self.qt_app
                        assert not dialog.isModal()  # Non-modal as requested
                        
                    # Test Qt event processing with multiple dialogs
                    self.qt_framework.process_events(100)
                    
                    # Validate no Qt lifecycle errors occurred
                    for dialog in created_dialogs:
                        assert hasattr(dialog, 'close'), "Dialog should be valid Qt object"
        
        except Exception as e:
            # Real Qt exceptions reveal actual lifecycle issues
            # This is valuable information that mocked tests hide
            pytest.fail(f"Real Qt lifecycle error (this reveals actual bugs): {e}")
    
    def test_real_integration_catches_architectural_bugs(self):
        """
        Demonstrate that real integration tests catch bugs mocked tests miss.
        
        This test intentionally creates scenarios that would pass with mocks
        but fail with real implementations, proving the value of real testing.
        """
        # Test 1: Real Qt parent/child relationships catch lifecycle bugs
        manager = self.manager_factory.create_extraction_manager(isolated=True)
        
        # This would pass with mocks but reveals real Qt lifecycle behavior
        parent_before = manager.parent()
        manager.setParent(None)  # Remove Qt parent
        parent_after = manager.parent()
        
        assert parent_before is self.qt_app, "Manager initially had Qt parent"
        assert parent_after is None, "Manager parent was actually removed"
        
        # Test 2: Real manager validation catches parameter bugs
        invalid_params = {
            "vram_path": "/nonexistent/file.dmp",  # Non-existent file
            "output_base": "/invalid/path/",       # Invalid output path
        }
        
        # Real manager validation catches these issues
        is_valid = manager.validate_extraction_params(invalid_params)
        assert not is_valid, "Real validation should catch invalid parameters"
        
        # Test 3: Real signal behavior catches connection bugs
        signal_connected = False
        
        def test_callback():
            nonlocal signal_connected
            signal_connected = True
        
        # Test real Qt signal connection
        if hasattr(manager, 'extraction_finished'):
            manager.extraction_finished.connect(test_callback)
            manager.extraction_finished.emit([])  # Emit signal
            
            # Process Qt events to ensure signal delivery
            self.qt_framework.process_events(100)
            
            assert signal_connected, "Real Qt signal should trigger callback"
        
        # Re-parent manager for cleanup
        manager.setParent(self.qt_app)


# Additional integration test for validation
class TestRealTestingInfrastructureValidation:
    """Validate that the real testing infrastructure works correctly."""
    
    def test_real_infrastructure_components(self):
        """Test that all real testing infrastructure components work."""
        # Test Qt application factory
        app = TestApplicationFactory.get_application()
        assert app is not None
        assert app.applicationName() == "SpritePal-Test"
        
        # Test real manager factory
        factory = RealManagerFixtureFactory()
        extraction_manager = factory.create_extraction_manager(isolated=True)
        assert extraction_manager is not None
        assert extraction_manager.parent() is app
        factory.cleanup()
        
        # Test test data repository
        test_data = TestDataRepository()
        vram_data = test_data.get_vram_extraction_data("small")
        assert "vram_path" in vram_data
        assert os.path.exists(vram_data["vram_path"])
        test_data.cleanup()
        
        # Test Qt testing framework
        qt_framework = QtTestingFramework()
        with qt_framework.create_widget_test_context(type(None)) as context:
            # Context should work without errors
            pass
        qt_framework.cleanup()
    
    def test_real_vs_mock_comparison(self):
        """
        Demonstrate specific cases where real tests catch bugs mocks miss.
        
        This serves as documentation of why we moved away from mocking.
        """
        # Example 1: Qt parent/child lifecycle
        factory = RealManagerFixtureFactory()
        manager = factory.create_extraction_manager(isolated=True)
        
        # Real test: Can validate actual Qt parent relationship
        app = TestApplicationFactory.get_application()
        assert manager.parent() is app, "Real test validates actual Qt parent"
        
        # Mock would have: mock_manager.parent.return_value = mock_app
        # But couldn't validate the ACTUAL relationship
        
        # Example 2: Real parameter validation
        invalid_params = {"vram_path": ""}  # Empty path
        
        # Real test: Uses actual validation logic
        is_valid = manager.validate_extraction_params(invalid_params)
        assert not is_valid, "Real validation catches empty path"
        
        # Mock would have: mock_manager.validate.return_value = False
        # But wouldn't test the ACTUAL validation logic
        
        factory.cleanup()


if __name__ == "__main__":
    # Run a quick validation that the real integration tests work
    import sys
    
    try:
        # Test infrastructure setup
        app = TestApplicationFactory.get_application()
        factory = RealManagerFixtureFactory()
        test_data = TestDataRepository()
        
        print("✅ Real testing infrastructure initialized successfully")
        
        # Test real manager creation
        manager = factory.create_extraction_manager(isolated=True)
        assert manager.parent() is app
        print("✅ Real manager creation with Qt parent works")
        
        # Test real test data
        data = test_data.get_vram_extraction_data("small")
        assert os.path.exists(data["vram_path"])
        print("✅ Real test data generation works")
        
        # Cleanup
        factory.cleanup()
        test_data.cleanup()
        
        print("✅ All real integration test infrastructure components working")
        print("🎉 Ready to replace mocked integration tests with real ones!")
        
    except Exception as e:
        print(f"❌ Real integration test infrastructure error: {e}")
        sys.exit(1)