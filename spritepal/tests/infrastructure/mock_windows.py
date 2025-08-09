"""
Mock Window Infrastructure for Testing

This module provides mock implementations of MainWindow and other windows
to prevent heavy component creation during tests.

Following Qt Testing Best Practices:
- Pattern 1: Real components with mocked dependencies
- Lightweight mocks with real Qt signals
- No heavy initialization or resource loading
"""

from typing import Optional
from unittest.mock import Mock

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QMainWindow, QWidget


class MockMainWindow(QMainWindow):
    """
    Mock MainWindow that provides real Qt signals without heavy initialization.
    
    Inherits from QMainWindow for compatibility with qtbot and Qt tests
    while avoiding controller creation, panel loading, and resource initialization.
    """

    # Real Qt signals
    extraction_started = pyqtSignal()
    extraction_completed = pyqtSignal()
    extraction_error = pyqtSignal(str)
    injection_started = pyqtSignal()
    injection_completed = pyqtSignal()
    file_opened = pyqtSignal(str)
    window_closing = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Lazy controller initialization (not created until accessed)
        self._controller = None

        # Mock UI components
        self.extraction_panel = Mock()
        self.extraction_panel.get_extraction_params.return_value = {
            'vram_path': '/test/vram.dmp',
            'cgram_path': '/test/cgram.dmp',
            'oam_path': '/test/oam.dmp'
        }

        self.injection_panel = Mock()
        self.status_bar = Mock()
        self.menu_bar = Mock()

        # Mock managers
        self.extraction_manager = Mock()
        self.injection_manager = Mock()
        self.session_manager = Mock()

        # Mock state
        self.current_file = None
        self.is_modified = False

        # Set window properties
        self.setWindowTitle("MockMainWindow")

    @property
    def controller(self):
        """Lazy controller access - creates controller on first access."""
        if self._controller is None:
            self._controller = Mock()
            self._controller.extract_sprites = Mock()
            self._controller.inject_sprites = Mock()
        return self._controller

    def get_extraction_params(self):
        """Get extraction parameters from UI."""
        return self.extraction_panel.get_extraction_params()

    def show_error(self, message: str):
        """Show error message."""
        self.extraction_error.emit(message)

    def update_status(self, message: str):
        """Update status bar."""
        self.status_bar.showMessage(message)

    def extraction_complete(self, extracted_files):
        """Handle extraction completion."""
        self.extraction_completed.emit()

    def injection_complete(self, success: bool):
        """Handle injection completion."""
        self.injection_completed.emit()

    def closeEvent(self, event):
        """Handle close event."""
        self.window_closing.emit()
        super().closeEvent(event)


class MockWorkerBase(QThread):
    """
    Mock base worker that provides real Qt signals without actual thread execution.
    
    This mock prevents "QThread: Destroyed while thread is still running" errors
    by not actually starting threads but still providing signal behavior.
    """

    # Standard worker signals
    started = pyqtSignal()
    finished = pyqtSignal()
    progress = pyqtSignal(int, str)
    error = pyqtSignal(str, object)
    warning = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.is_cancelled = False
        self.is_paused = False
        self._is_running = False

    def start(self):
        """Mock start that doesn't actually create a thread."""
        self._is_running = True
        self.started.emit()
        # Simulate immediate completion for tests
        self.run()
        self._is_running = False
        self.finished.emit()

    def run(self):
        """Mock run method - override in subclasses."""
        pass

    def quit(self):
        """Mock quit method."""
        self._is_running = False

    def wait(self, msecs: int = -1) -> bool:
        """Mock wait method."""
        return True

    def isRunning(self) -> bool:
        """Check if worker is running."""
        return self._is_running

    def cancel(self):
        """Cancel the worker."""
        self.is_cancelled = True
        self.quit()

    def pause(self):
        """Pause the worker."""
        self.is_paused = True

    def resume(self):
        """Resume the worker."""
        self.is_paused = False


class MockExtractionWorker(MockWorkerBase):
    """Mock extraction worker for testing."""

    extraction_completed = pyqtSignal(dict)

    def __init__(self, params: dict, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.params = params
        self.result = {'sprites': [], 'metadata': {}}

    def run(self):
        """Mock extraction operation."""
        # Emit progress
        self.progress.emit(50, "Extracting sprites...")
        # Emit completion with mock result
        self.extraction_completed.emit(self.result)


class MockInjectionWorker(MockWorkerBase):
    """Mock injection worker for testing."""

    injection_completed = pyqtSignal(bool)

    def __init__(self, params: dict, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.params = params

    def run(self):
        """Mock injection operation."""
        # Emit progress
        self.progress.emit(50, "Injecting sprites...")
        # Emit completion
        self.injection_completed.emit(True)


class MockWorkerManager:
    """
    Mock WorkerManager that tracks workers without actual thread management.
    
    This prevents thread cleanup issues during tests.
    """

    def __init__(self):
        self.workers = []
        self.active_workers = []

    def add_worker(self, worker):
        """Add a worker to track."""
        self.workers.append(worker)
        if hasattr(worker, '_is_running') and worker._is_running:
            self.active_workers.append(worker)

    def remove_worker(self, worker):
        """Remove a worker from tracking."""
        if worker in self.workers:
            self.workers.remove(worker)
        if worker in self.active_workers:
            self.active_workers.remove(worker)

    def cleanup_all(self):
        """Clean up all workers."""
        for worker in self.workers[:]:
            if hasattr(worker, 'cancel'):
                worker.cancel()
            if hasattr(worker, 'wait'):
                worker.wait(100)
        self.workers.clear()
        self.active_workers.clear()

    @classmethod
    def cleanup_all_workers(cls):
        """Class method for global cleanup."""
        pass  # Mock implementation


def create_mock_main_window() -> MockMainWindow:
    """
    Factory function to create a properly configured MockMainWindow.
    
    Returns:
        MockMainWindow instance ready for testing
    """
    window = MockMainWindow()

    # Set up any additional mocking needed
    window.extraction_manager = Mock()
    window.extraction_manager.extract_sprites = Mock(return_value={'sprites': []})

    window.injection_manager = Mock()
    window.injection_manager.inject_sprites = Mock(return_value=True)

    return window


def patch_main_window_creation(monkeypatch):
    """
    Patch MainWindow creation to use MockMainWindow.
    
    Args:
        monkeypatch: pytest monkeypatch fixture
    """
    monkeypatch.setattr('ui.main_window.MainWindow', MockMainWindow)

    # Also patch any direct imports
    import sys
    if 'ui.main_window' in sys.modules:
        sys.modules['ui.main_window'].MainWindow = MockMainWindow
