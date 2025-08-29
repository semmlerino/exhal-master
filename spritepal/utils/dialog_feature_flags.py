"""
Utility functions for managing dialog implementation feature flags.

This module provides convenient access to dialog feature flag functionality
from anywhere in the codebase without requiring knowledge of the internal
implementation details.

Examples:
    # Check current implementation
    if get_dialog_implementation() == "composed":
        print("Using new composed dialogs")

    # Enable composed dialogs for testing
    set_dialog_implementation(True)

    # Simple boolean check
    if is_composed_dialogs_enabled():
        # Handle composed-specific logic
        pass
"""
from __future__ import annotations

from ui.components.base.dialog_selector import (
    get_dialog_implementation as _get_dialog_implementation,
)
from ui.components.base.dialog_selector import (
    is_composed_dialogs_enabled as _is_composed_dialogs_enabled,
)
from ui.components.base.dialog_selector import (
    set_dialog_implementation as _set_dialog_implementation,
)


def get_dialog_implementation() -> str:
    """Get the current dialog implementation type.

    Returns:
        str: Either "legacy" or "composed" indicating which implementation is active.
    """
    return _get_dialog_implementation()

def set_dialog_implementation(use_composed: bool) -> None:
    """Set the dialog implementation type via environment variable.

    Args:
        use_composed: If True, enables composed dialogs. If False, uses legacy dialogs.

    Note:
        This sets the environment variable for the current process.
        The change will take effect on the next import of the dialog selector.
        For persistent changes across application restarts, set the
        SPRITEPAL_USE_COMPOSED_DIALOGS environment variable externally.
    """
    _set_dialog_implementation(use_composed)

def is_composed_dialogs_enabled() -> bool:
    """Check if composed dialogs are enabled via feature flag.

    Returns:
        bool: True if composed dialogs should be used, False for legacy dialogs.
    """
    return _is_composed_dialogs_enabled()

def enable_composed_dialogs() -> None:
    """Enable composed dialog implementation.

    Convenience function equivalent to set_dialog_implementation(True).
    """
    set_dialog_implementation(True)

def enable_legacy_dialogs() -> None:
    """Enable legacy dialog implementation.

    Convenience function equivalent to set_dialog_implementation(False).
    """
    set_dialog_implementation(False)

__all__ = [
    "enable_composed_dialogs",
    "enable_legacy_dialogs",
    "get_dialog_implementation",
    "is_composed_dialogs_enabled",
    "set_dialog_implementation"
]
