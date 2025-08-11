"""
UI Interaction Examples - Demonstrates advanced qtbot usage patterns

This file provides examples of sophisticated UI testing patterns using qtbot
for testing complex user interactions in SpritePal.

Examples include:
- Mouse drag operations on sliders
- Keyboard shortcuts testing
- Modal dialog interactions
- Multi-widget coordination
- Signal timing and sequencing
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest, QSignalSpy
from PySide6.QtWidgets import (
    QApplication, QWidget, QSlider, QPushButton, QDialog,
    QLineEdit, QLabel, QVBoxLayout, QHBoxLayout
)

# Test markers
pytestmark = [
    pytest.mark.gui,
    pytest.mark.integration, 
    pytest.mark.serial,
    pytest.mark.examples,  # Example tests
]

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.main_window import MainWindow
from core.managers.registry import initialize_managers, cleanup_managers


class TestUIInteractionExamples:
    """
    Examples of advanced UI testing patterns with qtbot.
    
    These tests demonstrate sophisticated user interaction testing
    that can be applied throughout the SpritePal test suite.
    """

    @pytest.fixture(autouse=True)
    def setup_test_environment(self, qtbot):
        """Set up test environment for each example test."""
        cleanup_managers()
        initialize_managers("SpritePal-UIExamples")
        
        yield
        
        cleanup_managers()

    @pytest.mark.gui
    def test_precise_slider_drag_interaction(self, qtbot):
        """
        Example: Test precise slider dragging with mouse coordinates.
        
        Demonstrates:
        - Mouse press/move/release sequences
        - Coordinate-based interactions
        - Value change verification
        """
        # Create test dialog with slider
        class TestSliderDialog(QDialog):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("Slider Drag Test")
                self.resize(400, 200)
                
                layout = QVBoxLayout(self)
                
                self.label = QLabel("Offset: 0")
                layout.addWidget(self.label)
                
                self.slider = QSlider(Qt.Orientation.Horizontal)
                self.slider.setRange(0, 1000000)
                self.slider.setValue(500000)
                self.slider.setGeometry(50, 50, 300, 30)
                layout.addWidget(self.slider)
                
                # Connect slider to label
                self.slider.valueChanged.connect(
                    lambda v: self.label.setText(f"Offset: {v}")
                )
        
        dialog = TestSliderDialog()
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        
        slider = dialog.slider
        initial_value = slider.value()
        
        # Get slider geometry for precise clicking
        slider_rect = slider.geometry()
        slider_center = slider_rect.center()
        
        # Calculate drag positions (25% and 75% of slider width)
        left_pos = QPoint(slider_rect.x() + slider_rect.width() // 4, slider_center.y())
        right_pos = QPoint(slider_rect.x() + 3 * slider_rect.width() // 4, slider_center.y())
        
        # Test precise drag from center to right
        qtbot.mousePress(slider, Qt.MouseButton.LeftButton, pos=slider_center)
        qtbot.mouseMove(slider, right_pos)
        qtbot.mouseRelease(slider, Qt.MouseButton.LeftButton, pos=right_pos)
        qtbot.wait(50)
        
        # Verify slider moved to higher value
        after_drag_value = slider.value()
        assert after_drag_value > initial_value, f"Slider should move right (was {initial_value}, now {after_drag_value})"
        
        # Test drag from right back to left
        qtbot.mousePress(slider, Qt.MouseButton.LeftButton, pos=right_pos)
        qtbot.mouseMove(slider, left_pos)
        qtbot.mouseRelease(slider, Qt.MouseButton.LeftButton, pos=left_pos)
        qtbot.wait(50)
        
        final_value = slider.value()
        assert final_value < after_drag_value, f"Slider should move left (was {after_drag_value}, now {final_value})"
        
        # Verify label updated correctly
        expected_text = f"Offset: {final_value}"
        assert dialog.label.text() == expected_text, f"Label should show '{expected_text}'"

    @pytest.mark.gui
    def test_keyboard_shortcuts_and_focus(self, qtbot):
        """
        Example: Test keyboard shortcuts and focus management.
        
        Demonstrates:
        - Keyboard shortcut activation
        - Focus testing and manipulation
        - Tab order verification
        """
        # Create test dialog with multiple focusable widgets
        class TestKeyboardDialog(QDialog):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("Keyboard Test")
                self.resize(300, 200)
                
                layout = QVBoxLayout(self)
                
                self.input1 = QLineEdit("Input 1")
                self.input1.setObjectName("input1")
                layout.addWidget(self.input1)
                
                self.input2 = QLineEdit("Input 2")
                self.input2.setObjectName("input2")
                layout.addWidget(self.input2)
                
                self.button = QPushButton("Test Button")
                self.button.setObjectName("test_button")
                self.button.setShortcut(QKeySequence("Ctrl+T"))
                
                # Track button clicks
                self.click_count = 0
                self.button.clicked.connect(lambda: setattr(self, 'click_count', self.click_count + 1))
                layout.addWidget(self.button)
                
                # Set tab order explicitly
                self.setTabOrder(self.input1, self.input2)
                self.setTabOrder(self.input2, self.button)
        
        dialog = TestKeyboardDialog()
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        
        # Test initial focus
        assert dialog.input1.hasFocus() or dialog.input2.hasFocus() or dialog.button.hasFocus(), "Some widget should have focus"
        
        # Test Tab navigation
        qtbot.keyClick(dialog, Qt.Key.Key_Tab)
        qtbot.wait(50)
        
        # Test keyboard shortcut
        initial_clicks = dialog.click_count
        qtbot.keySequence(dialog, QKeySequence("Ctrl+T"))
        qtbot.wait(50)
        
        assert dialog.click_count == initial_clicks + 1, "Keyboard shortcut should trigger button click"
        
        # Test text input with focus
        dialog.input1.setFocus()
        qtbot.wait(50)
        assert dialog.input1.hasFocus(), "Input 1 should have focus after setFocus()"
        
        # Clear input and type new text
        dialog.input1.clear()
        qtbot.keyClicks(dialog.input1, "New text via keyboard")
        qtbot.wait(50)
        
        assert dialog.input1.text() == "New text via keyboard", "Input should contain typed text"
        
        # Test focus changes with mouse clicks
        qtbot.mouseClick(dialog.input2, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        assert dialog.input2.hasFocus(), "Input 2 should have focus after mouse click"

    @pytest.mark.gui
    def test_modal_dialog_interaction_sequence(self, qtbot):
        """
        Example: Test complex modal dialog interaction sequences.
        
        Demonstrates:
        - Modal dialog handling
        - Signal sequencing
        - State verification across dialog operations
        """
        main_window = MainWindow()
        qtbot.addWidget(main_window)
        main_window.show()
        qtbot.waitForWindowShown(main_window)
        
        # Track dialog interactions
        dialog_interactions = []
        
        # Mock dialog for testing
        class TestModalDialog(QDialog):
            result_ready = Mock()
            
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Modal Test Dialog")
                self.setModal(True)
                self.resize(300, 150)
                
                layout = QVBoxLayout(self)
                
                self.input_field = QLineEdit("Default value")
                layout.addWidget(self.input_field)
                
                button_layout = QHBoxLayout()
                
                self.ok_button = QPushButton("OK")
                self.ok_button.clicked.connect(self.accept)
                button_layout.addWidget(self.ok_button)
                
                self.cancel_button = QPushButton("Cancel")
                self.cancel_button.clicked.connect(self.reject)
                button_layout.addWidget(self.cancel_button)
                
                layout.addLayout(button_layout)
                
                # Track interactions
                self.ok_button.clicked.connect(lambda: dialog_interactions.append("ok_clicked"))
                self.cancel_button.clicked.connect(lambda: dialog_interactions.append("cancel_clicked"))
                self.accepted.connect(lambda: dialog_interactions.append("dialog_accepted"))
                self.rejected.connect(lambda: dialog_interactions.append("dialog_rejected"))
        
        # Test 1: Dialog acceptance workflow
        dialog1 = TestModalDialog(main_window)
        qtbot.addWidget(dialog1)
        
        # Show dialog and modify input
        dialog1.show()
        qtbot.waitForWindowShown(dialog1)
        
        # Modify input field
        dialog1.input_field.clear()
        qtbot.keyClicks(dialog1.input_field, "Modified text")
        qtbot.wait(50)
        
        # Click OK button
        qtbot.mouseClick(dialog1.ok_button, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        # Verify dialog was accepted
        assert dialog1.result() == QDialog.DialogCode.Accepted, "Dialog should be accepted"
        assert "ok_clicked" in dialog_interactions, "OK button should be clicked"
        assert "dialog_accepted" in dialog_interactions, "Dialog accepted signal should be emitted"
        assert dialog1.input_field.text() == "Modified text", "Input field should contain modified text"
        
        # Test 2: Dialog rejection workflow
        dialog_interactions.clear()
        dialog2 = TestModalDialog(main_window)
        qtbot.addWidget(dialog2)
        
        dialog2.show()
        qtbot.waitForWindowShown(dialog2)
        
        # Test Escape key cancellation
        qtbot.keyClick(dialog2, Qt.Key.Key_Escape)
        qtbot.wait(50)
        
        assert dialog2.result() == QDialog.DialogCode.Rejected, "Dialog should be rejected via Escape"
        assert "dialog_rejected" in dialog_interactions, "Dialog rejected signal should be emitted"
        
        # Test 3: Cancel button workflow
        dialog_interactions.clear()
        dialog3 = TestModalDialog(main_window)
        qtbot.addWidget(dialog3)
        
        dialog3.show()
        qtbot.waitForWindowShown(dialog3)
        
        qtbot.mouseClick(dialog3.cancel_button, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        assert dialog3.result() == QDialog.DialogCode.Rejected, "Dialog should be rejected via Cancel button"
        assert "cancel_clicked" in dialog_interactions, "Cancel button should be clicked"
        assert "dialog_rejected" in dialog_interactions, "Dialog rejected signal should be emitted"

    @pytest.mark.gui
    def test_signal_timing_and_sequencing(self, qtbot):
        """
        Example: Test signal timing and sequencing with qtbot.
        
        Demonstrates:
        - QSignalSpy for timing analysis
        - waitSignal for async operations
        - Signal sequence verification
        """
        # Create widget with timed signals
        class TestTimedWidget(QWidget):
            immediate_signal = Mock()
            delayed_signal = Mock()
            sequence_signal = Mock()
            
            def __init__(self):
                super().__init__()
                self.resize(200, 100)
                
                layout = QVBoxLayout(self)
                
                self.trigger_button = QPushButton("Trigger Signals")
                self.trigger_button.clicked.connect(self.trigger_signal_sequence)
                layout.addWidget(self.trigger_button)
                
                self.signal_log = []
            
            def trigger_signal_sequence(self):
                """Trigger a sequence of signals with different timing"""
                self.signal_log.append("sequence_started")
                
                # Immediate signal
                self.immediate_signal.emit("immediate")
                self.signal_log.append("immediate_emitted")
                
                # Delayed signal (simulated with QTimer)
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, lambda: self._emit_delayed())
                
                # Sequence completion signal
                QTimer.singleShot(200, lambda: self._emit_sequence_complete())
            
            def _emit_delayed(self):
                self.delayed_signal.emit("delayed")
                self.signal_log.append("delayed_emitted")
            
            def _emit_sequence_complete(self):
                self.sequence_signal.emit("complete")
                self.signal_log.append("sequence_complete")
        
        widget = TestTimedWidget()
        qtbot.addWidget(widget)
        widget.show()
        qtbot.waitForWindowShown(widget)
        
        # Set up signal spies
        immediate_spy = QSignalSpy(widget.immediate_signal)
        delayed_spy = QSignalSpy(widget.delayed_signal) 
        sequence_spy = QSignalSpy(widget.sequence_signal)
        
        # Record start time
        start_time = time.time()
        
        # Trigger the signal sequence
        qtbot.mouseClick(widget.trigger_button, Qt.MouseButton.LeftButton)
        
        # Wait for immediate signal (should be very fast)
        with qtbot.waitSignal(widget.immediate_signal, timeout=1000) as blocker:
            pass
        
        immediate_time = time.time() - start_time
        assert immediate_time < 0.1, f"Immediate signal should be fast (was {immediate_time:.3f}s)"
        assert len(immediate_spy) == 1, "Immediate signal should be emitted once"
        assert immediate_spy[0][0] == "immediate", "Immediate signal should contain correct data"
        
        # Wait for delayed signal
        with qtbot.waitSignal(widget.delayed_signal, timeout=2000) as blocker:
            pass
        
        delayed_time = time.time() - start_time
        assert 0.1 <= delayed_time < 0.5, f"Delayed signal should take ~100ms (was {delayed_time:.3f}s)"
        assert len(delayed_spy) == 1, "Delayed signal should be emitted once"
        
        # Wait for sequence completion
        with qtbot.waitSignal(widget.sequence_signal, timeout=3000) as blocker:
            pass
        
        total_time = time.time() - start_time
        assert 0.2 <= total_time < 1.0, f"Total sequence should take ~200ms (was {total_time:.3f}s)"
        assert len(sequence_spy) == 1, "Sequence signal should be emitted once"
        
        # Verify signal sequence order
        expected_log = [
            "sequence_started",
            "immediate_emitted", 
            "delayed_emitted",
            "sequence_complete"
        ]
        assert widget.signal_log == expected_log, f"Signal sequence should be correct: {widget.signal_log}"

    @pytest.mark.gui
    def test_multi_widget_coordination(self, qtbot):
        """
        Example: Test coordination between multiple widgets.
        
        Demonstrates:
        - Cross-widget signal connections
        - State synchronization testing
        - Complex interaction patterns
        """
        # Create coordinated widgets
        class CoordinatedWidget(QWidget):
            def __init__(self):
                super().__init__()
                self.resize(400, 300)
                
                layout = QVBoxLayout(self)
                
                # Master slider
                layout.addWidget(QLabel("Master Offset:"))
                self.master_slider = QSlider(Qt.Orientation.Horizontal)
                self.master_slider.setRange(0, 1000000)
                self.master_slider.setValue(500000)
                layout.addWidget(self.master_slider)
                
                # Slave input (should sync with master)
                layout.addWidget(QLabel("Slave Input:"))
                self.slave_input = QLineEdit("500000")
                layout.addWidget(self.slave_input)
                
                # Status label
                self.status_label = QLabel("Status: Initialized")
                layout.addWidget(self.status_label)
                
                # Sync button
                self.sync_button = QPushButton("Force Sync")
                layout.addWidget(self.sync_button)
                
                # Set up coordination
                self._setup_coordination()
                
                # Track sync events
                self.sync_events = []
            
            def _setup_coordination(self):
                """Set up widget coordination"""
                # Master slider controls slave input
                self.master_slider.valueChanged.connect(self._on_master_changed)
                
                # Slave input can update master (with validation)
                self.slave_input.textChanged.connect(self._on_slave_changed)
                
                # Force sync button
                self.sync_button.clicked.connect(self._force_sync)
            
            def _on_master_changed(self, value):
                """Master slider changed - update slave"""
                self.slave_input.setText(str(value))
                self.status_label.setText(f"Status: Master → Slave ({value})")
                self.sync_events.append(f"master_to_slave_{value}")
            
            def _on_slave_changed(self, text):
                """Slave input changed - try to update master"""
                try:
                    value = int(text)
                    if 0 <= value <= 1000000:
                        # Temporarily disconnect to avoid recursion
                        self.master_slider.valueChanged.disconnect()
                        self.master_slider.setValue(value)
                        self.master_slider.valueChanged.connect(self._on_master_changed)
                        
                        self.status_label.setText(f"Status: Slave → Master ({value})")
                        self.sync_events.append(f"slave_to_master_{value}")
                    else:
                        self.status_label.setText("Status: Slave value out of range")
                        self.sync_events.append("slave_out_of_range")
                except ValueError:
                    self.status_label.setText("Status: Slave value invalid")
                    self.sync_events.append("slave_invalid")
            
            def _force_sync(self):
                """Force synchronization from master to slave"""
                master_value = self.master_slider.value()
                self.slave_input.setText(str(master_value))
                self.status_label.setText(f"Status: Force synced ({master_value})")
                self.sync_events.append(f"force_sync_{master_value}")
        
        widget = CoordinatedWidget()
        qtbot.addWidget(widget)
        widget.show()
        qtbot.waitForWindowShown(widget)
        
        # Test 1: Master controls slave
        initial_events = len(widget.sync_events)
        
        new_master_value = 750000
        widget.master_slider.setValue(new_master_value)
        qtbot.wait(50)
        
        assert widget.slave_input.text() == str(new_master_value), "Slave should sync with master"
        assert len(widget.sync_events) > initial_events, "Sync event should be recorded"
        assert f"master_to_slave_{new_master_value}" in widget.sync_events, "Master-to-slave sync should be logged"
        
        # Test 2: Slave controls master (valid input)
        widget.sync_events.clear()
        
        new_slave_value = 250000
        widget.slave_input.clear()
        qtbot.keyClicks(widget.slave_input, str(new_slave_value))
        qtbot.wait(100)  # Allow text processing
        
        assert widget.master_slider.value() == new_slave_value, "Master should sync with valid slave input"
        assert f"slave_to_master_{new_slave_value}" in widget.sync_events, "Slave-to-master sync should be logged"
        
        # Test 3: Invalid slave input
        widget.sync_events.clear()
        
        widget.slave_input.clear()
        qtbot.keyClicks(widget.slave_input, "invalid_text")
        qtbot.wait(50)
        
        assert "slave_invalid" in widget.sync_events, "Invalid slave input should be logged"
        assert "invalid" in widget.status_label.text().lower(), "Status should indicate invalid input"
        
        # Test 4: Force sync button
        widget.sync_events.clear()
        
        # Set master to known value
        known_value = 123456
        widget.master_slider.setValue(known_value)
        qtbot.wait(50)
        
        # Manually mess up slave input
        widget.slave_input.setText("wrong_value")
        
        # Force sync
        qtbot.mouseClick(widget.sync_button, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        assert widget.slave_input.text() == str(known_value), "Force sync should correct slave value"
        assert f"force_sync_{known_value}" in widget.sync_events, "Force sync should be logged"


if __name__ == "__main__":
    # Run examples when executed directly
    pytest.main([__file__, "-v", "--tb=short"])
EOF < /dev/null
