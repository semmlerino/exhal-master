"""
Dialog Test Helpers - Real Qt Dialog Testing Utilities

This module provides helpers for testing Qt dialogs with real components,
focusing on interaction patterns, state validation, and cross-dialog communication.

Key Features:
- Dialog factory with real widgets
- Interaction helpers for buttons, sliders, inputs
- Modal dialog testing patterns
- Cross-dialog communication testing
- State persistence validation
"""
from __future__ import annotations

import weakref
from collections.abc import Callable
from typing import Any, TypeVar

from PySide6.QtCore import QObject, QPoint, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QWidget,
)

from .qt_real_testing import EventLoopHelper, QtTestCase

D = TypeVar("D", bound=QDialog)

class DialogTestHelper(QtTestCase):
    """Helper class for testing Qt dialogs with real components."""

    def open_dialog(self, dialog: QDialog, modal: bool = False) -> QDialog:
        """
        Open a dialog for testing.

        Args:
            dialog: Dialog to open
            modal: Whether to open as modal

        Returns:
            The dialog instance
        """
        if modal:
            # For modal dialogs, use show() and process events
            dialog.setModal(True)
            dialog.show()
        else:
            dialog.show()

        # Process events to ensure dialog is visible
        EventLoopHelper.process_events(10)

        # Track for cleanup
        self.widgets.append(weakref.ref(dialog))

        return dialog

    def close_dialog(self, dialog: QDialog, accept: bool = True):
        """
        Close a dialog.

        Args:
            dialog: Dialog to close
            accept: Whether to accept (True) or reject (False)
        """
        if accept:
            dialog.accept()
        else:
            dialog.reject()

        EventLoopHelper.process_events(10)

    def click_button(self, button: QAbstractButton):
        """
        Click a button and wait for events.

        Args:
            button: Button to click
        """
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        EventLoopHelper.process_events(10)

    def click_dialog_button(self, dialog: QDialog, button_role: QDialogButtonBox.StandardButton):
        """
        Click a standard dialog button.

        Args:
            dialog: Dialog containing the button box
            button_role: Standard button role (Ok, Cancel, etc.)
        """
        button_box = dialog.findChild(QDialogButtonBox)
        if button_box:
            button = button_box.button(button_role)
            if button:
                self.click_button(button)

    def set_slider_value(self, slider: QSlider, value: int, use_mouse: bool = False):
        """
        Set slider value with optional mouse simulation.

        Args:
            slider: Slider widget
            value: Value to set
            use_mouse: Whether to simulate mouse drag
        """
        if use_mouse:
            # Calculate position for value
            min_val = slider.minimum()
            max_val = slider.maximum()
            ratio = (value - min_val) / (max_val - min_val)

            # Get slider geometry
            rect = slider.rect()
            if slider.orientation() == Qt.Orientation.Horizontal:
                x = int(rect.left() + ratio * rect.width())
                y = rect.center().y()
            else:
                x = rect.center().x()
                y = int(rect.bottom() - ratio * rect.height())

            # Simulate mouse press, move, release
            pos = QPoint(x, y)
            QTest.mousePress(slider, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos)
            EventLoopHelper.process_events(5)
            QTest.mouseRelease(slider, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos)
        else:
            slider.setValue(value)

        EventLoopHelper.process_events(10)

    def set_input_text(self, input_widget: QLineEdit | QTextEdit, text: str):
        """
        Set text in an input widget.

        Args:
            input_widget: Line edit or text edit widget
            text: Text to set
        """
        input_widget.clear()
        input_widget.setFocus()
        QTest.keyClicks(input_widget, text)
        EventLoopHelper.process_events(10)

    def select_combo_item(self, combo: QComboBox, index: int | None = None, text: str | None = None):
        """
        Select item in combo box.

        Args:
            combo: Combo box widget
            index: Item index to select
            text: Item text to select (alternative to index)
        """
        if text is not None:
            index = combo.findText(text)
            if index == -1:
                raise ValueError(f"Text '{text}' not found in combo box")

        if index is not None:
            combo.setCurrentIndex(index)
            EventLoopHelper.process_events(10)

    def check_checkbox(self, checkbox: QCheckBox, checked: bool):
        """
        Set checkbox state.

        Args:
            checkbox: Checkbox widget
            checked: Whether to check or uncheck
        """
        checkbox.setChecked(checked)
        EventLoopHelper.process_events(10)

    def select_tab(self, tab_widget: QTabWidget, index: int | None = None, title: str | None = None):
        """
        Select a tab in tab widget.

        Args:
            tab_widget: Tab widget
            index: Tab index to select
            title: Tab title to select (alternative to index)
        """
        if title is not None:
            for i in range(tab_widget.count()):
                if tab_widget.tabText(i) == title:
                    index = i
                    break
            else:
                raise ValueError(f"Tab '{title}' not found")

        if index is not None:
            tab_widget.setCurrentIndex(index)
            EventLoopHelper.process_events(10)

    def get_dialog_state(self, dialog: QDialog) -> dict[str, Any]:
        """
        Extract current state of all input widgets in dialog.

        Args:
            dialog: Dialog to extract state from

        Returns:
            Dictionary of widget states
        """
        state = {}

        # Line edits
        for line_edit in dialog.findChildren(QLineEdit):
            if line_edit.objectName():
                state[line_edit.objectName()] = line_edit.text()

        # Spin boxes
        for spin_box in dialog.findChildren(QSpinBox):
            if spin_box.objectName():
                state[spin_box.objectName()] = spin_box

        # Checkboxes
        for checkbox in dialog.findChildren(QCheckBox):
            if checkbox.objectName():
                state[checkbox.objectName()] = checkbox.isChecked()

        # Radio buttons
        for radio in dialog.findChildren(QRadioButton):
            if radio.objectName():
                state[radio.objectName()] = radio.isChecked()

        # Combo boxes
        for combo in dialog.findChildren(QComboBox):
            if combo.objectName():
                state[combo.objectName()] = {
                    "index": combo.currentIndex(),
                    "text": combo.currentText()
                }

        # Sliders
        for slider in dialog.findChildren(QSlider):
            if slider.objectName():
                state[slider.objectName()] = slider

        # Tab widgets
        for tab_widget in dialog.findChildren(QTabWidget):
            if tab_widget.objectName():
                state[tab_widget.objectName()] = {
                    "index": tab_widget.currentIndex(),
                    "tab": tab_widget.tabText(tab_widget.currentIndex())
                }

        return state

    def restore_dialog_state(self, dialog: QDialog, state: dict[str, Any]):
        """
        Restore dialog state from dictionary.

        Args:
            dialog: Dialog to restore state to
            state: State dictionary from get_dialog_state
        """
        for name, value in state.items():
            widget = dialog.findChild(QWidget, name)
            if not widget:
                continue

            if isinstance(widget, QLineEdit):
                widget.setText(value)
            elif isinstance(widget, QSpinBox):
                widget.setValue(value)
            elif isinstance(widget, (QCheckBox, QRadioButton)):
                widget.setChecked(value)
            elif isinstance(widget, QComboBox):
                if isinstance(value, dict):
                    widget.setCurrentIndex(value.get("index", 0))
                else:
                    widget.setCurrentIndex(value)
            elif isinstance(widget, QSlider):
                widget.setValue(value)
            elif isinstance(widget, QTabWidget):
                if isinstance(value, dict):
                    widget.setCurrentIndex(value.get("index", 0))
                else:
                    widget.setCurrentIndex(value)

        EventLoopHelper.process_events(10)

class DialogFactory:
    """Factory for creating test dialogs with standard components."""

    @staticmethod
    def create_simple_dialog(
        title: str = "Test Dialog",
        buttons: QDialogButtonBox.StandardButton = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    ) -> QDialog:
        """
        Create a simple dialog with button box.

        Args:
            title: Dialog title
            buttons: Standard buttons to include

        Returns:
            Dialog instance
        """
        dialog = QDialog()
        dialog.setWindowTitle(title)

        from PySide6.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(dialog)

        # Add button box
        button_box = QDialogButtonBox(buttons)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        return dialog

    @staticmethod
    def create_input_dialog(
        title: str = "Input Dialog",
        fields: dict[str, type | None] | None = None
    ) -> QDialog:
        """
        Create a dialog with input fields.

        Args:
            title: Dialog title
            fields: Dictionary of field names and types

        Returns:
            Dialog with input fields
        """
        dialog = QDialog()
        dialog.setWindowTitle(title)

        from PySide6.QtWidgets import QFormLayout, QVBoxLayout

        main_layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()

        fields = fields or {"text": str, "number": int, "checked": bool}

        for field_name, field_type in fields.items():
            if field_type is str:
                widget = QLineEdit()
                widget.setObjectName(f"{field_name}_input")
            elif field_type is int:
                widget = QSpinBox()
                widget.setObjectName(f"{field_name}_input")
            elif field_type is bool:
                widget = QCheckBox()
                widget.setObjectName(f"{field_name}_input")
            else:
                continue

            form_layout.addRow(field_name.title() + ":", widget)

        main_layout.addLayout(form_layout)

        # Add button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        main_layout.addWidget(button_box)

        return dialog

    @staticmethod
    def create_tab_dialog(
        title: str = "Tab Dialog",
        tabs: list[str | None] | None = None
    ) -> QDialog:
        """
        Create a dialog with tab widget.

        Args:
            title: Dialog title
            tabs: List of tab names

        Returns:
            Dialog with tab widget
        """
        dialog = QDialog()
        dialog.setWindowTitle(title)

        from PySide6.QtWidgets import QVBoxLayout

        layout = QVBoxLayout(dialog)

        tab_widget = QTabWidget()
        tab_widget.setObjectName("main_tabs")

        tabs = tabs or ["Tab 1", "Tab 2", "Tab 3"]

        for tab_name in tabs:
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            label = QLabel(f"Content for {tab_name}")
            tab_layout.addWidget(label)
            tab_widget.addTab(tab, tab_name)

        layout.addWidget(tab_widget)

        # Add button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        return dialog

class ModalDialogTester:
    """Helper for testing modal dialogs."""

    @staticmethod
    def test_modal_dialog(
        dialog_factory: Callable[[], QDialog],
        test_func: Callable[[QDialog], None],
        auto_close: bool = True,
        close_delay_ms: int = 100
    ):
        """
        Test a modal dialog by scheduling actions.

        Args:
            dialog_factory: Function that creates and returns the dialog
            test_func: Function to test the dialog
            auto_close: Whether to automatically close dialog
            close_delay_ms: Delay before auto-closing
        """
        dialog: QDialog | None = None

        def scheduled_test():
            nonlocal dialog
            # Give dialog time to open
            EventLoopHelper.process_events(50)

            # Find the dialog
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, QDialog) and widget.isVisible():
                    dialog = widget
                    break

            if dialog:
                # Run test function
                test_func(dialog)

                # Auto-close if requested
                if auto_close:
                    QTimer.singleShot(close_delay_ms, dialog.accept)

        # Schedule test to run after dialog opens
        QTimer.singleShot(0, scheduled_test)

        # Create and execute dialog
        dialog = dialog_factory()
        result = dialog.exec()

        return result

class CrossDialogCommunicationTester:
    """Helper for testing communication between dialogs."""

    def __init__(self):
        """Initialize cross-dialog tester."""
        self.signal_log: list[tuple[str, Any]] = []
        self.dialogs: list[QDialog] = []

    def create_connected_dialogs(
        self,
        dialog_specs: list[dict[str, Any]]
    ) -> list[QDialog]:
        """
        Create multiple dialogs with signal connections.

        Args:
            dialog_specs: List of dialog specifications

        Returns:
            List of created dialogs
        """
        for spec in dialog_specs:
            dialog = spec.get("factory", DialogFactory.create_simple_dialog)()

            # Add custom signals if specified
            if "signals" in spec:
                for signal_name, signal_type in spec["signals"].items():
                    # Create signal holder as Qt signals must be class attributes
                    class SignalHolder(QObject):
                        pass

                    setattr(SignalHolder, signal_name, signal_type)
                    holder = SignalHolder()
                    dialog._signal_holder = holder
                    setattr(dialog, signal_name, getattr(holder, signal_name))

            self.dialogs.append(dialog)

        return self.dialogs

    def connect_dialogs(
        self,
        source_dialog: QDialog,
        source_signal: str,
        target_dialog: QDialog,
        target_slot: str | Callable
    ):
        """
        Connect signal from one dialog to slot in another.

        Args:
            source_dialog: Dialog emitting signal
            source_signal: Signal name
            target_dialog: Dialog receiving signal
            target_slot: Slot name or callable
        """
        signal = getattr(source_dialog, source_signal, None)
        if not signal:
            # Try signal holder
            holder = getattr(source_dialog, "_signal_holder", None)
            if holder:
                signal = getattr(holder, source_signal, None)

        if signal:
            if isinstance(target_slot, str):
                slot = getattr(target_dialog, target_slot)
            else:
                slot = target_slot

            # Log connections
            def logged_slot(*args):
                self.signal_log.append((source_signal, args))
                slot(*args)

            signal.connect(logged_slot)

    def verify_communication(
        self,
        expected_signals: list[tuple[str, Any]]
    ) -> bool:
        """
        Verify expected signals were emitted.

        Args:
            expected_signals: List of (signal_name, args) tuples

        Returns:
            True if all expected signals were logged
        """
        return all(expected in self.signal_log for expected in expected_signals)

    def clear_log(self):
        """Clear signal log."""
        self.signal_log.clear()

