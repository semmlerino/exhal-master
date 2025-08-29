"""
DEPRECATED: This module has been superseded by tests/infrastructure/mock_factory.py
and tests/infrastructure/qt_mocks.py.

Please use the new consolidated mock infrastructure instead.
For backward compatibility, this module now imports from the new infrastructure.
"""

import warnings

from tests.infrastructure.mock_factory import MockFactory
from tests.infrastructure.real_component_factory import RealComponentFactory

# Import from new infrastructure for backward compatibility

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
    factory = RealComponentFactory()
    return factory.create_file_dialogs()

def create_mock_qimage():
    """Backward compatibility function."""
    return MockFactory.create_qimage()

def create_mock_drag_drop_event():
    """Backward compatibility function."""
    return MockFactory.create_drag_drop_event()

def create_mock_extraction_manager():
    """Backward compatibility function."""
    return MockFactory.create_extraction_manager()

def create_mock_extraction_worker():
    """Backward compatibility function."""
    return MockFactory.create_extraction_worker()

def create_mock_signals():
    """Backward compatibility function."""
    from tests.infrastructure.qt_mocks import (
        create_mock_signals as _create_mock_signals,
    )
    return _create_mock_signals()

def create_mock_main_window():
    """Backward compatibility function."""
    return MockFactory.create_main_window()
