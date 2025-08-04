"""
UI managers package

Contains manager classes that handle specific UI responsibilities,
following the Single Responsibility Principle.
"""

from .menu_bar_manager import MenuBarManager, MenuBarActionsProtocol
from .toolbar_manager import ToolbarManager, ToolbarActionsProtocol
from .status_bar_manager import StatusBarManager
from .output_settings_manager import OutputSettingsManager, OutputSettingsActionsProtocol
from .tab_coordinator import TabCoordinator, TabCoordinatorActionsProtocol
from .preview_coordinator import PreviewCoordinator
from .keyboard_handler import KeyboardShortcutHandler, KeyboardActionsProtocol
from .session_coordinator import SessionCoordinator

__all__ = [
    "MenuBarManager",
    "MenuBarActionsProtocol",
    "ToolbarManager", 
    "ToolbarActionsProtocol",
    "StatusBarManager",
    "OutputSettingsManager",
    "OutputSettingsActionsProtocol",
    "TabCoordinator",
    "TabCoordinatorActionsProtocol", 
    "PreviewCoordinator",
    "KeyboardShortcutHandler",
    "KeyboardActionsProtocol",
    "SessionCoordinator",
]