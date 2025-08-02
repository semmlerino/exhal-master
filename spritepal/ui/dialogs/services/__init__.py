"""
Services for Dialog State Management

This package contains dialog state management services:
- ViewStateManager: Window state and position management (working well)

Note: The over-engineered MVP services (ManualOffsetController, ROMDataSession,
OffsetExplorationService) have been removed and consolidated into the simplified
ManualOffsetDialogSimplified for better stability and maintainability.
"""

from .view_state_manager import ViewStateManager

__all__ = [
    "ViewStateManager"
]
