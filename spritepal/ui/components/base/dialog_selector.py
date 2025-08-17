"""
Dialog implementation selector with feature flag support.

This module provides a feature flag system that allows switching between the
legacy DialogBase implementation and the new composed dialog implementation.

Environment Variables:
    SPRITEPAL_USE_COMPOSED_DIALOGS: Controls which implementation is used
        - '0' or not set (default): Use legacy DialogBase
        - '1': Use new composed DialogBaseMigrationAdapter

The feature flag defaults to legacy for backward compatibility and safety during migration.
Once the new implementation is fully validated, the default can be changed or this
selector can be removed entirely.

Usage:
    # This module exports DialogBase - the actual class depends on the feature flag
    from ui.components.base.dialog_selector import DialogBase

    # Or use the utility functions to check/control the feature flag
    from ui.components.base.dialog_selector import (
        get_dialog_implementation,
        set_dialog_implementation,
        is_composed_dialogs_enabled
    )
"""

import os
from typing import TYPE_CHECKING, Union, Type, Any

from utils.logging_config import get_logger

if TYPE_CHECKING:
    from .dialog_base import DialogBase as DialogBaseType
    from .dialog_base import InitializationOrderError as InitializationOrderErrorType
    from .composed.migration_adapter import DialogBaseMigrationAdapter

logger = get_logger(__name__)

# Feature flag environment variable
FEATURE_FLAG_ENV_VAR = "SPRITEPAL_USE_COMPOSED_DIALOGS"


def is_composed_dialogs_enabled() -> bool:
    """Check if composed dialogs are enabled via feature flag.

    Returns:
        bool: True if composed dialogs should be used, False for legacy dialogs.
    """
    flag_value = os.environ.get(FEATURE_FLAG_ENV_VAR, "0").lower()
    return flag_value in ("1", "true", "yes", "on")


def get_dialog_implementation() -> str:
    """Get the current dialog implementation type.

    Returns:
        str: Either "legacy" or "composed" indicating which implementation is active.
    """
    return "composed" if is_composed_dialogs_enabled() else "legacy"


def set_dialog_implementation(use_composed: bool) -> None:
    """Set the dialog implementation type via environment variable.

    Args:
        use_composed: If True, enables composed dialogs. If False, uses legacy dialogs.

    Note:
        This sets the environment variable for the current process.
        The change will take effect on the next import of this module.
        For persistent changes across application restarts, set the
        environment variable externally.
    """
    os.environ[FEATURE_FLAG_ENV_VAR] = "1" if use_composed else "0"
    logger.info(f"Dialog implementation set to: {'composed' if use_composed else 'legacy'}")


# Import the appropriate implementation based on feature flag
# Handle import gracefully for testing environments without Qt
DialogBase: Type[Any] = None  # type: ignore[assignment]
InitializationOrderError: Type[Any] = None  # type: ignore[assignment]
_implementation_source = "none"

try:
    if is_composed_dialogs_enabled():
        logger.info("Using composed dialog implementation (DialogBaseMigrationAdapter)")
        try:
            from .composed.migration_adapter import (
                DialogBaseMigrationAdapter,
            )
            from .composed.migration_adapter import InitializationOrderError as ComposedInitializationOrderError
            DialogBase = DialogBaseMigrationAdapter  # type: ignore[assignment]
            InitializationOrderError = ComposedInitializationOrderError  # type: ignore[assignment]
            _implementation_source = "composed.migration_adapter"
        except ImportError as e:
            logger.error(f"Failed to import composed dialog implementation: {e}")
            logger.warning("Falling back to legacy dialog implementation")
            from .dialog_base import DialogBase as LegacyDialogBase, InitializationOrderError as LegacyInitializationOrderError
            DialogBase = LegacyDialogBase  # type: ignore[assignment]
            InitializationOrderError = LegacyInitializationOrderError  # type: ignore[assignment]
            _implementation_source = "dialog_base (fallback)"
    else:
        logger.info("Using legacy dialog implementation (DialogBase)")
        from .dialog_base import DialogBase as LegacyDialogBase, InitializationOrderError as LegacyInitializationOrderError
        DialogBase = LegacyDialogBase  # type: ignore[assignment]
        InitializationOrderError = LegacyInitializationOrderError  # type: ignore[assignment]
        _implementation_source = "dialog_base"
except ImportError as e:
    logger.warning(f"Qt dependencies not available: {e}")
    logger.info("Dialog implementations will not be available (testing mode)")
    _implementation_source = "unavailable (no Qt)"

    # Create placeholder classes for testing
    class DialogBase:
        """Placeholder DialogBase for testing environments without Qt."""
        pass

    class InitializationOrderError(Exception):
        """Placeholder InitializationOrderError for testing."""
        pass

# Log which implementation was actually loaded
logger.debug(f"DialogBase loaded from: {_implementation_source}")

# Export the selected implementation
__all__ = [
    "DialogBase",
    "InitializationOrderError",
    "get_dialog_implementation",
    "is_composed_dialogs_enabled",
    "set_dialog_implementation"
]
