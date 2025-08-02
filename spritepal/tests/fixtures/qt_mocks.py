"""
Consolidated Qt mock components for consistent testing across the SpritePal test suite.
This module provides reusable mock implementations that behave like real Qt components.
"""

from unittest.mock import Mock


class MockSignal:
    """
    Mock implementation of PyQt6 signals that actually connects and emits.

    This implementation maintains callback lists and properly executes connected
    functions when emit() is called, providing realistic signal behavior for tests.
    It also provides Mock-compatible connect/disconnect methods for assertion testing.
    """

    def __init__(self):
        self.callbacks = []
        self.emit = Mock(side_effect=self._emit)
        # Make connect and disconnect Mock objects for assertion compatibility
        self.connect = Mock(side_effect=self._connect)
        self.disconnect = Mock(side_effect=self._disconnect)

    def _connect(self, callback):
        """Internal connect implementation that maintains callback list"""
        self.callbacks.append(callback)

    def _disconnect(self, callback=None):
        """Internal disconnect implementation"""
        if callback is None:
            self.callbacks.clear()
        elif callback in self.callbacks:
            self.callbacks.remove(callback)

    def _emit(self, *args):
        """Internal emit implementation that calls all connected callbacks"""
        for callback in self.callbacks:
            callback(*args)


class MockQPixmap:
    """Mock implementation of QPixmap for image handling tests"""

    def __init__(self, width=100, height=100):
        self.width = Mock(return_value=width)
        self.height = Mock(return_value=height)
        self.loadFromData = Mock(return_value=True)
        self.save = Mock(return_value=True)
        self.isNull = Mock(return_value=False)
        self.scaled = Mock(return_value=self)


class MockQLabel:
    """Mock implementation of QLabel for UI tests"""

    def __init__(self):
        self.setText = Mock()
        self.setPixmap = Mock()
        self.text = Mock(return_value="")
        self.setAlignment = Mock()
        self.setStyleSheet = Mock()


class MockQWidget:
    """Mock implementation of QWidget for UI tests"""

    def __init__(self):
        self.show = Mock()
        self.hide = Mock()
        self.setVisible = Mock()
        self.update = Mock()
        self.repaint = Mock()
        self.setMinimumSize = Mock()
        self.setMaximumSize = Mock()
        self.resize = Mock()


class MockQThread:
    """Mock implementation of QThread for worker thread tests"""

    def __init__(self):
        self.start = Mock()
        self.quit = Mock()
        self.wait = Mock(return_value=True)
        self.isRunning = Mock(return_value=False)
        self.terminate = Mock()
        self.finished = MockSignal()


def create_mock_signals():
    """
    Create a standard set of mock signals commonly used in extraction workflows.

    Returns:
        dict: Dictionary containing mock signals for common extraction events
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
    }


def create_mock_main_window():
    """
    Create a comprehensive mock main window with all necessary components.

    Returns:
        Mock: Configured mock main window suitable for controller testing
    """
    window = Mock()

    # Signals
    window.extract_requested = MockSignal()
    window.open_in_editor_requested = MockSignal()
    window.arrange_rows_requested = MockSignal()
    window.arrange_grid_requested = MockSignal()
    window.inject_requested = MockSignal()

    # UI Components
    window.status_bar = Mock()
    window.status_bar.showMessage = Mock()
    window.sprite_preview = Mock()
    window.palette_preview = Mock()
    window.preview_info = Mock()
    window.output_name_edit = Mock()
    window.output_name_edit.text = Mock(return_value="test_output")

    # Methods
    window.get_extraction_params = Mock(return_value={
        "vram_path": "/test/vram.dmp",
        "cgram_path": "/test/cgram.dmp",
        "output_base": "/test/output",
        "create_grayscale": True,
        "create_metadata": True,
        "oam_path": None,
    })
    window.extraction_complete = Mock()
    window.extraction_failed = Mock()
    window.show = Mock()
    window.close = Mock()

    return window


def create_mock_extraction_worker():
    """
    Create a mock extraction worker with proper signal behavior.

    Returns:
        Mock: Configured mock worker with all extraction signals
    """
    worker = Mock()

    # Add all the signals that ExtractionWorker uses
    signals = create_mock_signals()
    for signal_name, signal in signals.items():
        setattr(worker, signal_name, signal)

    # Worker control methods
    worker.start = Mock()
    worker.run = Mock()
    worker.quit = Mock()
    worker.wait = Mock(return_value=True)
    worker.isRunning = Mock(return_value=False)

    return worker


def create_mock_extraction_manager():
    """
    Create a mock extraction manager for testing.

    Returns:
        Mock: Configured mock extraction manager
    """
    manager = Mock()
    manager.extract_sprites = Mock()
    manager.get_rom_extractor = Mock()
    manager.validate_extraction_params = Mock(return_value=True)
    manager.create_worker = Mock()

    # Add signals
    signals = create_mock_signals()
    for signal_name, signal in signals.items():
        setattr(manager, signal_name, signal)

    return manager




def create_mock_file_dialogs():
    """
    Create mock file dialog functions for testing.

    Returns:
        dict: Dictionary of mock file dialog functions
    """
    return {
        "getOpenFileName": Mock(return_value=("test_file.dmp", "Memory dump (*.dmp)")),
        "getSaveFileName": Mock(return_value=("output.png", "PNG files (*.png)")),
        "getExistingDirectory": Mock(return_value="/test/directory"),
    }


def create_mock_qimage():
    """
    Create a mock QImage for image processing tests.

    Returns:
        Mock: Configured mock QImage
    """
    qimage = Mock()
    qimage.width = Mock(return_value=128)
    qimage.height = Mock(return_value=128)
    qimage.format = Mock(return_value=Mock())
    qimage.bits = Mock(return_value=b"\x00" * 1024)
    qimage.save = Mock(return_value=True)
    qimage.load = Mock(return_value=True)
    qimage.isNull = Mock(return_value=False)
    return qimage


def create_mock_drag_drop_event():
    """
    Create a mock drag and drop event for testing.

    Returns:
        Mock: Configured mock drag drop event
    """
    event = Mock()
    event.mimeData = Mock()
    event.mimeData().hasUrls = Mock(return_value=True)
    event.mimeData().urls = Mock(return_value=[
        Mock(toLocalFile=Mock(return_value="/test/file.dmp"))
    ])
    event.accept = Mock()
    event.ignore = Mock()
    return event
