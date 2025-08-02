"""
Dialog components for SpritePal UI
"""

from .manual_offset_dialog_simplified import ManualOffsetDialogSimplified
from .resume_scan_dialog import ResumeScanDialog
from .settings_dialog import SettingsDialog
from .user_error_dialog import UserErrorDialog

# Legacy import for backward compatibility (until all tests are updated)
try:
    from .manual_offset_dialog import ManualOffsetDialog
    _legacy_available = True
except ImportError:
    _legacy_available = False
    ManualOffsetDialog = None

__all__ = ["ManualOffsetDialogSimplified", "ResumeScanDialog", "SettingsDialog", "UserErrorDialog"]
if _legacy_available:
    __all__.append("ManualOffsetDialog")
