"""
Integration tests for pixel editor launch functionality - Priority 2 test implementation.
Tests external pixel editor subprocess integration.
"""

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spritepal.core.controller import ExtractionController
from spritepal.core.managers import cleanup_managers, initialize_managers


@pytest.fixture(autouse=True)
def setup_managers():
    """Setup managers for all tests"""
    initialize_managers("TestApp")
    yield
    cleanup_managers()


@pytest.fixture
def sample_sprite_file():
    """Create sample sprite file for testing"""
    temp_dir = tempfile.mkdtemp()

    # Create a simple PNG file (mock content)
    sprite_file = Path(temp_dir) / "test_sprite.png"
    sprite_file.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x1fIDAT8\x11c\xf8\x0f\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    yield str(sprite_file)

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_launcher_file():
    """Create sample launcher file for testing"""
    temp_dir = tempfile.mkdtemp()

    # Create a simple Python launcher file
    launcher_file = Path(temp_dir) / "launch_pixel_editor.py"
    launcher_file.write_text(
        """#!/usr/bin/env python3
import sys
if __name__ == "__main__":
    print(f"Launching pixel editor with: {sys.argv[1] if len(sys.argv) > 1 else 'no args'}")
"""
    )

    yield str(launcher_file)

    # Cleanup
    shutil.rmtree(temp_dir)


class TestPixelEditorLaunchIntegration:
    """Test pixel editor launch integration"""

    def create_mock_main_window(self):
        """Create mock MainWindow for testing"""
        main_window = Mock()
        main_window.status_bar = Mock()
        main_window.status_bar.showMessage = Mock()
        main_window.open_in_editor_requested = Mock()
        main_window.open_in_editor_requested.connect = Mock()
        main_window.open_in_editor_requested.emit = Mock()
        return main_window

    def create_mock_controller(self, main_window):
        """Create ExtractionController for testing"""
        return ExtractionController(main_window)

    @pytest.mark.integration
    def test_pixel_editor_launch_success(
        self, sample_sprite_file, sample_launcher_file
    ):
        """Test successful pixel editor launch"""
        # Create mock components
        main_window = self.create_mock_main_window()
        controller = ExtractionController(main_window)

        # Mock successful subprocess launch
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("os.path.exists") as mock_exists,
            patch("os.path.abspath") as mock_abspath,
            patch("spritepal.core.controller.validate_image_file") as mock_validate,
        ):

            # Set up mocks - ensure launcher path exists during discovery and validation
            def mock_exists_side_effect(path):
                # Return True for the launcher file when it's being checked
                if path == sample_launcher_file:
                    return True
                # Return True for the absolute path version too
                if path == os.path.abspath(sample_launcher_file):
                    return True
                # Return True for any path that ends with the launcher file name
                return bool(path.endswith("launch_pixel_editor.py"))

            mock_exists.side_effect = mock_exists_side_effect
            mock_abspath.side_effect = lambda path: path
            mock_validate.return_value = (True, "")
            mock_popen.return_value = Mock()

            # Test successful launch
            controller.open_in_editor(sample_sprite_file)

            # Verify subprocess was called correctly
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]

            # Check that the call contains the expected elements
            assert call_args[0] == sys.executable
            assert call_args[1].endswith("launch_pixel_editor.py")
            assert call_args[2] == os.path.abspath(sample_sprite_file)

            # Verify success message
            main_window.status_bar.showMessage.assert_called_with(
                f"Opened {os.path.basename(sample_sprite_file)} in pixel editor"
            )

    @pytest.mark.integration
    def test_pixel_editor_launch_missing_editor(self, sample_sprite_file):
        """Test handling of missing pixel editor"""
        # Create mock components
        main_window = self.create_mock_main_window()
        controller = ExtractionController(main_window)

        # Mock missing launcher
        with (
            patch("os.path.exists") as mock_exists,
            patch("spritepal.core.controller.validate_image_file") as mock_validate,
        ):

            # Set up mocks - no launcher exists
            mock_exists.return_value = False
            mock_validate.return_value = (True, "")

            # Test missing launcher
            controller.open_in_editor(sample_sprite_file)

            # Verify error message
            main_window.status_bar.showMessage.assert_called_with(
                "Pixel editor not found"
            )

    @pytest.mark.integration
    def test_pixel_editor_launch_invalid_sprite_file(self, sample_launcher_file):
        """Test handling of invalid sprite file"""
        # Create mock components
        main_window = self.create_mock_main_window()
        controller = ExtractionController(main_window)

        invalid_sprite_file = "/path/to/invalid.txt"

        # Mock validation failure
        with (
            patch("os.path.exists") as mock_exists,
            patch("spritepal.core.controller.validate_image_file") as mock_validate,
        ):

            # Set up mocks - ensure launcher is found
            def mock_exists_side_effect(path):
                if path == sample_launcher_file:
                    return True
                # Return True for any path that ends with the launcher file name
                return bool(path.endswith("launch_pixel_editor.py"))

            mock_exists.side_effect = mock_exists_side_effect
            mock_validate.return_value = (
                False,
                "Invalid file extension: .txt. Allowed: {'.png'}",
            )

            # Test invalid sprite file
            controller.open_in_editor(invalid_sprite_file)

            # Verify error message
            main_window.status_bar.showMessage.assert_called_with(
                "Invalid sprite file: Invalid file extension: .txt. Allowed: {'.png'}"
            )

    @pytest.mark.integration
    def test_pixel_editor_launch_permission_error(
        self, sample_sprite_file, sample_launcher_file
    ):
        """Test handling of permission errors"""
        # Create mock components
        main_window = self.create_mock_main_window()
        controller = ExtractionController(main_window)

        # Mock permission error during subprocess launch
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("os.path.exists") as mock_exists,
            patch("os.path.abspath") as mock_abspath,
            patch("spritepal.core.controller.validate_image_file") as mock_validate,
        ):

            # Set up mocks - ensure launcher is found
            def mock_exists_side_effect(path):
                if path == sample_launcher_file:
                    return True
                # Return True for any path that ends with the launcher file name
                return bool(path.endswith("launch_pixel_editor.py"))

            mock_exists.side_effect = mock_exists_side_effect
            mock_abspath.side_effect = lambda path: path
            mock_validate.return_value = (True, "")
            mock_popen.side_effect = PermissionError("Permission denied")

            # Test permission error
            controller.open_in_editor(sample_sprite_file)

            # Verify error message
            main_window.status_bar.showMessage.assert_called_with(
                "Failed to open pixel editor: Permission denied"
            )

    @pytest.mark.integration
    def test_pixel_editor_launch_subprocess_error(
        self, sample_sprite_file, sample_launcher_file
    ):
        """Test handling of subprocess errors"""
        # Create mock components
        main_window = self.create_mock_main_window()
        controller = ExtractionController(main_window)

        # Mock subprocess error
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("os.path.exists") as mock_exists,
            patch("os.path.abspath") as mock_abspath,
            patch("spritepal.core.controller.validate_image_file") as mock_validate,
        ):

            # Set up mocks - ensure launcher is found in discovery and validation
            def mock_exists_side_effect(path):
                # Mock launcher discovery - any of the launcher paths should exist
                if "launch_pixel_editor.py" in path:
                    return True
                # Mock sprite file exists
                return path == sample_sprite_file

            mock_exists.side_effect = mock_exists_side_effect
            mock_abspath.side_effect = lambda path: path
            mock_validate.return_value = (True, "")
            mock_popen.side_effect = OSError("No such file or directory")

            # Test subprocess error
            controller.open_in_editor(sample_sprite_file)

            # Verify error message
            main_window.status_bar.showMessage.assert_called_with(
                "Failed to open pixel editor: No such file or directory"
            )

    @pytest.mark.integration
    def test_pixel_editor_launch_file_validation(self, sample_launcher_file):
        """Test file validation before launch"""
        # Create mock components
        main_window = self.create_mock_main_window()
        controller = ExtractionController(main_window)

        # Test various validation scenarios
        test_cases = [
            ("/path/to/nonexistent.png", (False, "File not found")),
            ("/path/to/too_large.png", (False, "File too large")),
            ("/path/to/invalid.txt", (False, "Invalid file extension")),
            ("/path/to/corrupted.png", (False, "Corrupted file")),
        ]

        for sprite_file, validation_result in test_cases:
            with (
                patch("os.path.exists") as mock_exists,
                patch("spritepal.core.controller.validate_image_file") as mock_validate,
            ):

                # Set up mocks - ensure launcher is found during discovery
                def mock_exists_side_effect(path):
                    # Return True for launcher file and any path that contains the launcher name
                    if path == sample_launcher_file:
                        return True
                    return "launch_pixel_editor.py" in path

                mock_exists.side_effect = mock_exists_side_effect
                mock_validate.return_value = validation_result

                # Test validation
                controller.open_in_editor(sprite_file)

                # Verify validation was called
                mock_validate.assert_called_once_with(sprite_file)

                # Verify error message
                main_window.status_bar.showMessage.assert_called_with(
                    f"Invalid sprite file: {validation_result[1]}"
                )

                # Reset mock
                main_window.status_bar.showMessage.reset_mock()

    @pytest.mark.integration
    def test_pixel_editor_launcher_path_discovery(
        self, sample_sprite_file, sample_launcher_file
    ):
        """Test launcher path discovery logic"""
        # Create mock components
        main_window = self.create_mock_main_window()
        controller = ExtractionController(main_window)

        # Test launcher discovery with simple scenario
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("os.path.exists") as mock_exists,
            patch("os.path.abspath") as mock_abspath,
            patch("spritepal.core.controller.validate_image_file") as mock_validate,
        ):

            # Set up mocks - ensure launcher is found during path discovery
            def mock_exists_side_effect(path):
                # Return True for the sample launcher file
                if path == sample_launcher_file:
                    return True
                # Return True for any path that contains launch_pixel_editor.py
                return "launch_pixel_editor.py" in path

            mock_exists.side_effect = mock_exists_side_effect
            mock_abspath.side_effect = lambda path: path
            mock_validate.return_value = (True, "")
            mock_popen.return_value = Mock()

            # Test launcher discovery
            controller.open_in_editor(sample_sprite_file)

            # Verify subprocess was called (the exact launcher path may vary but subprocess should be called)
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]

            # Check that the call contains the expected elements
            assert call_args[0] == sys.executable
            assert call_args[1].endswith("launch_pixel_editor.py")
            assert call_args[2] == os.path.abspath(sample_sprite_file)

            # Verify success message
            main_window.status_bar.showMessage.assert_called_with(
                f"Opened {os.path.basename(sample_sprite_file)} in pixel editor"
            )

    @pytest.mark.integration
    def test_pixel_editor_launch_with_palette_files(
        self, sample_sprite_file, sample_launcher_file
    ):
        """Test pixel editor launch with palette files"""
        # Create mock components
        main_window = self.create_mock_main_window()
        controller = ExtractionController(main_window)

        # Create sample palette files
        temp_dir = Path(sample_sprite_file).parent
        palette_files = []
        for i in range(8, 16):
            palette_file = temp_dir / f"test_sprite_pal{i}.pal.json"
            palette_file.write_text(
                f'{{"palette": {{"colors": [{{"r": {i*10}, "g": {i*10}, "b": {i*10}}}]}}}}'
            )
            palette_files.append(str(palette_file))

        # Mock successful launch
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("os.path.exists") as mock_exists,
            patch("os.path.abspath") as mock_abspath,
            patch("spritepal.core.controller.validate_image_file") as mock_validate,
        ):

            # Set up mocks - ensure launcher is found during discovery
            def mock_exists_side_effect(path):
                # Return True for the sample launcher file
                if path == sample_launcher_file:
                    return True
                # Return True for any path that contains launch_pixel_editor.py
                if "launch_pixel_editor.py" in path:
                    return True
                # Return True for palette files
                return path in palette_files

            mock_exists.side_effect = mock_exists_side_effect
            mock_abspath.side_effect = lambda path: path
            mock_validate.return_value = (True, "")
            mock_popen.return_value = Mock()

            # Test launch with palette files
            controller.open_in_editor(sample_sprite_file)

            # Verify subprocess was called (the exact launcher path may vary but subprocess should be called)
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]

            # Check that the call contains the expected elements
            assert call_args[0] == sys.executable
            assert call_args[1].endswith("launch_pixel_editor.py")
            assert call_args[2] == os.path.abspath(sample_sprite_file)

            # Note: Palette files are auto-loaded by the pixel editor itself
            # The launch process just passes the sprite file path

            # Verify success message
            main_window.status_bar.showMessage.assert_called_with(
                f"Opened {os.path.basename(sample_sprite_file)} in pixel editor"
            )

    @pytest.mark.integration
    def test_pixel_editor_launch_signal_integration(
        self, sample_sprite_file, sample_launcher_file
    ):
        """Test signal integration for pixel editor launch"""
        # Create mock components
        main_window = self.create_mock_main_window()
        controller = ExtractionController(main_window)

        # Mock successful launch
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("os.path.exists") as mock_exists,
            patch("os.path.abspath") as mock_abspath,
            patch("spritepal.core.controller.validate_image_file") as mock_validate,
        ):

            # Set up mocks - ensure launcher is found during discovery
            def mock_exists_side_effect(path):
                # Return True for the sample launcher file
                if path == sample_launcher_file:
                    return True
                # Return True for any path that contains launch_pixel_editor.py
                return "launch_pixel_editor.py" in path

            mock_exists.side_effect = mock_exists_side_effect
            mock_abspath.side_effect = lambda path: path
            mock_validate.return_value = (True, "")
            mock_popen.return_value = Mock()

            # Test signal emission
            main_window.open_in_editor_requested.emit(sample_sprite_file)

            # Verify signal was emitted
            main_window.open_in_editor_requested.emit.assert_called_with(
                sample_sprite_file
            )

            # Verify connection was made during controller initialization
            main_window.open_in_editor_requested.connect.assert_called_with(
                controller.open_in_editor
            )


class TestPixelEditorLaunchErrorRecovery:
    """Test error recovery scenarios for pixel editor launch"""

    def create_mock_main_window(self):
        """Create mock MainWindow for testing"""
        main_window = Mock()
        main_window.status_bar = Mock()
        main_window.status_bar.showMessage = Mock()
        return main_window

    def create_mock_controller(self, main_window):
        """Create ExtractionController for testing"""
        return ExtractionController(main_window)

    @pytest.mark.integration
    def test_pixel_editor_launch_recovery_after_error(
        self, sample_sprite_file, sample_launcher_file
    ):
        """Test recovery after launch error"""
        # Create mock components
        main_window = self.create_mock_main_window()
        controller = ExtractionController(main_window)

        # Test error followed by successful launch
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("os.path.exists") as mock_exists,
            patch("os.path.abspath") as mock_abspath,
            patch("spritepal.core.controller.validate_image_file") as mock_validate,
        ):

            # Set up mocks - ensure launcher is found during discovery
            def mock_exists_side_effect(path):
                # Return True for the sample launcher file
                if path == sample_launcher_file:
                    return True
                # Return True for any path that contains launch_pixel_editor.py
                return "launch_pixel_editor.py" in path

            mock_exists.side_effect = mock_exists_side_effect
            mock_abspath.side_effect = lambda path: path
            mock_validate.return_value = (True, "")

            # First call fails
            mock_popen.side_effect = [OSError("Process failed"), Mock()]

            # Test first launch (fails)
            controller.open_in_editor(sample_sprite_file)

            # Verify error message
            main_window.status_bar.showMessage.assert_called_with(
                "Failed to open pixel editor: Process failed"
            )

            # Test second launch (succeeds)
            controller.open_in_editor(sample_sprite_file)

            # Verify success message
            main_window.status_bar.showMessage.assert_called_with(
                f"Opened {os.path.basename(sample_sprite_file)} in pixel editor"
            )

            # Verify both calls were made
            assert mock_popen.call_count == 2

    @pytest.mark.integration
    def test_pixel_editor_launch_multiple_attempts(
        self, sample_sprite_file, sample_launcher_file
    ):
        """Test multiple launch attempts"""
        # Create mock components
        main_window = self.create_mock_main_window()
        controller = ExtractionController(main_window)

        # Test multiple launches
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("os.path.exists") as mock_exists,
            patch("os.path.abspath") as mock_abspath,
            patch("spritepal.core.controller.validate_image_file") as mock_validate,
        ):

            # Set up mocks - ensure launcher is found during discovery
            def mock_exists_side_effect(path):
                # Return True for the sample launcher file
                if path == sample_launcher_file:
                    return True
                # Return True for any path that contains launch_pixel_editor.py
                return "launch_pixel_editor.py" in path

            mock_exists.side_effect = mock_exists_side_effect
            mock_abspath.side_effect = lambda path: path
            mock_validate.return_value = (True, "")
            mock_popen.return_value = Mock()

            # Test multiple launches
            for i in range(3):
                controller.open_in_editor(sample_sprite_file)

                # Verify each launch
                assert mock_popen.call_count == i + 1
                main_window.status_bar.showMessage.assert_called_with(
                    f"Opened {os.path.basename(sample_sprite_file)} in pixel editor"
                )

    @pytest.mark.integration
    def test_pixel_editor_launch_cleanup_on_error(
        self, sample_sprite_file, sample_launcher_file
    ):
        """Test proper cleanup on launch error"""
        # Create mock components
        main_window = self.create_mock_main_window()
        controller = ExtractionController(main_window)

        # Test cleanup after error
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("os.path.exists") as mock_exists,
            patch("os.path.abspath") as mock_abspath,
            patch("spritepal.core.controller.validate_image_file") as mock_validate,
        ):

            # Set up mocks - ensure launcher is found during discovery
            def mock_exists_side_effect(path):
                # Return True for the sample launcher file
                if path == sample_launcher_file:
                    return True
                # Return True for any path that contains launch_pixel_editor.py
                return "launch_pixel_editor.py" in path

            mock_exists.side_effect = mock_exists_side_effect
            mock_abspath.side_effect = lambda path: path
            mock_validate.return_value = (True, "")

            # Mock process that fails
            mock_process = Mock()
            mock_process.poll.return_value = None  # Process still running
            mock_popen.side_effect = Exception("Launch failed")

            # Test launch with error
            controller.open_in_editor(sample_sprite_file)

            # Verify error was handled
            main_window.status_bar.showMessage.assert_called_with(
                "Failed to open pixel editor: Launch failed"
            )

            # Verify subprocess was attempted
            mock_popen.assert_called_once()


class TestPixelEditorLaunchPerformance:
    """Test performance characteristics of pixel editor launch"""

    def create_mock_main_window(self):
        """Create mock MainWindow for testing"""
        main_window = Mock()
        main_window.status_bar = Mock()
        main_window.status_bar.showMessage = Mock()
        return main_window

    def create_mock_controller(self, main_window):
        """Create ExtractionController for testing"""
        return ExtractionController(main_window)

    @pytest.mark.integration
    def test_pixel_editor_launch_performance(
        self, sample_sprite_file, sample_launcher_file
    ):
        """Test launch performance characteristics"""
        # Create mock components
        main_window = self.create_mock_main_window()
        controller = ExtractionController(main_window)

        # Test launch performance
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("os.path.exists") as mock_exists,
            patch("os.path.abspath") as mock_abspath,
            patch("spritepal.core.controller.validate_image_file") as mock_validate,
        ):

            # Set up mocks - ensure launcher is found during discovery
            def mock_exists_side_effect(path):
                # Return True for the sample launcher file
                if path == sample_launcher_file:
                    return True
                # Return True for any path that contains launch_pixel_editor.py
                return "launch_pixel_editor.py" in path

            mock_exists.side_effect = mock_exists_side_effect
            mock_abspath.side_effect = lambda path: path
            mock_validate.return_value = (True, "")
            mock_popen.return_value = Mock()

            # Measure launch time
            start_time = time.time()

            # Test multiple launches
            for _i in range(10):
                controller.open_in_editor(sample_sprite_file)

            end_time = time.time()
            total_time = end_time - start_time

            # Verify performance (should be fast with mocks)
            assert total_time < 1.0  # Should complete in under 1 second

            # Verify all launches completed
            assert mock_popen.call_count == 10
            assert main_window.status_bar.showMessage.call_count == 10

    @pytest.mark.integration
    def test_pixel_editor_launch_resource_usage(
        self, sample_sprite_file, sample_launcher_file
    ):
        """Test resource usage during launch"""
        # Create mock components
        main_window = self.create_mock_main_window()
        controller = ExtractionController(main_window)

        # Test resource usage
        with (
            patch("subprocess.Popen") as mock_popen,
            patch("os.path.exists") as mock_exists,
            patch("os.path.abspath") as mock_abspath,
            patch("spritepal.core.controller.validate_image_file") as mock_validate,
        ):

            # Set up mocks - ensure launcher is found during discovery
            def mock_exists_side_effect(path):
                # Return True for the sample launcher file
                if path == sample_launcher_file:
                    return True
                # Return True for any path that contains launch_pixel_editor.py
                return "launch_pixel_editor.py" in path

            mock_exists.side_effect = mock_exists_side_effect
            mock_abspath.side_effect = lambda path: path
            mock_validate.return_value = (True, "")
            mock_popen.return_value = Mock()

            # Test multiple simultaneous launches
            for _i in range(5):
                controller.open_in_editor(sample_sprite_file)

            # Verify all launches were attempted
            assert mock_popen.call_count == 5

            # Verify each call was made correctly
            for call in mock_popen.call_args_list:
                args, kwargs = call
                # Check that the call contains the expected elements
                assert args[0][0] == sys.executable
                assert args[0][1].endswith("launch_pixel_editor.py")
                assert args[0][2] == os.path.abspath(sample_sprite_file)
