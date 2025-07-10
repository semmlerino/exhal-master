#!/usr/bin/env python3
"""
Test script to verify the ProgressDialog.update_progress fix.
Tests both signal connections and direct calls.
"""

import sys
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import QTimer
from pixel_editor_widgets import ProgressDialog
from pixel_editor_workers import FileLoadWorker

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Progress Dialog Fix Test")
        self.setGeometry(100, 100, 400, 300)
        
        layout = QVBoxLayout()
        
        self.status_label = QLabel("Click a button to test the fix")
        layout.addWidget(self.status_label)
        
        # Test 1: Direct calls with message
        btn1 = QPushButton("Test Direct Calls (value + message)")
        btn1.clicked.connect(self.test_direct_calls)
        layout.addWidget(btn1)
        
        # Test 2: Direct calls without message
        btn2 = QPushButton("Test Direct Calls (value only)")
        btn2.clicked.connect(self.test_value_only)
        layout.addWidget(btn2)
        
        # Test 3: Signal connection
        btn3 = QPushButton("Test Signal Connection")
        btn3.clicked.connect(self.test_signal_connection)
        layout.addWidget(btn3)
        
        self.setLayout(layout)
        
    def test_direct_calls(self):
        """Test direct calls with both value and message"""
        self.status_label.setText("Testing direct calls with message...")
        
        dialog = ProgressDialog("Testing Direct Calls", self)
        dialog.show()
        
        # This was failing before the fix
        try:
            dialog.update_progress(0, "Starting...")
            QTimer.singleShot(500, lambda: dialog.update_progress(30, "Reading file..."))
            QTimer.singleShot(1000, lambda: dialog.update_progress(60, "Processing..."))
            QTimer.singleShot(1500, lambda: dialog.update_progress(90, "Almost done..."))
            QTimer.singleShot(2000, lambda: dialog.update_progress(100, "Complete!"))
            QTimer.singleShot(2500, dialog.accept)
            
            self.status_label.setText("✅ Direct calls with message: SUCCESS")
        except Exception as e:
            self.status_label.setText(f"❌ Direct calls with message: FAILED - {e}")
            dialog.reject()
    
    def test_value_only(self):
        """Test direct calls with value only"""
        self.status_label.setText("Testing direct calls without message...")
        
        dialog = ProgressDialog("Testing Value Only", self)
        dialog.show()
        
        # This should work both before and after the fix
        try:
            dialog.update_progress(0)
            QTimer.singleShot(500, lambda: dialog.update_progress(33))
            QTimer.singleShot(1000, lambda: dialog.update_progress(66))
            QTimer.singleShot(1500, lambda: dialog.update_progress(100))
            QTimer.singleShot(2000, dialog.accept)
            
            self.status_label.setText("✅ Direct calls without message: SUCCESS")
        except Exception as e:
            self.status_label.setText(f"❌ Direct calls without message: FAILED - {e}")
            dialog.reject()
    
    def test_signal_connection(self):
        """Test signal connection (should work both before and after)"""
        self.status_label.setText("Testing signal connection...")
        
        dialog = ProgressDialog("Testing Signal Connection", self)
        
        # Create a mock worker
        worker = FileLoadWorker("test.png")
        
        # Connect signal - this passes only the value
        worker.progress.connect(dialog.update_progress)
        
        # Simulate progress
        dialog.show()
        try:
            worker.progress.emit(0)
            QTimer.singleShot(500, lambda: worker.progress.emit(25))
            QTimer.singleShot(1000, lambda: worker.progress.emit(50))
            QTimer.singleShot(1500, lambda: worker.progress.emit(75))
            QTimer.singleShot(2000, lambda: worker.progress.emit(100))
            QTimer.singleShot(2500, dialog.accept)
            
            self.status_label.setText("✅ Signal connection: SUCCESS")
        except Exception as e:
            self.status_label.setText(f"❌ Signal connection: FAILED - {e}")
            dialog.reject()

def main():
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    print("Progress Dialog Fix Test")
    print("=" * 40)
    print("This tests that update_progress works with:")
    print("1. Direct calls with value + message")
    print("2. Direct calls with value only")
    print("3. Signal connections (value only)")
    print()
    print("All three should work after the fix!")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()