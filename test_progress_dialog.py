#!/usr/bin/env python3
"""
Test script for the ProgressDialog widget
"""

import sys
import time
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget

from pixel_editor_widgets import ProgressDialog


class WorkerThread(QThread):
    """Example worker thread to simulate async operation"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.cancelled = False
    
    def run(self):
        """Simulate some work"""
        total_items = 20
        for i in range(total_items):
            if self.cancelled:
                break
                
            # Simulate work
            time.sleep(0.2)
            
            # Report progress
            progress_percent = int((i + 1) * 100 / total_items)
            self.progress.emit(progress_percent, f"Processing item {i + 1} of {total_items}...")
        
        self.finished.emit()
    
    def cancel(self):
        """Cancel the operation"""
        self.cancelled = True


class TestWindow(QMainWindow):
    """Test window to demonstrate ProgressDialog"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ProgressDialog Test")
        self.setGeometry(100, 100, 400, 200)
        
        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Create layout
        layout = QVBoxLayout()
        central.setLayout(layout)
        
        # Create buttons
        self.start_button = QPushButton("Start Operation")
        self.start_button.clicked.connect(self.start_operation)
        layout.addWidget(self.start_button)
        
        self.worker = None
        self.progress_dialog = None
    
    def start_operation(self):
        """Start the async operation with progress dialog"""
        # Create and show progress dialog
        self.progress_dialog = ProgressDialog("Processing Items", self)
        self.progress_dialog.cancelled.connect(self.on_cancel)
        
        # Create worker thread
        self.worker = WorkerThread()
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        
        # Start operation
        self.worker.start()
        self.progress_dialog.show()
        
        # Disable start button
        self.start_button.setEnabled(False)
    
    def update_progress(self, value, message):
        """Update progress dialog"""
        if self.progress_dialog:
            self.progress_dialog.update_progress(value, message)
    
    def on_cancel(self):
        """Handle cancel request"""
        if self.worker:
            self.worker.cancel()
            self.worker.wait()  # Wait for thread to finish
    
    def on_finished(self):
        """Handle operation finished"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        self.worker = None
        self.start_button.setEnabled(True)


def main():
    """Run the test application"""
    app = QApplication(sys.argv)
    
    # Apply dark theme to match pixel editor
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
        }
        QPushButton {
            background-color: #3c3c3c;
            border: 2px solid #555;
            color: #ffffff;
            padding: 10px 20px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #484848;
            border-color: #777;
        }
        QPushButton:pressed {
            background-color: #2b2b2b;
            border-color: #333;
        }
        QPushButton:disabled {
            background-color: #1f1f1f;
            color: #666;
            border-color: #333;
        }
    """)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()