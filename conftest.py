"""
Root conftest.py for all tests in the project.
Configures Qt for headless testing environments.
"""

import os
import sys
from pathlib import Path

import pytest

# Add project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Qt imports - conditional to avoid issues when Qt is not needed
try:
    from PyQt6.QtWidgets import QApplication

    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


def is_headless_environment():
    """Detect if running in a headless environment"""
    # Check for common headless environment indicators
    if os.environ.get("CI"):  # Common CI environment variable
        return True
    if not os.environ.get("DISPLAY"):  # No X11 display
        return True
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":  # Already set
        return True
    # Check if we're in WSL
    if sys.platform == "linux" and "microsoft" in os.uname().release.lower():
        return True
    return False


# Configure Qt for headless testing if needed
if QT_AVAILABLE and is_headless_environment():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ["QT_LOGGING_RULES"] = "*.debug=false"


@pytest.fixture(scope="session", autouse=True)
def qt_headless_config():
    """
    Automatically configure Qt for headless testing.
    This runs before any tests to ensure Qt is properly configured.
    """
    if QT_AVAILABLE and is_headless_environment():
        print("Detected headless environment - using Qt offscreen platform")
        # Ensure the environment is set
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
