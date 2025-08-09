"""
Test fixtures package for SpritePal test suite.

This package contains reusable test components including Qt mocks,
test data generators, and common test utilities.
"""

from tests.infrastructure.mock_factory import MockFactory
from tests.infrastructure.qt_mocks import (
    MockQLabel,
    MockQPixmap,
    MockQThread,
    MockQWidget,
    MockSignal,
)

# Create backward compatibility functions
create_mock_drag_drop_event = MockFactory.create_drag_drop_event
create_mock_extraction_manager = MockFactory.create_extraction_manager
create_mock_extraction_worker = MockFactory.create_extraction_worker
create_mock_file_dialogs = MockFactory.create_file_dialogs
create_mock_main_window = MockFactory.create_main_window
create_mock_qimage = MockFactory.create_qimage

__all__ = [
    "MockQLabel",
    "MockQPixmap",
    "MockQThread",
    "MockQWidget",
    "MockSignal",
    "create_mock_drag_drop_event",
    "create_mock_extraction_manager",
    "create_mock_extraction_worker",
    "create_mock_file_dialogs",
    "create_mock_main_window",
    "create_mock_qimage",
]
