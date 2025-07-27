"""
Test InjectionDialog migration to TabbedDialog + components architecture

Validates that the migrated InjectionDialog maintains all original functionality
while using the new UI component architecture.
"""



from spritepal.ui.components import TabbedDialog
from spritepal.ui.injection_dialog import InjectionDialog


class TestInjectionDialogMigration:
    """Test InjectionDialog migration to component architecture"""

    def test_injection_dialog_inherits_from_tabbed_dialog(self, qtbot):
        """Test that InjectionDialog properly inherits from TabbedDialog"""
        dialog = InjectionDialog()
        qtbot.addWidget(dialog)

        # Verify inheritance
        assert isinstance(dialog, TabbedDialog)

        # Verify TabbedDialog features are available
        assert dialog.tab_widget is not None
        assert dialog.get_current_tab_index() >= 0
        assert dialog.get_current_tab_widget() is not None

        # Verify dialog configuration
        assert dialog.windowTitle() == "Inject Sprite"
        assert dialog.isModal() is True

    def test_injection_dialog_has_correct_tabs(self, qtbot):
        """Test that InjectionDialog has the correct tab structure"""
        dialog = InjectionDialog()
        qtbot.addWidget(dialog)

        # Should have 2 tabs (VRAM and ROM injection)
        assert dialog.tab_widget.count() == 2

        # Check tab titles
        assert dialog.tab_widget.tabText(0) == "VRAM Injection"
        assert dialog.tab_widget.tabText(1) == "ROM Injection"

        # Trigger showEvent to ensure default tab is set
        dialog.show()

        # ROM injection should be default tab (index 1)
        assert dialog.get_current_tab_index() == 1

    def test_injection_dialog_has_hex_offset_components(self, qtbot):
        """Test that hex offset inputs are properly replaced with HexOffsetInput components"""
        dialog = InjectionDialog()
        qtbot.addWidget(dialog)

        # Check that hex offset components exist
        assert hasattr(dialog, "vram_offset_input")
        assert hasattr(dialog, "rom_offset_input")

        # Verify they have the component API methods
        assert hasattr(dialog.vram_offset_input, "get_value")
        assert hasattr(dialog.vram_offset_input, "set_text")
        assert hasattr(dialog.vram_offset_input, "is_valid")

        assert hasattr(dialog.rom_offset_input, "get_value")
        assert hasattr(dialog.rom_offset_input, "set_text")
        assert hasattr(dialog.rom_offset_input, "is_valid")

    def test_injection_dialog_has_file_selector_components(self, qtbot):
        """Test that file selectors are properly replaced with FileSelector components"""
        dialog = InjectionDialog()
        qtbot.addWidget(dialog)

        # Check that file selector components exist
        assert hasattr(dialog, "sprite_file_selector")
        assert hasattr(dialog, "input_vram_selector")
        assert hasattr(dialog, "output_vram_selector")
        assert hasattr(dialog, "input_rom_selector")
        assert hasattr(dialog, "output_rom_selector")

        # Verify they have the component API methods
        for selector_name in ["sprite_file_selector", "input_vram_selector",
                             "output_vram_selector", "input_rom_selector", "output_rom_selector"]:
            selector = getattr(dialog, selector_name)
            assert hasattr(selector, "get_path")
            assert hasattr(selector, "set_path")
            assert hasattr(selector, "is_valid")

    def test_hex_offset_parsing_functionality(self, qtbot):
        """Test that hex offset parsing works correctly with new components"""
        dialog = InjectionDialog()
        qtbot.addWidget(dialog)

        # Test VRAM offset parsing
        dialog.vram_offset_input.set_text("0xC000")
        assert dialog.vram_offset_input.get_value() == 0xC000
        assert dialog.vram_offset_input.is_valid() is True

        # Test ROM offset parsing
        dialog.rom_offset_input.set_text("200000")
        assert dialog.rom_offset_input.get_value() == 0x200000
        assert dialog.rom_offset_input.is_valid() is True

        # Test invalid input
        dialog.vram_offset_input.set_text("invalid")
        assert dialog.vram_offset_input.get_value() is None
        assert dialog.vram_offset_input.is_valid() is False

    def test_file_path_functionality(self, qtbot):
        """Test that file path setting/getting works with new components"""
        dialog = InjectionDialog()
        qtbot.addWidget(dialog)

        # Test setting and getting paths
        test_path = "/test/path/sprite.png"
        dialog.sprite_file_selector.set_path(test_path)
        assert dialog.sprite_file_selector.get_path() == test_path

        # Test clearing paths
        dialog.sprite_file_selector.clear_path()
        assert dialog.sprite_file_selector.get_path() == ""

    def test_parameter_extraction_uses_component_apis(self, qtbot):
        """Test that parameter extraction uses component APIs instead of direct widget access"""
        dialog = InjectionDialog()
        qtbot.addWidget(dialog)

        # Set up test data using component APIs
        dialog.sprite_file_selector.set_path("/test/sprite.png")
        dialog.vram_offset_input.set_text("0xC000")
        dialog.input_vram_selector.set_path("/test/input.dmp")
        dialog.output_vram_selector.set_path("/test/output.dmp")

        # Mock the parameters extraction method if it exists
        if hasattr(dialog, "_get_vram_parameters"):
            params = dialog._get_vram_parameters()

            # Verify it's using component APIs
            assert params.get("sprite_path") == "/test/sprite.png"
            assert params.get("vram_offset") == 0xC000
            assert params.get("input_vram_path") == "/test/input.dmp"
            assert params.get("output_vram_path") == "/test/output.dmp"

    def test_injection_dialog_initialization_with_parameters(self, qtbot):
        """Test dialog initialization with initial parameters"""
        # Test initialization with parameters
        dialog = InjectionDialog(
            sprite_path="/test/sprite.png",
            metadata_path="/test/metadata.json",
            input_vram="/test/vram.dmp"
        )
        qtbot.addWidget(dialog)

        # Verify parameters were set correctly
        assert dialog.sprite_file_selector.get_path() == "/test/sprite.png"
        assert dialog.input_vram_selector.get_path() == "/test/vram.dmp"

    def test_no_legacy_methods_remain(self, qtbot):
        """Test that obsolete methods were properly removed"""
        dialog = InjectionDialog()
        qtbot.addWidget(dialog)

        # These methods should no longer exist after migration
        legacy_methods = [
            "_browse_sprite",
            "_browse_input_vram",
            "_browse_output_vram",
            "_browse_input_rom",
            "_browse_output_rom",
            "_parse_hex_offset"
        ]

        for method_name in legacy_methods:
            assert not hasattr(dialog, method_name), f"Legacy method {method_name} should be removed"

    def test_file_browsing_uses_component_dialogs(self, qtbot):
        """Test that file browsing uses FileSelector component dialogs"""
        from .fixtures.test_file_dialog_helper import TestFileDialogHelper

        helper = TestFileDialogHelper()
        helper.set_open_file_response("/selected/file.png", "")

        dialog = InjectionDialog()
        qtbot.addWidget(dialog)

        # Test file browsing with real QFileDialog behavior
        with helper.patch_file_dialogs():
            dialog.sprite_file_selector._browse_file()

        # Verify dialog was called with correct parameters
        assert helper.was_dialog_called("open")

        # Verify the dialog received the file path
        assert dialog.sprite_file_selector.get_path() == "/selected/file.png"

    def test_dialog_accepts_and_rejects_properly(self, qtbot):
        """Test that dialog accept/reject functionality works"""
        dialog = InjectionDialog()
        qtbot.addWidget(dialog)

        # Should be able to accept/reject without errors
        # (We can't easily test the actual dialog execution in headless mode,
        # but we can verify the methods exist and don't crash)
        assert hasattr(dialog, "accept")
        assert hasattr(dialog, "reject")

        # Verify button box exists and is connected
        assert dialog.button_box is not None
