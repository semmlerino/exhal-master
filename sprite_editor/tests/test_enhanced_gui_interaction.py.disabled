#!/usr/bin/env python3
"""
Enhanced GUI interaction tests using pytest-qt features
Demonstrates advanced qtbot usage for better widget testing
"""

import os

import pytest
from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from sprite_editor_unified import UnifiedSpriteEditor


@pytest.fixture
def sample_widget(qtbot):
    """Create a sample widget with various controls for testing"""

    class TestWidget(QWidget):
        button_clicked = pyqtSignal()
        text_changed = pyqtSignal(str)

        def __init__(self):
            super().__init__()
            layout = QVBoxLayout()

            self.button = QPushButton("Click Me")
            self.button.clicked.connect(self.button_clicked.emit)

            self.line_edit = QLineEdit()
            self.line_edit.textChanged.connect(self.text_changed.emit)

            self.checkbox = QCheckBox("Test Option")
            self.spinbox = QSpinBox()
            self.spinbox.setRange(0, 100)

            self.combo = QComboBox()
            self.combo.addItems(["Option 1", "Option 2", "Option 3"])

            self.text_edit = QTextEdit()

            layout.addWidget(self.button)
            layout.addWidget(self.line_edit)
            layout.addWidget(self.checkbox)
            layout.addWidget(self.spinbox)
            layout.addWidget(self.combo)
            layout.addWidget(self.text_edit)

            self.setLayout(layout)

    widget = TestWidget()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


@pytest.mark.gui
class TestEnhancedWidgetInteraction:
    """Test enhanced widget interactions using qtbot"""

    def test_button_click_with_qtbot(self, sample_widget, qtbot):
        """Test button clicking using qtbot.mouseClick"""
        # Spy on the signal
        with qtbot.waitSignal(sample_widget.button_clicked, timeout=1000) as blocker:
            # Click the button using qtbot
            qtbot.mouseClick(sample_widget.button, Qt.MouseButton.LeftButton)

        # Signal should have been emitted
        assert blocker.signal_triggered

    def test_keyboard_input_with_qtbot(self, sample_widget, qtbot):
        """Test keyboard input using qtbot.keyClicks"""
        # Focus the line edit
        sample_widget.line_edit.setFocus()

        # Type text using qtbot
        test_text = "Hello PyQt!"
        qtbot.keyClicks(sample_widget.line_edit, test_text)

        # Verify text was entered
        assert sample_widget.line_edit.text() == test_text

    def test_keyboard_shortcuts(self, sample_widget, qtbot):
        """Test keyboard shortcuts using qtbot.keyClick"""
        # Set some text
        sample_widget.line_edit.setText("Test Text")
        sample_widget.line_edit.setFocus()

        # Select all with Ctrl+A
        qtbot.keyClick(
            sample_widget.line_edit, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier
        )

        # Delete selected text
        qtbot.keyClick(sample_widget.line_edit, Qt.Key.Key_Delete)

        # Text should be empty
        assert sample_widget.line_edit.text() == ""

    def test_spinbox_interaction(self, sample_widget, qtbot):
        """Test spinbox interaction with keyboard"""
        sample_widget.spinbox.setFocus()

        # Set initial value
        sample_widget.spinbox.setValue(50)

        # Press up arrow multiple times
        for _ in range(5):
            qtbot.keyClick(sample_widget.spinbox, Qt.Key.Key_Up)

        assert sample_widget.spinbox.value() == 55

        # Press down arrow
        for _ in range(10):
            qtbot.keyClick(sample_widget.spinbox, Qt.Key.Key_Down)

        assert sample_widget.spinbox.value() == 45

    def test_combobox_interaction(self, sample_widget, qtbot):
        """Test combobox interaction"""
        # Click to open dropdown
        qtbot.mouseClick(sample_widget.combo, Qt.MouseButton.LeftButton)

        # Navigate with keyboard
        qtbot.keyClick(sample_widget.combo, Qt.Key.Key_Down)
        qtbot.keyClick(sample_widget.combo, Qt.Key.Key_Down)
        qtbot.keyClick(sample_widget.combo, Qt.Key.Key_Return)

        assert sample_widget.combo.currentText() == "Option 3"
        assert sample_widget.combo.currentIndex() == 2

    def test_checkbox_space_toggle(self, sample_widget, qtbot):
        """Test checkbox toggling with space key"""
        sample_widget.checkbox.setFocus()

        initial_state = sample_widget.checkbox.isChecked()

        # Toggle with space
        qtbot.keyClick(sample_widget.checkbox, Qt.Key.Key_Space)
        assert sample_widget.checkbox.isChecked() != initial_state

        # Toggle back
        qtbot.keyClick(sample_widget.checkbox, Qt.Key.Key_Space)
        assert sample_widget.checkbox.isChecked() == initial_state

    def test_text_edit_multiline(self, sample_widget, qtbot):
        """Test multiline text input in QTextEdit"""
        sample_widget.text_edit.setFocus()

        # Type multiple lines
        qtbot.keyClicks(sample_widget.text_edit, "Line 1")
        qtbot.keyClick(sample_widget.text_edit, Qt.Key.Key_Return)
        qtbot.keyClicks(sample_widget.text_edit, "Line 2")
        qtbot.keyClick(sample_widget.text_edit, Qt.Key.Key_Return)
        qtbot.keyClicks(sample_widget.text_edit, "Line 3")

        text = sample_widget.text_edit.toPlainText()
        lines = text.strip().split("\n")
        assert len(lines) == 3
        assert lines[0] == "Line 1"
        assert lines[1] == "Line 2"
        assert lines[2] == "Line 3"

    def test_wait_until_condition(self, sample_widget, qtbot):
        """Test waiting for a condition using qtbot.waitUntil"""

        # Simulate async operation
        def delayed_update():
            sample_widget.line_edit.setText("Updated!")

        QTimer.singleShot(100, delayed_update)

        # Wait until text changes
        qtbot.waitUntil(
            lambda: sample_widget.line_edit.text() == "Updated!", timeout=1000
        )

        assert sample_widget.line_edit.text() == "Updated!"

    def test_mouse_drag_simulation(self, sample_widget, qtbot):
        """Test mouse drag operations"""
        # This would be useful for testing drag-and-drop or selection
        # For demonstration, we'll select text in the line edit
        sample_widget.line_edit.setText("Select this text")
        sample_widget.line_edit.setFocus()

        # Get widget position
        widget_pos = sample_widget.line_edit.rect()
        start_pos = QPoint(widget_pos.left() + 5, widget_pos.center().y())
        end_pos = QPoint(widget_pos.right() - 5, widget_pos.center().y())

        # Simulate drag to select all text
        qtbot.mousePress(
            sample_widget.line_edit, Qt.MouseButton.LeftButton, pos=start_pos
        )
        qtbot.mouseMove(sample_widget.line_edit, pos=end_pos)
        qtbot.mouseRelease(
            sample_widget.line_edit, Qt.MouseButton.LeftButton, pos=end_pos
        )

        # Check if text is selected
        assert sample_widget.line_edit.hasSelectedText()
        assert len(sample_widget.line_edit.selectedText()) > 0


@pytest.mark.gui
class TestRealApplicationInteraction:
    """Test real application GUI interactions"""

    def test_extraction_workflow_with_clicks(self, qtbot):
        """Test extraction workflow using actual mouse clicks"""
        editor = UnifiedSpriteEditor()
        qtbot.addWidget(editor)
        editor.show()
        qtbot.waitExposed(editor)

        # Navigate to extraction tab by clicking
        editor.tab_widget.widget(0)
        tab_bar = editor.tab_widget.tabBar()
        tab_rect = tab_bar.tabRect(0)
        qtbot.mouseClick(tab_bar, Qt.MouseButton.LeftButton, pos=tab_rect.center())

        # Verify we're on extraction tab
        assert editor.tab_widget.currentIndex() == 0

        # Test offset spinbox interaction
        offset_spinbox = editor.extract_offset_input
        offset_spinbox.setFocus()

        # Clear and type new value
        offset_spinbox.clear()
        qtbot.keyClicks(offset_spinbox, "C000")

        # Verify hex input was accepted
        assert offset_spinbox.value() == 0xC000

    def test_dialog_interaction(self, qtbot):
        """Test interacting with dialogs"""

        # Create a simple dialog for testing
        def show_test_dialog():
            msg = QMessageBox()
            msg.setWindowTitle("Test Dialog")
            msg.setText("This is a test message")
            msg.setStandardButtons(
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
            )

            # Use qtbot to handle the dialog
            def handle_dialog():
                # Wait a bit for dialog to appear
                qtbot.wait(100)
                # Click OK button
                ok_button = msg.button(QMessageBox.StandardButton.Ok)
                qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)

            QTimer.singleShot(10, handle_dialog)
            result = msg.exec()
            return result == QMessageBox.StandardButton.Ok

        # Test the dialog
        result = show_test_dialog()
        assert result is True

    def test_tab_keyboard_navigation(self, qtbot):
        """Test tab navigation with keyboard"""
        editor = UnifiedSpriteEditor()
        qtbot.addWidget(editor)
        editor.show()
        qtbot.waitExposed(editor)

        # Focus on tab widget
        editor.tab_widget.setFocus()

        # Navigate through tabs with Ctrl+Tab
        initial_tab = editor.tab_widget.currentIndex()

        # Move to next tab
        qtbot.keyClick(
            editor.tab_widget, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier
        )
        assert (
            editor.tab_widget.currentIndex()
            == (initial_tab + 1) % editor.tab_widget.count()
        )

    def test_focus_chain_navigation(self, qtbot):
        """Test navigating through widgets with Tab key"""
        editor = UnifiedSpriteEditor()
        qtbot.addWidget(editor)
        editor.show()
        qtbot.waitExposed(editor)

        # Go to extraction tab
        editor.tab_widget.setCurrentIndex(0)

        # Start with first input
        editor.extract_vram_input.setFocus()
        # Wait for focus to be set
        qtbot.waitUntil(lambda: editor.extract_vram_input.hasFocus(), timeout=1000)

        # Tab to next widget
        qtbot.keyClick(editor.extract_vram_input, Qt.Key.Key_Tab)
        # Should move to browse button or next input
        assert not editor.extract_vram_input.hasFocus()


@pytest.mark.gui
class TestSignalMonitoring:
    """Test advanced signal monitoring with qtbot"""

    def test_multiple_signal_monitoring(self, sample_widget, qtbot):
        """Test monitoring multiple signals simultaneously"""
        # Monitor both signals
        with qtbot.waitSignals(
            [sample_widget.button_clicked, sample_widget.text_changed], timeout=1000
        ) as blocker:
            # Trigger both signals
            qtbot.mouseClick(sample_widget.button, Qt.MouseButton.LeftButton)
            qtbot.keyClicks(sample_widget.line_edit, "test")

        # Both signals should have been emitted
        assert blocker.signal_triggered

    def test_signal_argument_capture(self, sample_widget, qtbot):
        """Test capturing signal arguments"""
        # Clear any existing text
        sample_widget.line_edit.clear()

        # Since textChanged emits on each character, capture the last emission
        # by setting text directly
        with qtbot.waitSignal(sample_widget.text_changed, timeout=1000) as blocker:
            sample_widget.line_edit.setText("captured")

        # Check captured arguments
        assert blocker.args == ["captured"]

    def test_signal_not_emitted(self, sample_widget, qtbot):
        """Test asserting a signal is NOT emitted"""
        # Use qtbot.wait to ensure any potential signal would have time to emit
        with qtbot.assertNotEmitted(sample_widget.button_clicked):
            # Do something that should NOT trigger the signal
            sample_widget.line_edit.setText("This shouldn't trigger button signal")
            qtbot.wait(100)  # Wait a bit to ensure no delayed signals


# Example of using xvfb-run for tests requiring OpenGL or full rendering
# Run with: xvfb-run -a python -m pytest test_enhanced_gui_interaction.py
@pytest.mark.skipif(
    os.environ.get("DISPLAY") is None
    and os.environ.get("QT_QPA_PLATFORM") == "offscreen",
    reason="Requires display for OpenGL rendering",
)
class TestOpenGLRendering:
    """Tests that require full graphical rendering"""

    def test_opengl_widget_rendering(self, qtbot):
        """Test that would require OpenGL support"""
        # This would be for testing OpenGL-based widgets
        # Skipped in headless mode
