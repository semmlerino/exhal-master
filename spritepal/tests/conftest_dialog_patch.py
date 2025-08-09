"""
Early patching of dialog imports to prevent collection-time timeouts.

This module must be imported before any test that uses dialogs to prevent
the DialogBase metaclass from being triggered during import.
"""

import sys
from unittest.mock import MagicMock

# Import our mock dialogs
from tests.infrastructure.mock_dialogs import (
    MockAdvancedSearchDialog,
    MockGridArrangementDialog,
    MockResumeScanDialog,
    MockRowArrangementDialog,
    MockSettingsDialog,
    MockUnifiedManualOffsetDialog,
    MockUserErrorDialog,
)

# Patch all dialog modules BEFORE they can be imported
sys.modules['ui.dialogs.manual_offset_unified_integrated'] = MagicMock(
    UnifiedManualOffsetDialog=MockUnifiedManualOffsetDialog,
    SimpleBrowseTab=MagicMock,
    SimpleSmartTab=MagicMock,
    SimpleHistoryTab=MagicMock,
)

sys.modules['ui.dialogs.settings_dialog'] = MagicMock(
    SettingsDialog=MockSettingsDialog
)

sys.modules['ui.dialogs.grid_arrangement_dialog'] = MagicMock(
    GridArrangementDialog=MockGridArrangementDialog
)

sys.modules['ui.dialogs.row_arrangement_dialog'] = MagicMock(
    RowArrangementDialog=MockRowArrangementDialog
)

sys.modules['ui.dialogs.advanced_search_dialog'] = MagicMock(
    AdvancedSearchDialog=MockAdvancedSearchDialog
)

sys.modules['ui.dialogs.resume_scan_dialog'] = MagicMock(
    ResumeScanDialog=MockResumeScanDialog
)

sys.modules['ui.dialogs.user_error_dialog'] = MagicMock(
    UserErrorDialog=MockUserErrorDialog
)

# Also patch the unified dialog components
sys.modules['ui.dialogs'] = MagicMock(
    manual_offset_unified_integrated=sys.modules['ui.dialogs.manual_offset_unified_integrated'],
    settings_dialog=sys.modules['ui.dialogs.settings_dialog'],
    grid_arrangement_dialog=sys.modules['ui.dialogs.grid_arrangement_dialog'],
    row_arrangement_dialog=sys.modules['ui.dialogs.row_arrangement_dialog'],
    advanced_search_dialog=sys.modules['ui.dialogs.advanced_search_dialog'],
    resume_scan_dialog=sys.modules['ui.dialogs.resume_scan_dialog'],
    user_error_dialog=sys.modules['ui.dialogs.user_error_dialog'],
)
