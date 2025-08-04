"""
Dialog components for SpritePal UI
"""

# Import dialog components
from .manual_offset_unified_integrated import UnifiedManualOffsetDialog
from .resume_scan_dialog import ResumeScanDialog
from .settings_dialog import SettingsDialog
from .user_error_dialog import UserErrorDialog

# Primary interface
ManualOffsetDialog = UnifiedManualOffsetDialog

__all__ = [
    "ManualOffsetDialog",           # Primary interface (unified dialog)
    "ResumeScanDialog",
    "SettingsDialog",
    "UnifiedManualOffsetDialog",    # Explicit new dialog name
    "UserErrorDialog"
]
