#!/usr/bin/env python3
"""
Test suite for the main() function
Tests command-line argument handling and application startup
"""

import os
import sys
import tempfile
from unittest.mock import Mock, patch

import pytest

from indexed_pixel_editor import main


class TestMainFunction:
    """Test cases for the main() function"""

    @pytest.fixture
    def mock_qt_app(self):
        """Mock QApplication"""
        with patch("indexed_pixel_editor.QApplication") as mock_app:
            mock_instance = Mock()
            mock_instance.exec.return_value = 0
            mock_app.return_value = mock_instance
            yield mock_app, mock_instance

    @pytest.fixture
    def mock_editor(self):
        """Mock IndexedPixelEditor"""
        with patch("indexed_pixel_editor.IndexedPixelEditor") as mock_editor_class:
            mock_instance = Mock()
            mock_instance.load_file_by_path.return_value = True
            mock_instance.load_palette_by_path.return_value = True
            mock_editor_class.return_value = mock_instance
            yield mock_editor_class, mock_instance

    @pytest.fixture
    def mock_os_exists(self):
        """Mock os.path.exists"""
        with patch("os.path.exists") as mock_exists:
            yield mock_exists

    def test_no_arguments(self, mock_qt_app, mock_editor):
        """Test launching with no command line arguments"""
        with patch.object(sys, "argv", ["indexed_pixel_editor.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Verify application was created and shown
            mock_qt_app[0].assert_called_once_with(["indexed_pixel_editor.py"])
            mock_editor[1].show.assert_called_once()
            mock_qt_app[1].exec.assert_called_once()
            assert exc_info.value.code == 0

    def test_with_valid_image_file(self, mock_qt_app, mock_editor, mock_os_exists):
        """Test launching with valid image file"""
        mock_os_exists.return_value = True

        with patch.object(sys, "argv", ["indexed_pixel_editor.py", "test.png"]):
            with pytest.raises(SystemExit):
                main()

            # Verify file was loaded
            mock_editor[1].show.assert_called_once()
            mock_editor[1].load_file_by_path.assert_called_once_with("test.png")
            mock_editor[1].load_palette_by_path.assert_not_called()

    def test_with_nonexistent_image_file(self, mock_qt_app, mock_editor, mock_os_exists):
        """Test launching with non-existent image file"""
        mock_os_exists.return_value = False

        with patch.object(sys, "argv", ["indexed_pixel_editor.py", "missing.png"]):
            with patch("indexed_pixel_editor.debug_log") as mock_log:
                with pytest.raises(SystemExit):
                    main()

                # Verify error was logged
                mock_log.assert_called_with("MAIN", "File not found: missing.png", "ERROR")
                mock_editor[1].load_file_by_path.assert_not_called()

    def test_with_image_and_palette(self, mock_qt_app, mock_editor, mock_os_exists):
        """Test launching with image and palette files"""
        mock_os_exists.return_value = True

        with patch.object(sys, "argv", ["indexed_pixel_editor.py", "test.png", "-p", "palette.json"]):
            with pytest.raises(SystemExit):
                main()

            # Verify both files were loaded
            mock_editor[1].load_file_by_path.assert_called_once_with("test.png")
            mock_editor[1].load_palette_by_path.assert_called_once_with("palette.json")

    def test_with_image_and_nonexistent_palette(self, mock_qt_app, mock_editor, mock_os_exists):
        """Test launching with image and non-existent palette"""
        def exists_side_effect(path):
            return path == "test.png"  # Only image exists

        mock_os_exists.side_effect = exists_side_effect

        with patch.object(sys, "argv", ["indexed_pixel_editor.py", "test.png", "-p", "missing.json"]):
            with pytest.raises(SystemExit):
                main()

            # Verify image loaded but palette didn't (silently skips)
            mock_editor[1].load_file_by_path.assert_called_once_with("test.png")
            mock_editor[1].load_palette_by_path.assert_not_called()

    def test_image_load_failure(self, mock_qt_app, mock_editor, mock_os_exists):
        """Test when image loading fails"""
        mock_os_exists.return_value = True
        mock_editor[1].load_file_by_path.return_value = False

        with patch.object(sys, "argv", ["indexed_pixel_editor.py", "corrupt.png"]):
            with patch("indexed_pixel_editor.debug_log") as mock_log:
                with pytest.raises(SystemExit):
                    main()

                # Verify error was logged and palette not loaded
                mock_log.assert_called_with("MAIN", "Failed to load file: corrupt.png", "ERROR")
                mock_editor[1].load_palette_by_path.assert_not_called()

    def test_invalid_argument_count(self, mock_qt_app, mock_editor):
        """Test with incomplete palette arguments"""
        # This tests the potential bug where argv[3] might not exist
        with patch.object(sys, "argv", ["indexed_pixel_editor.py", "test.png", "-p"]):
            with pytest.raises(SystemExit):
                main()

            # Should still show editor but not crash
            mock_editor[1].show.assert_called_once()

    def test_wrong_palette_flag_position(self, mock_qt_app, mock_editor, mock_os_exists):
        """Test palette flag in wrong position"""
        mock_os_exists.return_value = True

        # Put -p as first argument (wrong position)
        with patch.object(sys, "argv", ["indexed_pixel_editor.py", "-p", "palette.json", "test.png"]):
            with pytest.raises(SystemExit):
                main()

            # Should try to load '-p' as image file
            mock_editor[1].load_file_by_path.assert_called_once_with("-p")
            mock_editor[1].load_palette_by_path.assert_not_called()

    @patch("indexed_pixel_editor.debug_log")
    def test_debug_logging(self, mock_log, mock_qt_app, mock_editor, mock_os_exists):
        """Test that debug logging works correctly"""
        mock_os_exists.return_value = False

        with patch.object(sys, "argv", ["indexed_pixel_editor.py", "test.png"]):
            with pytest.raises(SystemExit):
                main()

            mock_log.assert_called_with("MAIN", "File not found: test.png", "ERROR")

    def test_app_exec_return_code(self, mock_qt_app, mock_editor):
        """Test that app.exec() return code is properly propagated"""
        # Test with non-zero return code
        mock_qt_app[1].exec.return_value = 1

        with patch.object(sys, "argv", ["indexed_pixel_editor.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

    def test_integration_with_real_files(self):
        """Integration test with real temporary files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a real indexed PNG
            import numpy as np
            from PIL import Image

            img_path = os.path.join(temp_dir, "test.png")
            data = np.zeros((8, 8), dtype=np.uint8)
            img = Image.fromarray(data, mode="P")
            img.save(img_path)

            # Create a real palette file
            import json
            pal_path = os.path.join(temp_dir, "test.pal.json")
            palette_data = {
                "palette": {
                    "name": "Test",
                    "colors": [[255, 0, 0]] * 16
                }
            }
            with open(pal_path, "w") as f:
                json.dump(palette_data, f)

            # Mock only the Qt parts
            with patch("indexed_pixel_editor.QApplication") as mock_app:
                mock_instance = Mock()
                mock_instance.exec.return_value = 0
                mock_app.return_value = mock_instance

                with patch("indexed_pixel_editor.IndexedPixelEditor") as mock_editor_class:
                    mock_editor_inst = Mock()
                    mock_editor_inst.load_file_by_path.return_value = True
                    mock_editor_inst.load_palette_by_path.return_value = True
                    mock_editor_class.return_value = mock_editor_inst

                    # Test with real file paths
                    with patch.object(sys, "argv", ["indexed_pixel_editor.py", img_path, "-p", pal_path]):
                        with pytest.raises(SystemExit) as exc_info:
                            main()

                        # Verify correct loading sequence
                        mock_editor_inst.show.assert_called_once()
                        mock_editor_inst.load_file_by_path.assert_called_once_with(img_path)
                        mock_editor_inst.load_palette_by_path.assert_called_once_with(pal_path)
                        assert exc_info.value.code == 0
