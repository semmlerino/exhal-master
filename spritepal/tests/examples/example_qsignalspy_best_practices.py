"""
Example demonstrating QSignalSpy best practices.

This file shows the correct way to use QSignalSpy with test doubles
and how to avoid common pitfalls.
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QDialog, QWidget

# ============================================================================
# CORRECT: Real QObject Test Doubles
# ============================================================================

class TestDialog(QDialog):
    """
    CORRECT: Test double that inherits from QDialog.

    Even though it has 'test' or 'mock' in the name, it's a real QDialog
    with real Qt signals that work with QSignalSpy.
    """

    value_changed = Signal(int)
    text_changed = Signal(str)
    accepted = Signal()  # Override parent's signal

    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0

    def set_value(self, value: int):
        self.value = value
        self.value_changed.emit(value)

class TestWorker(QObject):
    """
    CORRECT: Worker test double with real signals.

    Inherits from QObject and can be moved to a thread safely.
    """

    started = Signal()
    progress = Signal(int, str)
    finished = Signal()
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self.is_running = False

    def start(self):
        self.is_running = True
        self.started.emit()

    def stop(self):
        self.is_running = False
        self.finished.emit()

# ============================================================================
# Test Examples
# ============================================================================

class TestQSignalSpyBestPractices:
    """Examples of correct QSignalSpy usage."""

    def test_dialog_signals_with_spy(self, qtbot):
        """CORRECT: Using QSignalSpy with real QDialog subclass."""
        dialog = TestDialog()
        qtbot.addWidget(dialog)

        # Create signal spy for real signal
        value_spy = QSignalSpy(dialog.value_changed)
        text_spy = QSignalSpy(dialog.text_changed)

        # Trigger signals
        dialog.set_value(42)
        dialog.text_changed.emit("Hello")

        # Verify emissions
        assert value_spy.count() == 1
        assert value_spy.at(0) == [42]
        assert text_spy.count() == 1
        assert text_spy.at(0) == ["Hello"]

    def test_worker_with_thread(self, qtbot):
        """CORRECT: Testing worker in thread with QSignalSpy."""
        worker = TestWorker()
        thread = QThread()

        # Move worker to thread
        worker.moveToThread(thread)

        # Create spies before starting thread
        started_spy = QSignalSpy(worker.started)
        finished_spy = QSignalSpy(worker.finished)

        # Connect and start
        thread.started.connect(worker.start)
        thread.start()

        # Wait for signal with timeout
        assert qtbot.waitSignal(worker.started, timeout=1000)
        assert started_spy.count() == 1

        # Stop worker
        worker.stop()
        assert qtbot.waitSignal(worker.finished, timeout=1000)
        assert finished_spy.count() == 1

        # Cleanup
        thread.quit()
        thread.wait()

    def test_async_signal_wait(self, qtbot):
        """CORRECT: Using qtbot.waitSignal for async operations."""
        dialog = TestDialog()
        qtbot.addWidget(dialog)

        # Use waitSignal instead of QSignalSpy for async waiting
        with qtbot.waitSignal(dialog.value_changed, timeout=1000) as blocker:
            # This will emit the signal asynchronously
            QTimer.singleShot(100, lambda: dialog.set_value(100))

        # Access the signal arguments
        assert blocker.args == [100]

    def test_multiple_signals_monitoring(self, qtbot):
        """CORRECT: Monitor multiple signals with QSignalSpy."""
        worker = TestWorker()

        # Create multiple spies
        spies = {
            'started': QSignalSpy(worker.started),
            'progress': QSignalSpy(worker.progress),
            'finished': QSignalSpy(worker.finished),
            'error': QSignalSpy(worker.error)
        }

        # Simulate workflow
        worker.start()
        worker.progress.emit(50, "Half way")
        worker.progress.emit(100, "Complete")
        worker.stop()

        # Verify all signals
        assert spies['started'].count() == 1
        assert spies['progress'].count() == 2
        assert spies['progress'].at(0) == [50, "Half way"]
        assert spies['progress'].at(1) == [100, "Complete"]
        assert spies['finished'].count() == 1
        assert spies['error'].count() == 0

# ============================================================================
# INCORRECT: Examples to Avoid (Commented Out)
# ============================================================================

"""
# NEVER DO THIS - QSignalSpy with unittest.mock.Mock

def test_incorrect_mock_usage():
    # WRONG: Mock objects don't have real Qt signals
    mock_dialog = Mock()
    mock_dialog.signal = Mock()  # Not a real Signal

    # This would crash or not work properly:
    # spy = QSignalSpy(mock_dialog.signal)  # DON'T DO THIS!

    # Instead, create a real QObject test double as shown above

# NEVER DO THIS - Mixing Mock with Qt signals

def test_incorrect_mixed_usage():
    # WRONG: Mixing Mock with real signals
    mock = Mock(spec=QDialog)
    mock.accepted = Signal()  # Doesn't work properly

    # This won't work correctly:
    # spy = QSignalSpy(mock.accepted)  # DON'T DO THIS!

# NEVER DO THIS - Wrong inheritance

class BadTestDouble:
    # WRONG: Not inheriting from QObject
    signal = Signal()  # Won't work without QObject parent

    def __init__(self):
        # Can't use Qt signals without QObject
        pass
"""

# ============================================================================
# Helper Functions
# ============================================================================

def create_test_widget_with_signals() -> QWidget:
    """
    Factory function to create test widgets with signals.

    Returns a real QWidget with real signals for testing.
    """
    class TestWidget(QWidget):
        clicked = Signal()
        value_changed = Signal(int)

        def __init__(self):
            super().__init__()

    return TestWidget()

# ============================================================================
# Documentation
# ============================================================================

"""
Key Takeaways:

1. ALWAYS use real QObject subclasses for test doubles that need signals
2. NEVER use unittest.mock.Mock for Qt signal testing
3. Use QSignalSpy for counting and inspecting signal emissions
4. Use qtbot.waitSignal() for async signal waiting
5. Add widgets to qtbot with addWidget() for proper cleanup
6. Move workers to threads with moveToThread(), not by subclassing QThread
7. Create signal spies before triggering the signals
8. Clean up threads properly with quit() and wait()

Common Patterns:

- Test doubles: Create QObject subclasses with real Signal() instances
- Async testing: Use qtbot.waitSignal() with timeout
- Multiple signals: Create dictionary of QSignalSpy objects
- Thread testing: moveToThread() pattern with proper cleanup
- Signal arguments: Access with spy.at(index) or blocker.args

Anti-Patterns to Avoid:

- Mock() objects with QSignalSpy
- Fake signal attributes on non-QObject classes
- Missing super().__init__() in QObject subclasses
- Not cleaning up threads and widgets
- Using DirectConnection across threads unsafely
"""

if __name__ == '__main__':
    # This file is meant to be run with pytest
    pytest.main([__file__, '-v'])
