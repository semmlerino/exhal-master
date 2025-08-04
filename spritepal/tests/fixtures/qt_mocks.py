"""
DEPRECATED: This module has been superseded by tests/infrastructure/mock_factory.py
and tests/infrastructure/qt_mocks.py.

Please use the new consolidated mock infrastructure instead.
For backward compatibility, this module now imports from the new infrastructure.
"""

import warnings

# Import from new infrastructure for backward compatibility
from ..infrastructure.qt_mocks import (
    MockSignal,
    MockQWidget, 
    MockQPixmap,
    MockQLabel,
    MockQThread,
    create_mock_signals,
)
from ..infrastructure.mock_factory import (
    MockFactory,
    create_mock_main_window,
    create_mock_extraction_worker,
    create_mock_extraction_manager,
)

# Deprecation warning
warnings.warn(
    "tests/fixtures/qt_mocks.py is deprecated. "
    "Use tests/infrastructure/mock_factory.py and tests/infrastructure/qt_mocks.py instead.",
    DeprecationWarning,
    stacklevel=2
)


# Backward compatibility aliases (original definitions are now in infrastructure/)
def create_mock_file_dialogs():
    """Backward compatibility function."""
    return MockFactory.create_file_dialogs()


def create_mock_qimage():
    """Backward compatibility function."""
    return MockFactory.create_qimage()


def create_mock_drag_drop_event():
    """Backward compatibility function."""
    return MockFactory.create_drag_drop_event()