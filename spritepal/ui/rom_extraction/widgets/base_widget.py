"""Base widget class for ROM extraction widgets"""

from PyQt6.QtWidgets import QGroupBox, QSizePolicy, QWidget


class BaseExtractionWidget(QWidget):
    """Base class for extraction panel widgets with common functionality"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def _create_group_box(self, title: str) -> QGroupBox:
        """Create a group box with consistent styling"""
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 8px;
                padding-top: 10px;
                padding-left: 8px;
                padding-right: 8px;
                padding-bottom: 8px;
                border: 1px solid #555;
                border-radius: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px 0 6px;
            }
        """)
        group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        return group
