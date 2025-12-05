"""
Root conftest.py for all tests in the project.
Delegates Qt configuration to SpritePal's infrastructure.

NOTE: SpritePal uses PySide6, NOT PyQt6. All Qt configuration is delegated
to spritepal.tests.infrastructure.environment_detection which properly
configures PySide6 for headless/offscreen testing.
"""

import sys
from pathlib import Path

import pytest

# Add project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Delegate Qt configuration to SpritePal's infrastructure
# This handles PySide6 configuration correctly for all environments
try:
    from spritepal.tests.infrastructure.environment_detection import (
        configure_qt_for_environment,
        get_environment_info,
    )
    configure_qt_for_environment()
    _env_info = get_environment_info()
    QT_CONFIGURED = True
except ImportError:
    # SpritePal infrastructure not available (e.g., running non-SpritePal tests)
    QT_CONFIGURED = False
    _env_info = None


@pytest.fixture(scope="session", autouse=True)
def qt_headless_config():
    """
    Automatically configure Qt for headless testing.
    Delegates to SpritePal's infrastructure for proper PySide6 configuration.
    """
    if QT_CONFIGURED and _env_info and _env_info.is_headless:
        print(f"Qt configured for headless environment: {_env_info.platform}")
