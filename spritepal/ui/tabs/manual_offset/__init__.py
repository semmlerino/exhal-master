"""
Manual offset tab widgets.

This module provides tab widgets for the manual offset dialog:
- SimpleBrowseTab: ROM navigation and offset control
- SimpleSmartTab: Region-based smart navigation
- SimpleHistoryTab: Found sprite history tracking
"""

from .browse_tab import SimpleBrowseTab
from .history_tab import SimpleHistoryTab
from .smart_tab import SimpleSmartTab

__all__ = [
    "SimpleBrowseTab",
    "SimpleHistoryTab",
    "SimpleSmartTab",
]
