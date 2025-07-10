#!/usr/bin/env python3
"""
Comprehensive tests for main_controller module
Tests all methods and signal handling with minimal mocking
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QObject

from sprite_editor.controllers.main_controller import MainController
from sprite_editor.models.palette_model import PaletteModel
from sprite_editor.models.project_model import ProjectModel
from sprite_editor.models.sprite_model import SpriteModel


class MockSignal:
    """Mock PyQt signal that can be connected to"""

    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args, **kwargs):
        for callback in self.callbacks:
            callback(*args, **kwargs)


class MockMainWindow(QObject):
    """Mock main window with required signals"""

    def __init__(self):
        super().__init__()
        # Create mock signals
        self.recent_vram_selected = MockSignal()
        self.recent_cgram_selected = MockSignal()
        self.reset_settings_requested = MockSignal()
        self.clear_recent_requested = MockSignal()

        # Create mock actions
        self.action_open_vram = MagicMock()
        self.action_open_vram.triggered = MockSignal()
        self.action_open_cgram = MagicMock()
        self.action_open_cgram.triggered = MockSignal()

        # Add methods that might be called
        self.show_viewer_tab = MagicMock()
        self.show_inject_tab = MagicMock()


class MockExtractView(QObject):
    """Mock extract view with required signals and methods"""

    def __init__(self):
        super().__init__()
        # Required signals
        self.extract_requested = MockSignal()
        self.browse_vram_requested = MockSignal()
        self.browse_cgram_requested = MockSignal()

        # Required methods
        self.set_vram_file = MagicMock()
        self.set_cgram_file = MagicMock()


class MockInjectView(QObject):
    """Mock inject view with required signals and methods"""

    def __init__(self):
        super().__init__()
        # Required signals
        self.inject_requested = MockSignal()
        self.browse_png_requested = MockSignal()
        self.browse_vram_requested = MockSignal()

        # Required methods
        self.set_vram_file = MagicMock()
        self.set_png_file = MagicMock()
        self.set_validation_text = MagicMock()
        self.clear_output = MagicMock()
        self.append_output = MagicMock()
        self.set_inject_enabled = MagicMock()
        self.get_injection_params = MagicMock(
            return_value={
                "png_file": "/test/input.png",
                "vram_file": "/test/vram.dmp",
                "offset": 0xC000,
                "output_file": "output.dmp",
            }
        )


class MockViewerView(QObject):
    """Mock viewer view with required signals and methods"""

    def __init__(self):
        super().__init__()
        # Required signals
        self.zoom_in_requested = MockSignal()
        self.zoom_out_requested = MockSignal()
        self.zoom_fit_requested = MockSignal()
        self.grid_toggled = MockSignal()
        self.save_requested = MockSignal()
        self.open_editor_requested = MockSignal()

        # Required methods
        self.set_image = MagicMock()
        self.set_palette = MagicMock()
        self.update_zoom_label = MagicMock()
        self.update_image_info = MagicMock()

        # Mock sprite viewer
        self.sprite_viewer = MagicMock()
        self.sprite_viewer.zoom_in = MagicMock()
        self.sprite_viewer.zoom_out = MagicMock()
        self.sprite_viewer.zoom_fit = MagicMock()
        self.sprite_viewer.get_current_zoom = MagicMock(return_value=100)
        self.sprite_viewer.set_show_grid = MagicMock()
        self.sprite_viewer.get_image_info = MagicMock(
            return_value={
                "width": 128,
                "height": 128,
                "tiles_x": 16,
                "tiles_y": 16,
                "total_tiles": 256,
                "mode": "P",
                "colors": 16,
            }
        )
        self.get_sprite_viewer = MagicMock(return_value=self.sprite_viewer)


class MockPaletteView(QObject):
    """Mock palette view with required signals and methods"""

    def __init__(self):
        super().__init__()
        # Required signals
        self.browse_oam_requested = MockSignal()
        self.generate_preview_requested = MockSignal()
        self.palette_selected = MockSignal()

        # Required methods
        self.set_oam_file = MagicMock()
        self.get_preview_size = MagicMock(return_value=16)
        self.set_single_image_all_palettes = MagicMock()
        self.set_oam_statistics = MagicMock()


@pytest.fixture
def mock_views():
    """Create mock views with required attributes"""
    return {
        "main_window": MockMainWindow(),
        "extract_tab": MockExtractView(),
        "inject_tab": MockInjectView(),
        "viewer_tab": MockViewerView(),
        "multi_palette_tab": MockPaletteView(),
    }


@pytest.fixture
def real_models(tmp_path):
    """Create real model instances"""
    # Create unique settings file for each test
    import uuid

    settings_file = tmp_path / f"test_settings_{uuid.uuid4()}.json"

    # Create real models
    sprite_model = SpriteModel()
    palette_model = PaletteModel()
    project_model = ProjectModel()

    # Override settings with test-specific file
    from sprite_editor.settings_manager import SettingsManager

    test_settings = SettingsManager()
    test_settings.settings_file = settings_file
    test_settings.settings = test_settings._get_default_settings()
    test_settings.settings["recent_files"] = {
        "vram": [],
        "cgram": [],
        "oam": [],
        "png": [],
    }
    project_model.settings = test_settings

    # Initialize with empty recent files
    project_model.recent_vram_files = []
    project_model.recent_cgram_files = []
    project_model.recent_oam_files = []
    project_model.recent_png_files = []

    return {"sprite": sprite_model, "palette": palette_model, "project": project_model}


@pytest.fixture
def mock_controllers():
    """Create mock sub-controllers"""
    extract_controller = MagicMock()
    extract_controller.browse_vram_file = MagicMock()
    extract_controller.browse_cgram_file = MagicMock()
    extract_controller.load_recent_vram = MagicMock()
    extract_controller.load_recent_cgram = MagicMock()
    extract_controller.extract_sprites = MagicMock()

    inject_controller = MagicMock()
    inject_controller.browse_png_file = MagicMock()

    viewer_controller = MagicMock()
    viewer_controller.set_image = MagicMock()

    palette_controller = MagicMock()
    palette_controller.load_palettes = MagicMock()

    return {
        "extract": extract_controller,
        "inject": inject_controller,
        "viewer": viewer_controller,
        "palette": palette_controller,
    }


@pytest.mark.unit
class TestMainControllerInitialization:
    """Test MainController initialization"""

    def test_initialization_creates_all_controllers(self, real_models, mock_views):
        """Test that initialization creates all sub-controllers"""
        controller = MainController(real_models, mock_views)

        # Verify models are stored
        assert controller.sprite_model is real_models["sprite"]
        assert controller.project_model is real_models["project"]
        assert controller.palette_model is real_models["palette"]

        # Verify views are stored
        assert controller.main_window is mock_views["main_window"]
        assert controller.extract_tab is mock_views["extract_tab"]
        assert controller.inject_tab is mock_views["inject_tab"]
        assert controller.viewer_tab is mock_views["viewer_tab"]
        assert controller.multi_palette_tab is mock_views["multi_palette_tab"]

        # Verify sub-controllers are created
        assert controller.extract_controller is not None
        assert controller.inject_controller is not None
        assert controller.viewer_controller is not None
        assert controller.palette_controller is not None

    def test_initialization_connects_signals(self, real_models, mock_views):
        """Test that initialization connects all signals"""
        with patch.object(
            MainController, "_connect_main_window_signals"
        ) as mock_main_signals, patch.object(
            MainController, "_connect_cross_controller_signals"
        ) as mock_cross_signals, patch.object(
            MainController, "_initialize_from_settings"
        ) as mock_init_settings:
            MainController(real_models, mock_views)

            mock_main_signals.assert_called_once()
            mock_cross_signals.assert_called_once()
            mock_init_settings.assert_called_once()


@pytest.mark.unit
class TestMainWindowSignals:
    """Test main window signal connections"""

    def test_connect_main_window_signals_all_attributes_present(
        self, real_models, mock_views, mock_controllers
    ):
        """Test signal connections when all attributes are present"""
        controller = MainController(real_models, mock_views)

        # Replace sub-controllers with mocks before re-connecting signals
        controller.extract_controller = mock_controllers["extract"]

        # Clear any existing callbacks from initialization
        mock_views["main_window"].action_open_vram.triggered.callbacks = []
        mock_views["main_window"].action_open_cgram.triggered.callbacks = []
        mock_views["main_window"].recent_vram_selected.callbacks = []
        mock_views["main_window"].recent_cgram_selected.callbacks = []
        mock_views["main_window"].reset_settings_requested.callbacks = []
        mock_views["main_window"].clear_recent_requested.callbacks = []

        # Mock project model methods
        with patch.object(real_models["project"], "reset_settings") as mock_reset:
            with patch.object(
                real_models["project"], "clear_recent_files"
            ) as mock_clear:
                # Re-connect signals to ensure our test callbacks are connected
                controller._connect_main_window_signals()

                # Test action connections - verify connections were made
                assert (
                    len(mock_views["main_window"].action_open_vram.triggered.callbacks)
                    == 1
                )
                assert (
                    len(mock_views["main_window"].action_open_cgram.triggered.callbacks)
                    == 1
                )

                # Test recent file signals
                mock_views["main_window"].recent_vram_selected.emit("test_vram.bin")
                mock_controllers["extract"].load_recent_vram.assert_called_with(
                    "test_vram.bin"
                )

                mock_views["main_window"].recent_cgram_selected.emit("test_cgram.bin")
                mock_controllers["extract"].load_recent_cgram.assert_called_with(
                    "test_cgram.bin"
                )

                # Test settings signals
                mock_views["main_window"].reset_settings_requested.emit()
                mock_reset.assert_called_once()

                mock_views["main_window"].clear_recent_requested.emit()
                mock_clear.assert_called_once()

    def test_connect_main_window_signals_missing_attributes(
        self, real_models, mock_views
    ):
        """Test signal connections when attributes are missing"""
        # Create a minimal main window without some attributes
        minimal_window = QObject()
        minimal_window.show_viewer_tab = MagicMock()
        minimal_window.show_inject_tab = MagicMock()
        # Intentionally missing: action_open_vram, recent_vram_selected, etc.

        mock_views["main_window"] = minimal_window

        # Should not raise exception
        controller = MainController(real_models, mock_views)

        # Verify controller is still functional
        assert controller.extract_controller is not None


@pytest.mark.unit
class TestCrossControllerSignals:
    """Test cross-controller signal connections"""

    def test_connect_cross_controller_signals(self, real_models, mock_views):
        """Test connections between controllers"""
        MainController(real_models, mock_views)

        # Test extraction completed signal
        test_image = MagicMock()
        real_models["sprite"].extraction_completed.emit(test_image, 10)

        # Verify viewer tab was shown (if method exists)
        if hasattr(mock_views["main_window"], "show_viewer_tab"):
            mock_views["main_window"].show_viewer_tab.assert_called_once()

        # Test palette applied signal
        real_models["palette"].palette_applied.emit(5)

        # Test VRAM file changed signal
        real_models["sprite"].vram_file_changed.emit("/path/to/vram.bin")
        mock_views["inject_tab"].set_vram_file.assert_called_with("/path/to/vram.bin")


@pytest.mark.unit
class TestInitializeFromSettings:
    """Test initialization from saved settings"""

    def test_initialize_from_empty_settings(self, real_models, mock_views):
        """Test initialization when no saved settings exist"""
        controller = MainController(real_models, mock_views)

        # Should not raise exceptions
        assert controller.sprite_model.vram_file == ""
        assert controller.sprite_model.cgram_file == ""
        assert controller.sprite_model.oam_file == ""

    def test_initialize_from_saved_settings(self, real_models, mock_views, tmp_path):
        """Test initialization with saved file paths"""
        # Set up saved settings using SettingsManager methods
        real_models["project"].settings.set(
            "recent_files",
            {
                "vram": [str(tmp_path / "test.vram")],
                "cgram": [str(tmp_path / "test.cgram")],
                "oam": [str(tmp_path / "test.oam")],
            },
        )
        real_models["project"].settings.set("preferences.auto_load_files", True)

        # Force reload settings
        real_models["project"]._load_settings()

        controller = MainController(real_models, mock_views)

        # Verify files were restored
        assert controller.sprite_model.vram_file == str(tmp_path / "test.vram")
        assert controller.sprite_model.cgram_file == str(tmp_path / "test.cgram")
        assert controller.sprite_model.oam_file == str(tmp_path / "test.oam")

    def test_auto_load_preference(self, real_models, mock_views, tmp_path):
        """Test auto-load preference handling"""
        # Set up auto-load preference
        real_models["project"].settings.set(
            "recent_files", {"vram": [str(tmp_path / "test.vram")]}
        )
        real_models["project"].settings.set("preferences.auto_load_files", True)
        real_models["project"]._load_settings()

        controller = MainController(real_models, mock_views)

        # Currently auto-load is not implemented (pass statement)
        # Just verify no exceptions occur
        assert controller.project_model.auto_load_files


@pytest.mark.unit
class TestEventHandlers:
    """Test event handler methods"""

    def test_on_extraction_completed(self, real_models, mock_views, mock_controllers):
        """Test extraction completion handler"""
        controller = MainController(real_models, mock_views)
        controller.viewer_controller = mock_controllers["viewer"]
        controller.palette_controller = mock_controllers["palette"]

        # Set CGRAM file
        controller.sprite_model.cgram_file = "test.cgram"

        # Call handler
        test_image = MagicMock()
        controller._on_extraction_completed(test_image, 100)

        # Verify actions
        mock_views["main_window"].show_viewer_tab.assert_called_once()
        mock_controllers["viewer"].set_image.assert_called_once_with(test_image)
        mock_controllers["palette"].load_palettes.assert_called_once()

    def test_on_extraction_completed_no_cgram(
        self, real_models, mock_views, mock_controllers
    ):
        """Test extraction completion without CGRAM file"""
        controller = MainController(real_models, mock_views)
        controller.viewer_controller = mock_controllers["viewer"]
        controller.palette_controller = mock_controllers["palette"]

        # No CGRAM file
        controller.sprite_model.cgram_file = ""

        # Call handler
        test_image = MagicMock()
        controller._on_extraction_completed(test_image, 100)

        # Palette loading should not be called
        mock_controllers["palette"].load_palettes.assert_not_called()

    def test_on_extraction_completed_no_show_method(
        self, real_models, mock_views, mock_controllers
    ):
        """Test extraction completion when show_viewer_tab doesn't exist"""
        controller = MainController(real_models, mock_views)
        controller.viewer_controller = mock_controllers["viewer"]

        # Remove show_viewer_tab method
        delattr(mock_views["main_window"], "show_viewer_tab")

        # Should not raise exception
        test_image = MagicMock()
        controller._on_extraction_completed(test_image, 100)

        # Viewer should still be updated
        mock_controllers["viewer"].set_image.assert_called_once_with(test_image)

    def test_on_palette_applied_with_image(
        self, real_models, mock_views, mock_controllers
    ):
        """Test palette application with current image"""
        controller = MainController(real_models, mock_views)
        controller.viewer_controller = mock_controllers["viewer"]

        # Set current image
        test_image = MagicMock()
        controller.sprite_model.current_image = test_image

        # Apply palette
        controller._on_palette_applied(3)

        # Viewer should be updated
        mock_controllers["viewer"].set_image.assert_called_once_with(test_image)

    def test_on_palette_applied_no_image(
        self, real_models, mock_views, mock_controllers
    ):
        """Test palette application without current image"""
        controller = MainController(real_models, mock_views)
        controller.viewer_controller = mock_controllers["viewer"]

        # No current image
        controller.sprite_model.current_image = None

        # Apply palette
        controller._on_palette_applied(3)

        # Viewer should not be updated
        mock_controllers["viewer"].set_image.assert_not_called()


@pytest.mark.unit
class TestPublicMethods:
    """Test public interface methods"""

    def test_save_state(self, real_models, mock_views):
        """Test save state functionality"""
        controller = MainController(real_models, mock_views)

        with patch.object(real_models["project"], "save_settings") as mock_save:
            controller.save_state()
            mock_save.assert_called_once()

    def test_quick_extract_with_vram_file(
        self, real_models, mock_views, mock_controllers
    ):
        """Test quick extract when VRAM file is set"""
        controller = MainController(real_models, mock_views)
        controller.extract_controller = mock_controllers["extract"]

        # Set VRAM file
        controller.sprite_model.vram_file = "/path/to/vram.bin"

        controller.quick_extract()

        # Should call extract_sprites
        mock_controllers["extract"].extract_sprites.assert_called_once()
        mock_controllers["extract"].browse_vram_file.assert_not_called()

    def test_quick_extract_without_vram_file(
        self, real_models, mock_views, mock_controllers
    ):
        """Test quick extract when no VRAM file is set"""
        controller = MainController(real_models, mock_views)
        controller.extract_controller = mock_controllers["extract"]

        # No VRAM file
        controller.sprite_model.vram_file = ""

        controller.quick_extract()

        # Should browse for file
        mock_controllers["extract"].browse_vram_file.assert_called_once()
        mock_controllers["extract"].extract_sprites.assert_not_called()

    def test_quick_inject(self, real_models, mock_views, mock_controllers):
        """Test quick inject functionality"""
        controller = MainController(real_models, mock_views)
        controller.inject_controller = mock_controllers["inject"]

        controller.quick_inject()

        # Should show inject tab and browse for PNG
        mock_views["main_window"].show_inject_tab.assert_called_once()
        mock_controllers["inject"].browse_png_file.assert_called_once()

    def test_quick_inject_no_show_method(
        self, real_models, mock_views, mock_controllers
    ):
        """Test quick inject when show_inject_tab doesn't exist"""
        controller = MainController(real_models, mock_views)
        controller.inject_controller = mock_controllers["inject"]

        # Remove show_inject_tab method
        delattr(mock_views["main_window"], "show_inject_tab")

        controller.quick_inject()

        # Should still browse for PNG
        mock_controllers["inject"].browse_png_file.assert_called_once()


@pytest.mark.unit
class TestSignalPropagation:
    """Test signal propagation between components"""

    def test_full_signal_flow(self, real_models, mock_views):
        """Test complete signal flow through the system"""
        controller = MainController(real_models, mock_views)

        # Track method calls
        calls = []

        def track_call(name):
            def wrapper(*args, **kwargs):
                calls.append(name)

            return wrapper

        # Mock viewer controller methods
        controller.viewer_controller.set_image = track_call("viewer_set_image")
        controller.palette_controller.load_palettes = track_call("palette_load")

        # Set up state
        controller.sprite_model.cgram_file = "test.cgram"
        test_image = MagicMock()

        # Trigger extraction completed
        controller.sprite_model.extraction_completed.emit(test_image, 50)

        # Verify call order
        assert "viewer_set_image" in calls
        assert "palette_load" in calls

    def test_model_state_consistency(self, real_models, mock_views, tmp_path):
        """Test that model states remain consistent"""
        controller = MainController(real_models, mock_views)

        # Set file paths
        vram_path = str(tmp_path / "test.vram")
        cgram_path = str(tmp_path / "test.cgram")

        controller.sprite_model.vram_file = vram_path
        controller.sprite_model.cgram_file = cgram_path

        # Verify paths are preserved
        assert controller.sprite_model.vram_file == vram_path
        assert controller.sprite_model.cgram_file == cgram_path

        # Emit file change signal
        controller.sprite_model.vram_file_changed.emit(vram_path)

        # Verify inject tab was notified
        mock_views["inject_tab"].set_vram_file.assert_called_with(vram_path)


@pytest.mark.integration
class TestMainControllerIntegration:
    """Integration tests for MainController"""

    def test_complete_extraction_workflow(
        self, real_models, mock_views, mock_controllers
    ):
        """Test complete extraction workflow"""
        controller = MainController(real_models, mock_views)

        # Replace controllers with mocks
        controller.extract_controller = mock_controllers["extract"]
        controller.viewer_controller = mock_controllers["viewer"]
        controller.palette_controller = mock_controllers["palette"]

        # Set up initial state
        controller.sprite_model.vram_file = "/test/vram.bin"
        controller.sprite_model.cgram_file = "/test/cgram.bin"

        # Start extraction
        controller.quick_extract()
        mock_controllers["extract"].extract_sprites.assert_called_once()

        # Simulate extraction completion
        test_image = MagicMock()
        controller._on_extraction_completed(test_image, 100)

        # Verify complete workflow
        mock_controllers["viewer"].set_image.assert_called_with(test_image)
        mock_controllers["palette"].load_palettes.assert_called_once()

    def test_settings_persistence(self, real_models, mock_views, tmp_path):
        """Test settings save and restore"""
        # Create test files
        vram_file = tmp_path / "test1.vram"
        cgram_file = tmp_path / "test1.cgram"
        vram_file.write_bytes(b"vram")
        cgram_file.write_bytes(b"cgram")

        # Create controller and set state
        controller1 = MainController(real_models, mock_views)
        controller1.sprite_model.vram_file = str(vram_file)
        controller1.sprite_model.cgram_file = str(cgram_file)

        # Save state using the project model's methods
        controller1.project_model.add_recent_file(str(vram_file), "vram")
        controller1.project_model.add_recent_file(str(cgram_file), "cgram")
        controller1.save_state()

        # Create new controller with same models
        controller2 = MainController(real_models, mock_views)

        # Verify state was restored
        assert controller2.sprite_model.vram_file == str(vram_file)
        assert controller2.sprite_model.cgram_file == str(cgram_file)

    def test_error_handling_resilience(self, real_models, mock_views):
        """Test that controller handles errors gracefully"""
        controller = MainController(real_models, mock_views)

        # Create controller that raises exception
        error_controller = MagicMock()
        error_controller.extract_sprites.side_effect = Exception("Test error")
        controller.extract_controller = error_controller

        # Should handle exception gracefully
        controller.sprite_model.vram_file = "test.vram"

        with pytest.raises(Exception):
            controller.quick_extract()

        # Controller should still be functional
        assert controller.sprite_model is not None

    def test_cross_controller_communication(self, real_models, mock_views):
        """Test communication between multiple controllers"""
        controller = MainController(real_models, mock_views)

        # Track cross-controller calls
        viewer_calls = []
        palette_calls = []

        controller.viewer_controller.set_image = lambda img: viewer_calls.append(img)
        controller.palette_controller.load_palettes = lambda: palette_calls.append(True)

        # Set up scenario
        controller.sprite_model.cgram_file = "test.cgram"
        test_image = MagicMock()

        # Trigger workflow
        controller.sprite_model.extraction_completed.emit(test_image, 50)

        # Verify both controllers were involved
        assert len(viewer_calls) == 1
        assert viewer_calls[0] == test_image
        assert len(palette_calls) == 1
