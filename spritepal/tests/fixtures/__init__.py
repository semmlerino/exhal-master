"""
Test fixtures package for SpritePal test suite.

This package contains reusable test components including Qt mocks,
test data generators, and common test utilities.
"""

from .qt_mocks import (
    MockQLabel,
    MockQPixmap,
    MockQThread,
    MockQWidget,
    MockSignal,
    create_mock_drag_drop_event,
    create_mock_extraction_manager,
    create_mock_extraction_worker,
    create_mock_file_dialogs,
    create_mock_injection_manager,
    create_mock_main_window,
    create_mock_qimage,
    create_mock_session_manager,
    create_mock_settings_manager,
    create_mock_signals,
)

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
    "create_mock_injection_manager",
    "create_mock_main_window",
    "create_mock_qimage",
    "create_mock_session_manager",
    "create_mock_settings_manager",
    "create_mock_signals",
]
