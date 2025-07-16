#!/usr/bin/env python3
"""
Comprehensive GUI tests for sprite editor views
Tests real Qt widget interactions with minimal mocking
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QPushButton

from sprite_editor_unified import QuickActionDialog, UnifiedSpriteEditor, WorkflowWorker


@pytest.fixture
def editor(qtbot):
    """Create UnifiedSpriteEditor instance with Qt support"""
    editor = UnifiedSpriteEditor()
    qtbot.addWidget(editor)
    editor.show()
    qtbot.waitExposed(editor)
    return editor


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files"""
    # Create test VRAM file
    vram_file = tmp_path / "test.vram"
    vram_file.write_bytes(b"\x00" * 65536)  # 64KB

    # Create test CGRAM file
    cgram_file = tmp_path / "test.cgram"
    cgram_file.write_bytes(b"\x00" * 512)  # 512 bytes

    # Create test PNG file
    png_file = tmp_path / "test.png"
    # Minimal PNG header
    png_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x00IEND\xaeB`\x82"
    png_file.write_bytes(png_data)

    return {
        "vram": str(vram_file),
        "cgram": str(cgram_file),
        "png": str(png_file),
        "dir": str(tmp_path),
    }


@pytest.mark.gui
class TestMainWindow:
    """Test main window functionality"""

    def test_window_initialization(self, editor):
        """Test main window is properly initialized"""
        assert editor.windowTitle() == "Kirby Super Star Sprite Editor - Unified"
        assert editor.isVisible()

        # Check main components exist based on actual implementation
        assert hasattr(editor, "tab_widget")
        assert hasattr(editor, "status_bar")
        assert hasattr(editor, "current_project")
        assert hasattr(editor, "recent_files")
        assert hasattr(editor, "worker")
        assert hasattr(editor, "progress_dialog")

        # Check UI components
        assert editor.menuBar() is not None
        assert editor.statusBar() is not None
        assert editor.centralWidget() is not None

    def test_tab_widget_structure(self, editor):
        """Test all tabs are created"""
        tab_widget = editor.tab_widget

        # Verify tab count
        assert tab_widget.count() == 6

        # Verify tab names
        expected_tabs = [
            "Extract",
            "Edit Workflow",
            "Validate",
            "Reinsert",
            "Visual Tools",
            "Log",
        ]

        for i, expected in enumerate(expected_tabs):
            assert tab_widget.tabText(i) == expected

    def test_toolbar_exists(self, editor):
        """Test toolbar is created"""
        # Find toolbar widgets
        from PyQt6.QtWidgets import QToolBar

        toolbars = editor.findChildren(QToolBar)

        # Should have at least one toolbar
        assert len(toolbars) > 0

        # Check toolbar has actions
        toolbar = toolbars[0]
        actions = toolbar.actions()
        assert len(actions) > 0

        # Verify expected actions exist by checking their text
        action_texts = [action.text() for action in actions if action.text()]
        assert "Extract" in action_texts
        assert "Validate" in action_texts
        assert "Reinsert" in action_texts
        assert "Quick Action" in action_texts


@pytest.mark.gui
class TestExtractionTab:
    """Test extraction tab functionality"""

    def test_extraction_mode_selection(self, editor, qtbot):
        """Test extraction mode radio buttons"""
        # Switch to extraction tab
        editor.tab_widget.setCurrentIndex(0)

        # Test initial state
        assert editor.tile_mode_radio.isChecked()
        assert not editor.sheet_mode_radio.isChecked()

        # Use setChecked directly since qtbot.mouseClick might not work reliably
        # This tests the widget state changes, which is what matters for the logic
        editor.sheet_mode_radio.setChecked(True)
        assert editor.sheet_mode_radio.isChecked()
        # tile_mode_radio should be unchecked now since they're mutually exclusive radio buttons
        assert not editor.tile_mode_radio.isChecked()

        # Switch back to tile mode
        editor.tile_mode_radio.setChecked(True)
        assert editor.tile_mode_radio.isChecked()
        assert not editor.sheet_mode_radio.isChecked()

    def test_file_browsing(self, editor, qtbot, temp_files):
        """Test file browse buttons"""
        # Mock file dialog
        with patch.object(QFileDialog, "getOpenFileName") as mock_dialog:
            mock_dialog.return_value = (temp_files["vram"], "VRAM dumps (*.dmp *.bin)")

            # Click browse button
            qtbot.mouseClick(editor.extract_vram_btn, Qt.MouseButton.LeftButton)

            # Verify file path was set
            assert editor.extract_vram_input.text() == temp_files["vram"]

    def test_extraction_options(self, editor, qtbot):
        """Test extraction option widgets"""
        # Test offset spinbox
        editor.extract_offset_input.setValue(0x8000)
        assert editor.extract_offset_input.value() == 0x8000

        # Test size spinbox
        editor.extract_size_input.setValue(0x2000)
        assert editor.extract_size_input.value() == 0x2000

        # Test tiles per row
        editor.extract_tiles_row.setValue(8)
        assert editor.extract_tiles_row.value() == 8

        # Test guide checkbox
        editor.extract_guide_check.setChecked(False)
        assert not editor.extract_guide_check.isChecked()

    def test_extraction_validation(self, editor, qtbot):
        """Test extraction input validation"""
        # Try to extract without files
        with patch.object(QMessageBox, "warning") as mock_warning:
            editor.perform_extraction()

            # Should show warning
            mock_warning.assert_called_once()
            args = mock_warning.call_args[0]
            assert args[1] == "Input Error"
            assert args[2] == "Please select VRAM and CGRAM files"

    def test_successful_extraction(self, editor, qtbot, temp_files):
        """Test successful extraction workflow"""
        # Set up inputs
        editor.extract_vram_input.setText(temp_files["vram"])
        editor.extract_cgram_input.setText(temp_files["cgram"])
        editor.extract_offset_input.setValue(0xC000)
        editor.extract_size_input.setValue(0x1000)

        # Make sure tile mode is selected (default)
        assert editor.tile_mode_radio.isChecked()

        # Mock file dialog for output directory
        with patch.object(QFileDialog, "getExistingDirectory") as mock_dir:
            mock_dir.return_value = temp_files["dir"]

            # Mock the worker thread
            with patch("sprite_editor_unified.WorkflowWorker") as mock_worker_class:
                mock_worker = MagicMock()
                mock_worker_class.return_value = mock_worker

                # Trigger extraction
                editor.perform_extraction()

                # Verify worker was created with correct parameters
                mock_worker_class.assert_called_once()
                args = mock_worker_class.call_args[0]
                assert args[0] == "extract_tiles"  # Operation name
                assert isinstance(args[1], dict)  # Parameters dict

                # Check parameters
                params = args[1]
                assert params["vram_file"] == temp_files["vram"]
                assert params["cgram_file"] == temp_files["cgram"]
                assert params["offset"] == 0xC000
                assert params["size"] == 0x1000
                assert params["output_dir"] == temp_files["dir"]

                # Verify worker was started
                mock_worker.start.assert_called_once()


@pytest.mark.gui
class TestValidationTab:
    """Test validation tab functionality"""

    def test_validation_type_selection(self, editor, qtbot):
        """Test validation type combo box"""
        # Switch to validation tab
        editor.tab_widget.setCurrentIndex(2)

        # Find combo box
        combo = editor.validate_type_combo

        # Test options - check actual implementation
        assert combo.count() == 2
        assert combo.itemText(0) == "Individual Tiles (Folder)"
        assert combo.itemText(1) == "Sprite Sheet (PNG)"

        # Change selection
        combo.setCurrentIndex(1)
        assert combo.currentText() == "Sprite Sheet (PNG)"

    def test_validation_execution(self, editor, qtbot, temp_files):
        """Test validation workflow"""
        editor.tab_widget.setCurrentIndex(2)

        # Set input
        editor.validate_input.setText(temp_files["dir"])

        with patch("sprite_editor_unified.WorkflowWorker") as mock_worker_class:
            mock_worker = MagicMock()
            mock_worker_class.return_value = mock_worker

            # Trigger validation
            editor.perform_validation()

            # Verify worker creation
            mock_worker_class.assert_called_once()
            assert mock_worker.start.called


@pytest.mark.gui
class TestReinsertionTab:
    """Test reinsertion tab functionality"""

    def test_reinsertion_inputs(self, editor, qtbot, temp_files):
        """Test reinsertion input fields"""
        editor.tab_widget.setCurrentIndex(3)

        # Set inputs
        editor.reinsert_input.setText(temp_files["dir"])
        editor.reinsert_output.setText(temp_files["vram"])  # Output VRAM field

        # Test backup checkbox
        editor.reinsert_backup_check.setChecked(True)
        assert editor.reinsert_backup_check.isChecked()

        # Test preview checkbox
        editor.reinsert_preview_check.setChecked(False)
        assert not editor.reinsert_preview_check.isChecked()

    def test_reinsertion_validation(self, editor, qtbot):
        """Test reinsertion validation"""
        editor.tab_widget.setCurrentIndex(3)

        # Try without inputs
        with patch.object(QMessageBox, "warning") as mock_warning:
            editor.perform_reinsertion()

            mock_warning.assert_called_once()
            args = mock_warning.call_args[0]
            assert args[1] == "Input Error"
            assert "Please select sprites to reinsert" in args[2]


@pytest.mark.gui
class TestQuickActionDialog:
    """Test quick action dialog"""

    def test_dialog_creation(self, qtbot):
        """Test quick action dialog initialization"""
        dialog = QuickActionDialog(None)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Quick Action"
        assert hasattr(dialog, "action_combo")
        assert hasattr(dialog, "options_widget")
        assert hasattr(dialog, "vram_input")
        assert hasattr(dialog, "cgram_input")

    def test_action_selection(self, qtbot):
        """Test action type selection"""
        dialog = QuickActionDialog(None)
        qtbot.addWidget(dialog)

        # Test initial state
        assert dialog.action_combo.currentIndex() == 0

        # Test available actions
        assert dialog.action_combo.count() > 0

        # Change action and verify it changes
        initial_text = dialog.action_combo.currentText()
        dialog.action_combo.setCurrentIndex(1)
        assert dialog.action_combo.currentText() != initial_text

    def test_dialog_execution(self, qtbot, temp_files):
        """Test executing quick action"""
        dialog = QuickActionDialog(None)
        qtbot.addWidget(dialog)

        # Set up extract action
        dialog.action_combo.setCurrentIndex(0)  # "Extract Kirby sprites only"
        dialog.vram_input.setText(temp_files["vram"])
        dialog.cgram_input.setText(temp_files["cgram"])

        # Test get_params method
        params = dialog.get_params()
        assert params["action"] == dialog.action_combo.currentText()
        assert params["vram_file"] == temp_files["vram"]
        assert params["cgram_file"] == temp_files["cgram"]

        # Since "Kirby" is in the action text, it should set specific offset/size
        assert params["offset"] == 0xC000
        assert params["size"] == 0x400


@pytest.mark.gui
class TestVisualTools:
    """Test visual tools tab"""

    def test_visual_tool_buttons(self, editor, qtbot):
        """Test visual tool button availability"""
        editor.tab_widget.setCurrentIndex(4)

        # Find buttons
        buttons = editor.tab_widget.currentWidget().findChildren(QPushButton)
        button_texts = [btn.text() for btn in buttons if btn.text()]

        expected_buttons = [
            "Create Palette Reference",
            "Generate Coverage Map",
            "Create Visual Summary",
            "Compare Before/After",
        ]

        for expected in expected_buttons:
            assert expected in button_texts

    def test_palette_reference_creation(self, editor, qtbot, temp_files):
        """Test creating palette reference"""
        editor.tab_widget.setCurrentIndex(4)

        # Mock QMessageBox to prevent hanging on dialog
        with patch.object(QMessageBox, "information") as mock_info:
            # The method currently just shows a "not implemented" message
            editor.create_palette_reference()

            # Verify the information dialog was shown
            mock_info.assert_called_once()
            args = mock_info.call_args[0]
            assert args[1] == "Palette Reference"
            assert "not yet implemented" in args[2]


@pytest.mark.gui
class TestLogTab:
    """Test log tab functionality"""

    def test_log_display(self, editor, qtbot):
        """Test log message display"""
        editor.tab_widget.setCurrentIndex(5)

        # Add log message
        test_message = "Test log message"
        editor.log(test_message)

        # Verify message appears
        log_text = editor.log_text.toPlainText()
        assert test_message in log_text
        assert editor.log_text.textCursor().atEnd()  # Auto-scroll

    def test_log_messages(self, editor):
        """Test different log message types"""
        # Test different log types
        editor.log("INFO: Information message")
        editor.log("WARNING: Warning message")
        editor.log("ERROR: Error message")
        editor.log("SUCCESS: Success message")

        # Get log content
        log_content = editor.log_text.toPlainText()

        # Verify all messages are present
        assert "INFO: Information message" in log_content
        assert "WARNING: Warning message" in log_content
        assert "ERROR: Error message" in log_content
        assert "SUCCESS: Success message" in log_content

        # Verify timestamps are added
        lines = log_content.strip().split("\n")
        for line in lines:
            assert line.startswith("[")  # Each line should start with timestamp


@pytest.mark.gui
class TestMenuSystem:
    """Test menu functionality"""

    def test_file_menu(self, editor):
        """Test file menu structure"""
        # Get the file menu (first menu in menubar)
        menubar = editor.menuBar()
        file_menu_action = menubar.actions()[0]
        file_menu = file_menu_action.menu()

        # Check menu actions exist
        action_texts = [
            action.text() for action in file_menu.actions() if action.text()
        ]

        expected_actions = [
            "&New Project",
            "&Open Project",
            "&Save Project",
            "Recent Projects",
        ]

        for expected in expected_actions:
            assert any(expected in text for text in action_texts)

    def test_recent_files_menu(self, editor, temp_files):
        """Test recent files submenu"""
        # Add a recent file
        editor.recent_files = [temp_files["dir"] + "/test.ksproj"]
        editor.update_recent_menu()

        # Check menu was updated
        assert len(editor.recent_menu.actions()) == 1
        assert "test.ksproj" in editor.recent_menu.actions()[0].text()

    def test_help_menu(self, editor):
        """Test help menu actions"""
        # Find help menu
        help_menu = None
        menubar = editor.menuBar()
        for action in menubar.actions():
            if action.text() == "&Help":  # Note the & for menu accelerator
                help_menu = action.menu()
                break

        assert help_menu is not None

        # Test about dialog
        with patch.object(QMessageBox, "about") as mock_about:
            # Find and trigger about action
            for action in help_menu.actions():
                if "About" in action.text():
                    action.trigger()
                    break

            mock_about.assert_called_once()


@pytest.mark.gui
class TestProgressDialog:
    """Test progress dialog functionality"""

    def test_progress_dialog_lifecycle(self, editor, qtbot):
        """Test showing/hiding progress dialog"""
        # Show progress
        editor.show_progress("Test Operation", 100)

        assert editor.progress_dialog is not None
        assert editor.progress_dialog.isVisible()
        assert editor.progress_dialog.labelText() == "Test Operation"
        assert editor.progress_dialog.maximum() == 100

        # Update progress
        editor.update_progress(50, "Half way done")
        assert editor.progress_dialog.value() == 50
        assert editor.progress_dialog.labelText() == "Half way done"

        # Hide progress
        editor.hide_progress()
        assert editor.progress_dialog is None


@pytest.mark.gui
class TestWorkerThread:
    """Test worker thread integration"""

    def test_worker_signals(self, qtbot):
        """Test worker thread signal emission"""
        # Create worker with correct parameters
        params = {"input_path": "/test/path", "type": "folder"}
        worker = WorkflowWorker("validate", params)

        # Connect signal spy for finished signal
        finished_spy = qtbot.waitSignal(worker.finished, timeout=1000)

        # Mock the internal validation method
        with patch.object(worker, "_validate") as mock_validate:
            # Make _validate emit the finished signal
            def emit_finished():
                worker.finished.emit(True, "Validation completed successfully")

            mock_validate.side_effect = emit_finished

            # Run worker
            worker.run()

            # Verify finished signal was emitted
            assert finished_spy.signal_triggered
            success, message = finished_spy.args
            assert success is True
            assert "completed" in message


@pytest.mark.gui
class TestKeyboardShortcuts:
    """Test keyboard shortcuts"""

    def test_tab_navigation(self, editor, qtbot):
        """Test tab navigation"""
        # Test programmatic tab switching
        editor.tab_widget.setCurrentIndex(0)
        assert editor.tab_widget.currentIndex() == 0

        editor.tab_widget.setCurrentIndex(1)
        assert editor.tab_widget.currentIndex() == 1

        # Verify tab count
        assert editor.tab_widget.count() == 6

    def test_menu_shortcuts(self, editor, qtbot):
        """Test menu action shortcuts"""
        # Test that menu actions have shortcuts
        menubar = editor.menuBar()
        file_menu = menubar.actions()[0].menu()

        # Check that standard shortcuts are set
        for action in file_menu.actions():
            if action.text() == "&New Project":
                # New should have Ctrl+N shortcut
                assert action.shortcut() == QKeySequence.StandardKey.New
            elif action.text() == "&Open Project":
                # Open should have Ctrl+O shortcut
                assert action.shortcut() == QKeySequence.StandardKey.Open
            elif action.text() == "&Save Project":
                # Save should have Ctrl+S shortcut
                assert action.shortcut() == QKeySequence.StandardKey.Save
