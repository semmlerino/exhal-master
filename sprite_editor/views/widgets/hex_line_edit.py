#!/usr/bin/env python3
"""
Hex line edit widget for hexadecimal input
Provides a specialized QLineEdit for entering hex values
"""

from PyQt6.QtWidgets import QLineEdit


class HexLineEdit(QLineEdit):
    """Line edit for hexadecimal input with validation and conversion utilities"""

    def __init__(self, default="0x0000"):
        """
        Initialize the hex line edit

        Args:
            default: Default hex value to display
        """
        super().__init__(default)
        self.setMaxLength(8)
        self._setup_ui()

    def _setup_ui(self):
        """Configure the widget appearance and behavior"""
        self.setPlaceholderText("Enter hex value (e.g., 0x1234)")
        self.setToolTip("Enter a hexadecimal value")

    def value(self):
        """
        Get the hex value as integer

        Returns:
            int: The hex value converted to integer, or 0 if invalid
        """
        try:
            text = self.text().strip()
            if text.startswith("0x") or text.startswith("0X"):
                return int(text, 16)
            else:
                # Assume hex even without 0x prefix
                return int(text, 16)
        except ValueError:
            return 0

    def setValue(self, value):
        """
        Set value from integer

        Args:
            value: Integer value to convert to hex and display
        """
        self.setText(f"0x{value:04X}")

    def isValid(self):
        """
        Check if the current text is a valid hex value

        Returns:
            bool: True if valid hex, False otherwise
        """
        try:
            self.value()
            return True
        except (ValueError, TypeError, AttributeError):
            return False
