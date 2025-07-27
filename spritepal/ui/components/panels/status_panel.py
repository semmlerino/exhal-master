"""
Status Panel for Manual Offset Dialog

Displays detection status, progress information, and scanning progress.
"""

from PyQt6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from spritepal.ui.styles import get_panel_style


class StatusPanel(QWidget):
    """Panel for displaying status information and progress"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(get_panel_style())
        self._setup_ui()

    def _setup_ui(self):
        """Initialize the status panel UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)  # Reduced padding
        layout.setSpacing(3)  # Tighter spacing

        status_label = QLabel("Detection Status")
        status_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 3px;")  # Smaller and tighter
        layout.addWidget(status_label)

        self.detection_info = QLabel("Ready to search for sprites")
        self.detection_info.setWordWrap(True)
        self.detection_info.setStyleSheet("color: #cccccc;")
        layout.addWidget(self.detection_info)

        # Progress bar (initially hidden)
        self.scan_progress = QProgressBar()
        self.scan_progress.setVisible(False)
        layout.addWidget(self.scan_progress)

        self.setLayout(layout)

    def update_status(self, message: str):
        """Update the status message"""
        self.detection_info.setText(message)

    def show_progress(self, minimum: int = 0, maximum: int = 100):
        """Show and configure the progress bar"""
        self.scan_progress.setRange(minimum, maximum)
        self.scan_progress.setValue(minimum)
        self.scan_progress.setVisible(True)

    def hide_progress(self):
        """Hide the progress bar"""
        self.scan_progress.setVisible(False)

    def update_progress(self, value: int):
        """Update the progress bar value"""
        if self.scan_progress.isVisible():
            self.scan_progress.setValue(value)

    def get_progress_bar(self) -> QProgressBar:
        """Get reference to the progress bar for external management"""
        return self.scan_progress
