"""
Modernized Qt mock components for SpritePal tests.

This module provides realistic Qt mock implementations that behave consistently
across all test environments, including headless setups.
"""

from typing import Any, Callable, Optional
from unittest.mock import Mock


class MockSignal:
    """
    Realistic mock implementation of PyQt6 signals.

    This implementation maintains callback lists and properly executes connected
    functions when emit() is called, providing realistic signal behavior for tests.
    """

    def __init__(self):
        self._callbacks: list[Callable] = []
        self.emit = Mock(side_effect=self._emit)
        self.connect = Mock(side_effect=self._connect)
        self.disconnect = Mock(side_effect=self._disconnect)

    def _connect(self, callback: Callable) -> None:
        """Internal connect implementation that maintains callback list."""
        self._callbacks.append(callback)

    def _disconnect(self, callback: Optional[Callable] = None) -> None:
        """Internal disconnect implementation."""
        if callback is None:
            self._callbacks.clear()
        elif callback in self._callbacks:
            self._callbacks.remove(callback)

    def _emit(self, *args: Any) -> None:
        """Internal emit implementation that calls all connected callbacks."""
        for callback in self._callbacks:
            try:
                callback(*args)
            except Exception:
                # In real Qt, signal emission doesn't crash on callback errors
                pass


class MockQWidget:
    """Comprehensive mock implementation of QWidget."""

    def __init__(self, parent=None):
        self.parent = Mock(return_value=parent)
        self.show = Mock()
        self.hide = Mock()
        self.close = Mock()
        self.setVisible = Mock()
        self.isVisible = Mock(return_value=False)
        self.update = Mock()
        self.repaint = Mock()
        self.setMinimumSize = Mock()
        self.setMaximumSize = Mock()
        self.resize = Mock()
        self.setWindowTitle = Mock()
        self.setWindowFlags = Mock()
        self.windowFlags = Mock(return_value=Mock())
        self.isModal = Mock(return_value=False)
        self.setModal = Mock()
        self.deleteLater = Mock()

        # Layout support
        self.setLayout = Mock()
        self.layout = Mock(return_value=None)


class MockQDialog(MockQWidget):
    """Mock implementation of QDialog extending QWidget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.accept = Mock()
        self.reject = Mock()
        self.exec = Mock(return_value=0)
        self.result = Mock(return_value=0)


class MockQPixmap:
    """Mock implementation of QPixmap for image handling tests."""

    def __init__(self, width: int = 100, height: int = 100):
        self._width = width
        self._height = height
        self.width = Mock(return_value=width)
        self.height = Mock(return_value=height)
        self.loadFromData = Mock(return_value=True)
        self.save = Mock(return_value=True)
        self.isNull = Mock(return_value=False)
        self.scaled = Mock(return_value=self)


class MockQLabel(MockQWidget):
    """Mock implementation of QLabel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self.setText = Mock(side_effect=self._set_text)
        self.text = Mock(side_effect=self._get_text)
        self.setPixmap = Mock()
        self.setAlignment = Mock()
        self.setStyleSheet = Mock()

    def _set_text(self, text: str) -> None:
        self._text = text

    def _get_text(self) -> str:
        return self._text


class MockQThread:
    """Mock implementation of QThread for worker thread tests."""

    def __init__(self):
        self.start = Mock()
        self.quit = Mock()
        self.wait = Mock(return_value=True)
        self.isRunning = Mock(return_value=False)
        self.terminate = Mock()
        self.finished = MockSignal()
        self.started = MockSignal()


class MockQApplication:
    """Mock implementation of QApplication."""

    def __init__(self):
        self.processEvents = Mock()
        self.quit = Mock()
        self.exit = Mock()

    @classmethod
    def instance(cls):
        """Mock class method that returns a mock app instance."""
        return cls()


def create_mock_signals() -> dict[str, MockSignal]:
    """
    Create a standard set of mock signals commonly used in extraction workflows.

    Returns:
        Dictionary containing mock signals for common extraction events
    """
    return {
        "progress": MockSignal(),
        "preview_ready": MockSignal(),
        "preview_image_ready": MockSignal(),
        "palettes_ready": MockSignal(),
        "active_palettes_ready": MockSignal(),
        "extraction_complete": MockSignal(),
        "extraction_failed": MockSignal(),
        "extraction_finished": MockSignal(),
        "error": MockSignal(),
        "injection_started": MockSignal(),
        "injection_progress": MockSignal(),
        "injection_complete": MockSignal(),
        "injection_failed": MockSignal(),
    }


def create_qt_mock_context():
    """
    Create a complete Qt mock context for headless testing.

    Returns:
        Dictionary of Qt module mocks for patching sys.modules
    """
    mock_modules = {
        "PyQt6": Mock(),
        "PyQt6.QtCore": Mock(),
        "PyQt6.QtGui": Mock(),
        "PyQt6.QtWidgets": Mock(),
        "PyQt6.QtTest": Mock(),
    }

    # Configure QtCore
    mock_modules["PyQt6.QtCore"].QObject = Mock
    mock_modules["PyQt6.QtCore"].QThread = MockQThread
    mock_modules["PyQt6.QtCore"].pyqtSignal = MockSignal
    mock_modules["PyQt6.QtCore"].Qt = Mock()

    # Configure QtWidgets
    mock_modules["PyQt6.QtWidgets"].QApplication = MockQApplication
    mock_modules["PyQt6.QtWidgets"].QWidget = MockQWidget
    mock_modules["PyQt6.QtWidgets"].QDialog = MockQDialog
    mock_modules["PyQt6.QtWidgets"].QLabel = MockQLabel

    # Configure QtGui
    mock_modules["PyQt6.QtGui"].QPixmap = MockQPixmap

    return mock_modules
