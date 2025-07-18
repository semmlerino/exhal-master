"""
Safe Qt configuration for pytest that prevents crashes in headless environments.
Provides comprehensive Qt mocking and safe fixtures for pixel editor tests.
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


def setup_qt_mocks():
    """Set up Qt mocks early in the test process"""
    # Don't mock if we're not in headless mode
    if not IS_HEADLESS:
        return
        
    # Set Qt to use offscreen platform
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_LOGGING_RULES"] = "*.debug=false"
    
    # The main issue is likely the QTimer in controller initialization
    # Let's patch it after import but before test runs
    print("Setting up Qt for headless testing with offscreen platform")


def pytest_configure(config):
    """Configure pytest with custom markers and early Qt mocking"""
    config.addinivalue_line(
        "markers", "gui: mark test as requiring GUI (skip in headless)"
    )
    config.addinivalue_line(
        "markers", "mock_gui: mark test as GUI test that uses mocks"
    )
    
    # Early Qt mocking for headless environments
    if IS_HEADLESS:
        setup_qt_mocks()


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
    
    # Import and patch specific Qt components that cause issues
    try:
        from PyQt6.QtCore import QTimer, QObject, pyqtSignal
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QPixmap, QImage
        
        # Patch QTimer to not actually start timers
        original_start = QTimer.start
        def mock_start(self, *args, **kwargs):
            # Don't actually start the timer in headless mode
            pass
        QTimer.start = mock_start
        
        # Patch QApplication.processEvents to prevent hanging
        if hasattr(QApplication, 'processEvents'):
            QApplication.processEvents = Mock()
            
        print("Applied Qt patches for headless testing")
            
    except ImportError:
        print("Qt not available, skipping patches")
    
    yield


@pytest.fixture
def qt_safe_app(qapp):
    """Provide a QApplication that's safe for headless environments"""
    if IS_HEADLESS:
        # Return a mock if we're headless
        mock_app = Mock()
        mock_app.processEvents = Mock()
        mock_app.quit = Mock()
        mock_app.instance = Mock(return_value=mock_app)
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
        mock_qtbot.mouseClick = Mock()
        mock_qtbot.keyClick = Mock()
        return mock_qtbot
    return qtbot


@pytest.fixture
def mock_controller():
    """Mock pixel editor controller for testing without Qt"""
    controller = Mock()
    
    # Mock basic properties
    controller.image_model = Mock()
    controller.palette_model = Mock()
    controller.project_model = Mock()
    controller.tool_manager = Mock()
    controller.file_manager = Mock()
    controller.palette_manager = Mock()
    controller.undo_manager = Mock()
    
    # Mock signals
    for signal_name in [
        "imageChanged",
        "paletteChanged", 
        "titleChanged",
        "statusMessage",
        "error",
        "toolChanged"
    ]:
        signal = Mock()
        signal.emit = Mock()
        signal.connect = Mock()
        setattr(controller, signal_name, signal)
    
    # Mock methods
    controller.set_tool = Mock()
    controller.get_current_tool_name = Mock(return_value="pencil")
    controller.load_image = Mock()
    controller.save_image = Mock()
    controller.undo = Mock()
    controller.redo = Mock()
    
    return controller