"""
SpritePal UI Components

Reusable dialog architecture components for consistent UI development.
"""

# Import all components from subdirectories
from .base.dialog_base import BaseDialog, SplitterDialog, TabbedDialog
from .inputs.file_selector import FileSelector
from .inputs.form_row import (
    FormRow,
    create_horizontal_form_row,
    create_vertical_form_row,
)
from .inputs.hex_offset_input import HexOffsetInput
from .layouts.styled_group_box import StyledGroupBox
from .layouts.styled_splitter import StyledSplitter

__all__ = [
    "BaseDialog",
    "FileSelector",
    "FormRow",
    "HexOffsetInput",
    "SplitterDialog",
    "StyledGroupBox",
    "StyledSplitter",
    "TabbedDialog",
    "create_horizontal_form_row",
    "create_vertical_form_row",
]
