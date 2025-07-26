"""
Tests for ROM injection settings persistence
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from spritepal.ui.injection_dialog import InjectionDialog
from spritepal.utils.constants import (
    SETTINGS_KEY_FAST_COMPRESSION,
    SETTINGS_KEY_LAST_CUSTOM_OFFSET,
    SETTINGS_KEY_LAST_INPUT_ROM,
    SETTINGS_KEY_LAST_INPUT_VRAM,
    SETTINGS_KEY_LAST_OUTPUT_VRAM,
    SETTINGS_KEY_LAST_SPRITE_LOCATION,
    SETTINGS_NS_ROM_INJECTION,
)
from spritepal.utils.settings_manager import SettingsManager


class TestROMInjectionSettingsPersistence:
    """Test ROM injection settings persistence functionality"""

    @pytest.fixture
    def temp_settings_file(self):
        """Create a temporary settings file"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def settings_manager(self, temp_settings_file):
        """Create a settings manager with temporary file"""
        # Create patcher for the settings file path
        patcher = patch.object(
            SettingsManager, "_get_settings_file", return_value=Path(temp_settings_file)
        )
        patcher.start()

        manager = SettingsManager()

        yield manager

        patcher.stop()

    @pytest.fixture
    def mock_dialog(self):
        """Create a mock injection dialog"""
        # Create a mock dialog without initializing Qt components
        dialog = Mock(spec=InjectionDialog)

        # Mock UI elements
        dialog.input_rom_edit = Mock()
        dialog.output_rom_edit = Mock()
        dialog.sprite_location_combo = Mock()
        dialog.rom_offset_hex_edit = Mock()
        dialog.fast_compression_check = Mock()
        dialog.input_vram_edit = Mock()
        dialog.output_vram_edit = Mock()

        # Add the actual method from the class
        dialog.save_rom_injection_parameters = (
            InjectionDialog.save_rom_injection_parameters.__get__(dialog)
        )
        dialog._set_rom_injection_defaults = (
            InjectionDialog._set_rom_injection_defaults.__get__(dialog)
        )
        dialog._restore_saved_sprite_location = (
            InjectionDialog._restore_saved_sprite_location.__get__(dialog)
        )
        dialog._suggest_output_rom_path = Mock(return_value="/test/rom_modified.sfc")
        dialog._load_rom_info = Mock()

        return dialog

    def test_save_rom_injection_parameters(self, mock_dialog, settings_manager):
        """Test saving ROM injection parameters"""
        # Set up mock values
        mock_dialog.input_rom_edit.text.return_value = "/path/to/test.sfc"
        mock_dialog.sprite_location_combo.currentText.return_value = (
            "Kirby Sprite (0x123456)"
        )
        mock_dialog.rom_offset_hex_edit.text.return_value = "0x123456"
        mock_dialog.fast_compression_check.isChecked.return_value = True

        # Save parameters
        with patch(
            "spritepal.ui.injection_dialog.get_settings_manager",
            return_value=settings_manager,
        ):
            mock_dialog.save_rom_injection_parameters()

        # Verify saved values
        assert (
            settings_manager.get_value(
                SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_INPUT_ROM
            )
            == "/path/to/test.sfc"
        )
        assert (
            settings_manager.get_value(
                SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_SPRITE_LOCATION
            )
            == "Kirby Sprite (0x123456)"
        )
        assert (
            settings_manager.get_value(
                SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_CUSTOM_OFFSET
            )
            == "0x123456"
        )
        assert (
            settings_manager.get_value(
                SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_FAST_COMPRESSION
            )
            is True
        )

    def test_save_empty_rom_injection_parameters(self, mock_dialog, settings_manager):
        """Test saving when fields are empty"""
        # Set up empty values
        mock_dialog.input_rom_edit.text.return_value = ""
        mock_dialog.sprite_location_combo.currentText.return_value = (
            "Select sprite location..."
        )
        mock_dialog.rom_offset_hex_edit.text.return_value = ""
        mock_dialog.fast_compression_check.isChecked.return_value = False

        # Save parameters
        with patch(
            "spritepal.ui.injection_dialog.get_settings_manager",
            return_value=settings_manager,
        ):
            mock_dialog.save_rom_injection_parameters()

        # Verify empty custom offset is saved as empty string
        value = settings_manager.get_value(
            SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_CUSTOM_OFFSET, None
        )
        assert value == ""  # Empty string is saved

        # Verify fast compression is saved as False
        value = settings_manager.get_value(
            SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_FAST_COMPRESSION, None
        )
        assert value is False

    def test_save_vram_injection_paths(self, settings_manager):
        """Test saving VRAM injection paths using ROM injection namespace"""
        # Save VRAM paths
        settings_manager.set_value(
            SETTINGS_NS_ROM_INJECTION,
            SETTINGS_KEY_LAST_INPUT_VRAM,
            "/path/to/input.dmp",
        )
        settings_manager.set_value(
            SETTINGS_NS_ROM_INJECTION,
            SETTINGS_KEY_LAST_OUTPUT_VRAM,
            "/path/to/output.dmp",
        )
        settings_manager.save()

        # Create a new settings manager to verify persistence
        with patch.object(
            SettingsManager,
            "_get_settings_file",
            return_value=settings_manager._settings_file,
        ):
            new_manager = SettingsManager()
            assert (
                new_manager.get_value(
                    SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_INPUT_VRAM
                )
                == "/path/to/input.dmp"
            )
            assert (
                new_manager.get_value(
                    SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_OUTPUT_VRAM
                )
                == "/path/to/output.dmp"
            )

    def test_load_rom_injection_defaults(self, mock_dialog, settings_manager):
        """Test loading ROM injection defaults"""
        # Pre-populate settings
        settings_manager.set_value(
            SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_INPUT_ROM, "/test/rom.sfc"
        )
        settings_manager.set_value(
            SETTINGS_NS_ROM_INJECTION,
            SETTINGS_KEY_LAST_SPRITE_LOCATION,
            "Kirby Sprite (0x123456)",
        )
        settings_manager.set_value(
            SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_CUSTOM_OFFSET, "0x789ABC"
        )
        settings_manager.set_value(
            SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_FAST_COMPRESSION, True
        )

        # Mock file existence check
        with (
            patch("os.path.exists", return_value=True),
            patch(
                "spritepal.ui.injection_dialog.get_settings_manager",
                return_value=settings_manager,
            ),
        ):

            mock_dialog._set_rom_injection_defaults()

        # Verify UI elements were populated
        mock_dialog.input_rom_edit.setText.assert_called_with("/test/rom.sfc")
        mock_dialog.output_rom_edit.setText.assert_called_with("/test/rom_modified.sfc")
        mock_dialog.rom_offset_hex_edit.setText.assert_called_with("0x789ABC")
        mock_dialog.fast_compression_check.setChecked.assert_called_with(True)

    def test_settings_save_error_handling(self, mock_dialog, settings_manager, caplog):
        """Test error handling when saving settings fails"""
        import logging

        caplog.set_level(logging.ERROR)

        # Set up mock values
        mock_dialog.input_rom_edit.text.return_value = "/path/to/test.sfc"
        mock_dialog.sprite_location_combo.currentText.return_value = (
            "Select sprite location..."
        )
        mock_dialog.rom_offset_hex_edit.text.return_value = ""
        mock_dialog.fast_compression_check.isChecked.return_value = False

        # Mock save to raise exception
        with (
            patch(
                "spritepal.ui.injection_dialog.get_settings_manager",
                return_value=settings_manager,
            ),
            patch.object(
                settings_manager, "save", side_effect=OSError("Permission denied")
            ),
        ):

            # Call the method
            mock_dialog.save_rom_injection_parameters()

            # Verify error was logged using caplog
            assert len(caplog.records) >= 1
            assert "Failed to save ROM injection parameters" in caplog.text
            assert "Permission denied" in caplog.text

    def test_sprite_location_restoration_after_rom_load(self, mock_dialog):
        """Test that sprite location is restored after ROM is loaded"""
        # Setup combo box with items
        mock_dialog.sprite_location_combo.count.return_value = 4
        mock_dialog.sprite_location_combo.itemText.side_effect = [
            "Select sprite location...",
            "Kirby Sprite (0x123456)",
            "Helper Sprite (0x234567)",
            "Boss Sprite (0x345678)",
        ]

        # Mock settings with saved sprite location
        with patch(
            "spritepal.ui.injection_dialog.get_settings_manager"
        ) as mock_get_settings:
            mock_settings = Mock()
            mock_settings.get_value.return_value = "Helper Sprite (0x234567)"
            mock_get_settings.return_value = mock_settings

            mock_dialog._restore_saved_sprite_location()

        # Verify correct index was selected (index 2 for "Helper Sprite")
        mock_dialog.sprite_location_combo.setCurrentIndex.assert_called_with(2)

    def test_settings_namespace_consistency(self, settings_manager):
        """Test that all ROM injection settings use consistent namespace"""
        # Save various settings
        settings_manager.set_value(
            SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_INPUT_ROM, "/test.sfc"
        )
        settings_manager.set_value(
            SETTINGS_NS_ROM_INJECTION, SETTINGS_KEY_LAST_INPUT_VRAM, "/test.dmp"
        )
        settings_manager.save()

        # Verify namespace structure in raw settings
        raw_settings = settings_manager._settings
        assert SETTINGS_NS_ROM_INJECTION in raw_settings
        rom_injection_settings = raw_settings[SETTINGS_NS_ROM_INJECTION]

        assert SETTINGS_KEY_LAST_INPUT_ROM in rom_injection_settings
        assert SETTINGS_KEY_LAST_INPUT_VRAM in rom_injection_settings

        # Verify old namespace is not used
        assert (
            "injection" not in raw_settings
            or SETTINGS_KEY_LAST_INPUT_ROM not in raw_settings.get("injection", {})
        )
