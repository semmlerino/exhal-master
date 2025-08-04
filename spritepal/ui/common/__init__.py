"""
Common UI utilities and helpers.
"""

from .collapsible_group_box import CollapsibleGroupBox
from .error_handler import ErrorHandler, get_error_handler, reset_error_handler
from .file_dialogs import (
    FileDialogHelper,
    browse_for_directory,
    browse_for_open_file,
    browse_for_save_file,
)
from .spacing_constants import *  # Import all spacing constants
from .tabbed_widget_base import TabbedWidgetBase
from .widget_factory import (
    WidgetFactory,
    create_browse_layout,
    create_checkbox_with_tooltip,
    create_info_label,
)
from .worker_manager import WorkerManager

__all__ = [
    "CollapsibleGroupBox",
    "ErrorHandler",
    "FileDialogHelper",
    "TabbedWidgetBase",
    "WidgetFactory",
    "WorkerManager",
    "browse_for_directory",
    "browse_for_open_file",
    "browse_for_save_file",
    "create_browse_layout",
    "create_checkbox_with_tooltip",
    "create_info_label",
    "get_error_handler",
    "reset_error_handler"
]
