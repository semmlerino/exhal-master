"""
Modernized Qt mock components for SpritePal tests.

This module provides realistic Qt mock implementations that behave consistently
across all test environments, including headless setups.
"""

from typing import Any, Callable
from unittest.mock import Mock

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    from PyQt6.QtWidgets import QApplication
    QT_AVAILABLE = True
except ImportError:
    # Fallback for environments where Qt is not available
    QT_AVAILABLE = False
    QObject = object
    pyqtSignal = Mock


# For backward compatibility, MockSignal is now an alias to pyqtSignal
if QT_AVAILABLE:
    MockSignal = pyqtSignal
else:
    # Minimal fallback implementation for non-Qt environments
    class MockSignal:
        """Fallback signal implementation when Qt is not available."""

        def __init__(self, *args):
            """Initialize MockSignal, accepting any type arguments like real pyqtSignal."""
            self._callbacks: list[Callable] = []
            self.emit = Mock(side_effect=self._emit)
            self.connect = Mock(side_effect=self._connect)
            self.disconnect = Mock(side_effect=self._disconnect)

        def _connect(self, callback: Callable) -> None:
            """Internal connect implementation that maintains callback list."""
            self._callbacks.append(callback)

        def _disconnect(self, callback: Callable | None = None) -> None:
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


class SignalHolder(QObject):
    """
    Helper class to hold Qt signals for mock objects.

    Since Qt signals must be class attributes on QObject subclasses,
    this class provides a way to attach real signals to mock objects.
    """

    # Common signals used across tests - defined at class level
    # These will be overridden with specific signal types as needed
    pass


def create_signal_holder(**signals):
    """
    Create a SignalHolder with dynamic signals.

    Args:
        **signals: Keyword arguments where key is signal name and value is signal type
                   e.g., extract_requested=pyqtSignal(), progress=pyqtSignal(int)

    Returns:
        SignalHolder instance with the specified signals
    """
    if not QT_AVAILABLE:
        # Fallback for non-Qt environments
        holder = Mock()
        for name, _signal_type in signals.items():
            setattr(holder, name, MockSignal())
        return holder

    # For Qt environments, ensure QApplication exists before creating signal holder
    from PyQt6.QtCore import QCoreApplication
    if QCoreApplication.instance() is None:
        # Create QApplication if not exists
        import os
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PyQt6.QtWidgets import QApplication
        QApplication([])

    # Now create the pre-defined signal holder
    holder = CommonSignalHolder()

    # Return the holder - it has all common signals pre-defined
    return holder


class CommonSignalHolder(QObject):
    """
    Pre-defined signal holder with all common signals used in tests.

    This avoids runtime signal creation issues by defining all signals
    at class definition time.
    """
    # Main window signals
    extract_requested = pyqtSignal()
    open_in_editor_requested = pyqtSignal(str)
    arrange_rows_requested = pyqtSignal(str)
    arrange_grid_requested = pyqtSignal(str)
    inject_requested = pyqtSignal()

    # Worker/manager signals
    progress = pyqtSignal(int)
    preview_ready = pyqtSignal(bytes, int, int, str)
    preview_image_ready = pyqtSignal(object)
    preview_error = pyqtSignal(str)
    palettes_ready = pyqtSignal(list)
    active_palettes_ready = pyqtSignal(list)
    extraction_complete = pyqtSignal(object)
    extraction_failed = pyqtSignal(str)
    extraction_finished = pyqtSignal(list)
    error = pyqtSignal(str, object)

    # Injection signals
    injection_started = pyqtSignal()
    injection_progress = pyqtSignal(int)
    injection_complete = pyqtSignal(object)
    injection_failed = pyqtSignal(str)

    # Navigation signals
    offset_changed = pyqtSignal(int)
    navigation_bounds_changed = pyqtSignal(int, int)
    step_size_changed = pyqtSignal(int)

    # Coordinator signals
    preview_requested = pyqtSignal(int)
    preview_cleared = pyqtSignal()
    sprite_found = pyqtSignal(int, object)
    search_started = pyqtSignal()
    search_completed = pyqtSignal(int)

    # Tab signals
    tab_switch_requested = pyqtSignal(int)
    update_title_requested = pyqtSignal(str)
    status_message = pyqtSignal(str)
    navigation_enabled = pyqtSignal(bool)
    step_size_synchronized = pyqtSignal(int)
    preview_update_queued = pyqtSignal(int)
    preview_generation_started = pyqtSignal()
    preview_generation_completed = pyqtSignal()

    # Registry signals
    sprite_added = pyqtSignal(int, object)
    sprite_removed = pyqtSignal(int)
    sprites_cleared = pyqtSignal()
    sprites_imported = pyqtSignal(int)

    # Worker manager signals
    worker_started = pyqtSignal(str)
    worker_finished = pyqtSignal(str)
    worker_error = pyqtSignal(str, object)

    # Dialog tab signals
    find_next_clicked = pyqtSignal()
    find_prev_clicked = pyqtSignal()
    smart_mode_changed = pyqtSignal(bool)
    offset_requested = pyqtSignal(int)
    sprite_selected = pyqtSignal(int)
    clear_requested = pyqtSignal()

    # Thread signals
    started = pyqtSignal()
    finished = pyqtSignal()


class TestMainWindow(QObject):
    """
    QObject-based test double for MainWindow.

    This provides real Qt signals while mocking other functionality,
    avoiding segfaults from attaching signals to Mock objects.
    """

    # Define signals as class attributes (required by Qt)
    extract_requested = pyqtSignal()
    open_in_editor_requested = pyqtSignal(str)
    arrange_rows_requested = pyqtSignal(str)
    arrange_grid_requested = pyqtSignal(str)
    inject_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Mock methods
        self.show = Mock()
        self.close = Mock()
        self.extraction_complete = Mock()
        self.extraction_failed = Mock()
        self.get_extraction_params = Mock(return_value={
            "vram_path": "/test/vram.dmp",
            "cgram_path": "/test/cgram.dmp",
            "output_base": "/test/output",
            "create_grayscale": True,
            "create_metadata": True,
            "oam_path": None,
        })

        # Mock UI components
        self.status_bar = Mock()
        self.status_bar.showMessage = Mock()
        self.sprite_preview = Mock()
        self.palette_preview = Mock()
        self.preview_info = Mock()
        self.output_name_edit = Mock()
        self.output_name_edit.text = Mock(return_value="test_output")

        # Create TestExtractionPanel with real signals
        self.extraction_panel = TestExtractionPanel()

        # Add preview_coordinator mock (needed by controller tests)
        self.preview_coordinator = Mock()
        self.preview_coordinator.update_preview_info = Mock()

        # Add get_output_path method (needed by injection tests)
        self.get_output_path = Mock(return_value="/test/output")


class TestExtractionPanel(QObject):
    """
    QObject-based test double for ExtractionPanel.

    Provides real Qt signals for extraction panel functionality.
    """

    # Define signals as class attributes
    file_dropped = pyqtSignal(str)
    files_changed = pyqtSignal()
    extraction_ready = pyqtSignal(bool)
    offset_changed = pyqtSignal(int)
    mode_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Mock methods and attributes
        self.get_vram_path = Mock(return_value="/test/vram.dmp")
        self.get_cgram_path = Mock(return_value="/test/cgram.dmp")
        self.get_oam_path = Mock(return_value=None)
        self.get_output_base = Mock(return_value="/test/output")
        self.get_vram_offset = Mock(return_value=0xC000)
        self.set_vram_offset = Mock()


class TestROMExtractionPanel(QObject):
    """
    QObject-based test double for ROMExtractionPanel.

    Provides real Qt signals for ROM extraction panel functionality.
    """

    # Define signals as class attributes
    files_changed = pyqtSignal()
    extraction_ready = pyqtSignal(bool)
    rom_extraction_requested = pyqtSignal(dict)
    output_name_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Mock methods and attributes
        self.get_rom_path = Mock(return_value="/test/rom.sfc")
        self.get_sprite_offset = Mock(return_value=0x8000)
        self.get_output_base = Mock(return_value="/test/output")
        self.get_sprite_name = Mock(return_value="TestSprite")


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

        # Create a signal holder for thread signals
        if QT_AVAILABLE:
            signal_holder = create_signal_holder(
                finished=pyqtSignal(),
                started=pyqtSignal()
            )
            self.finished = signal_holder.finished
            self.started = signal_holder.started
        else:
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


def create_mock_signals() -> dict[str, Any]:
    """
    Create a standard set of mock signals commonly used in extraction workflows.

    Returns:
        Dictionary containing mock signals for common extraction events
    """
    if QT_AVAILABLE:
        # Create a signal holder with all the common signals
        signal_holder = create_signal_holder(
            progress=pyqtSignal(int),
            preview_ready=pyqtSignal(bytes, int, int, str),
            preview_image_ready=pyqtSignal(object),
            palettes_ready=pyqtSignal(list),
            active_palettes_ready=pyqtSignal(list),
            extraction_complete=pyqtSignal(object),
            extraction_failed=pyqtSignal(str),
            extraction_finished=pyqtSignal(list),
            error=pyqtSignal(str, object),
            injection_started=pyqtSignal(),
            injection_progress=pyqtSignal(int),
            injection_complete=pyqtSignal(object),
            injection_failed=pyqtSignal(str),
        )

        # Return a dictionary of the signals
        return {
            "progress": signal_holder.progress,
            "preview_ready": signal_holder.preview_ready,
            "preview_image_ready": signal_holder.preview_image_ready,
            "palettes_ready": signal_holder.palettes_ready,
            "active_palettes_ready": signal_holder.active_palettes_ready,
            "extraction_complete": signal_holder.extraction_complete,
            "extraction_failed": signal_holder.extraction_failed,
            "extraction_finished": signal_holder.extraction_finished,
            "error": signal_holder.error,
            "injection_started": signal_holder.injection_started,
            "injection_progress": signal_holder.injection_progress,
            "injection_complete": signal_holder.injection_complete,
            "injection_failed": signal_holder.injection_failed,
        }
    # Fallback for non-Qt environments
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


def create_mock_main_window(**kwargs):
    """
    Create a mock main window for testing.

    This is a compatibility function that delegates to MockFactory.
    """
    from .mock_factory import MockFactory
    return MockFactory.create_main_window(**kwargs)
