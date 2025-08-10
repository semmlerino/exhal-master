"""
Manual Offset Dialog - Composed Implementation

This module provides a composed implementation of the UnifiedManualOffsetDialog
that maintains full backward compatibility while using composition instead of inheritance.
"""

from .manual_offset_dialog_adapter import ManualOffsetDialogAdapter

# Export the adapter as the main dialog class for backward compatibility
UnifiedManualOffsetDialog = ManualOffsetDialogAdapter

__all__ = ["ManualOffsetDialogAdapter", "UnifiedManualOffsetDialog"]
