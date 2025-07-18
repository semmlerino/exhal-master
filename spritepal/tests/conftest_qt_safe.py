"""
Safe Qt configuration for pytest that prevents crashes in headless environments.
This can be used as a drop-in replacement for conftest.py when GUI tests fail.
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Detect if we're in a problematic headless environment
IS_HEADLESS = (
    not os.environ.get("DISPLAY")
    or os.environ.get("QT_QPA_PLATFORM") == "offscreen"
    or os.environ.get("CI")
    or (sys.platform == "linux" and "microsoft" in os.uname().release.lower())
)


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "gui: mark test as requiring GUI (skip in headless)"
    )
    config.addinivalue_line(
        "markers", "mock_gui: mark test as GUI test that uses mocks"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on environment"""
    if IS_HEADLESS:
        skip_gui = pytest.mark.skip(reason="GUI tests skipped in headless environment")
        for item in items:
            if "gui" in item.keywords and "mock_gui" not in item.keywords:
                item.add_marker(skip_gui)


@pytest.fixture(scope="session", autouse=True)
def mock_qt_in_headless():
    """Automatically mock Qt in headless environments to prevent crashes"""
    if not IS_HEADLESS:
        yield
        return

    # Create comprehensive Qt mocks
    mock_modules = {
        "PyQt6": Mock(),
        "PyQt6.QtCore": Mock(),
        "PyQt6.QtGui": Mock(),
        "PyQt6.QtWidgets": Mock(),
        "PyQt6.QtTest": Mock(),
    }

    # Mock common Qt classes
    mock_qobject = Mock()
    mock_qthread = Mock()
    mock_qapplication = Mock()
    mock_qwidget = Mock()
    mock_signal = Mock(return_value=Mock())

    # Configure the mocks
    mock_modules["PyQt6.QtCore"].QObject = mock_qobject
    mock_modules["PyQt6.QtCore"].QThread = mock_qthread
    mock_modules["PyQt6.QtCore"].pyqtSignal = mock_signal
    mock_modules["PyQt6.QtWidgets"].QApplication = mock_qapplication
    mock_modules["PyQt6.QtWidgets"].QWidget = mock_qwidget

    with patch.dict("sys.modules", mock_modules):
        yield


@pytest.fixture
def qt_safe_app(qapp):
    """Provide a QApplication that's safe for headless environments"""
    if IS_HEADLESS:
        # Return a mock if we're headless
        mock_app = Mock()
        mock_app.processEvents = Mock()
        mock_app.quit = Mock()
        return mock_app
    return qapp


@pytest.fixture
def safe_qtbot(qtbot):
    """Provide a qtbot that's safe for headless environments"""
    if IS_HEADLESS:
        # Create a mock qtbot
        mock_qtbot = Mock()
        mock_qtbot.wait = Mock()
        mock_qtbot.waitSignal = Mock(return_value=Mock())
        mock_qtbot.waitUntil = Mock()
        mock_qtbot.addWidget = Mock()
        return mock_qtbot
    return qtbot


# Alternative fixtures for truly headless-safe testing
@pytest.fixture
def mock_main_window():
    """Mock main window for testing without Qt"""
    window = Mock()
    window.extract_requested = Mock()
    window.open_in_editor_requested = Mock()
    window.get_extraction_params = Mock(
        return_value={
            "vram_path": "/test/vram.dmp",
            "cgram_path": "/test/cgram.dmp",
            "output_base": "/test/output",
            "create_grayscale": True,
            "create_metadata": True,
            "oam_path": None,
        }
    )
    window.extraction_complete = Mock()
    window.extraction_failed = Mock()
    window.status_bar = Mock()
    window.status_bar.showMessage = Mock()
    window.sprite_preview = Mock()
    window.palette_preview = Mock()
    window.preview_info = Mock()
    return window


@pytest.fixture
def mock_worker():
    """Mock extraction worker for testing without Qt"""
    worker = Mock()

    # Create mock signals
    for signal_name in [
        "progress",
        "preview_ready",
        "palettes_ready",
        "active_palettes_ready",
        "finished",
        "error",
    ]:
        signal = Mock()
        signal.emit = Mock()
        signal.connect = Mock()
        setattr(worker, signal_name, signal)

    worker.start = Mock()
    worker.run = Mock()
    return worker
