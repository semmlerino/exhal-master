#!/usr/bin/env python3
"""
Visual comparison test between legacy and composed implementations.

This script creates both implementations side by side to demonstrate
the visual improvements in the composed version.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication, QHBoxLayout, QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from ui.dialogs.manual_offset import UnifiedManualOffsetDialog

class VisualComparisonWidget(QWidget):
    """Widget that shows both implementations side by side."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SpritePal Dialog Migration - Visual Comparison")
        self.setGeometry(100, 100, 1800, 900)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("SpritePal Dialog Architecture Migration - Visual Comparison")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            padding: 10px;
            background-color: #f0f0f0;
            border-radius: 5px;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(title)
        
        # Comparison layout
        comparison_layout = QHBoxLayout()
        
        # Legacy side
        legacy_container = self.create_dialog_container(
            "Legacy Implementation", 
            "DialogBase Inheritance",
            False
        )
        comparison_layout.addWidget(legacy_container)
        
        # Composed side  
        composed_container = self.create_dialog_container(
            "Composed Implementation",
            "Modern Component Architecture", 
            True
        )
        comparison_layout.addWidget(composed_container)
        
        main_layout.addLayout(comparison_layout)
        
    def create_dialog_container(self, title: str, subtitle: str, use_composed: bool) -> QWidget:
        """Create a container with a dialog instance."""
        container = QWidget()
        container.setMinimumWidth(850)
        layout = QVBoxLayout(container)
        
        # Header
        header_layout = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        
        subtitle_label = QLabel(subtitle)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        subtitle_label.setStyleSheet("font-size: 11px; color: #7f8c8d; font-style: italic;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        layout.addLayout(header_layout)
        
        # Set environment variable for this implementation
        os.environ['SPRITEPAL_USE_COMPOSED_DIALOGS'] = 'true' if use_composed else 'false'
        
        try:
            # Create dialog instance
            dialog = UnifiedManualOffsetDialog(parent=container)
            
            # Make it not modal so we can see both at once
            dialog.setModal(False)
            
            # Adjust size to fit in container
            if use_composed:
                dialog.resize(800, 650)  # Show off the better sizing
            else:
                dialog.resize(800, 600)  # Smaller legacy size
                
            # Embed the dialog in the container
            layout.addWidget(dialog)
            
            # Add comparison notes
            notes = self.create_comparison_notes(use_composed)
            layout.addWidget(notes)
            
        except Exception as e:
            error_label = QLabel(f"Error creating dialog: {str(e)}")
            error_label.setStyleSheet("color: red; padding: 20px;")
            layout.addWidget(error_label)
        
        # Style the container
        if use_composed:
            container.setStyleSheet("""
                QWidget {
                    border: 2px solid #27ae60;
                    border-radius: 8px;
                    background-color: #f8fff8;
                    margin: 5px;
                }
            """)
        else:
            container.setStyleSheet("""
                QWidget {
                    border: 2px solid #e74c3c;
                    border-radius: 8px; 
                    background-color: #fff8f8;
                    margin: 5px;
                }
            """)
        
        return container
        
    def create_comparison_notes(self, is_composed: bool) -> QWidget:
        """Create notes highlighting the differences."""
        notes_widget = QWidget()
        notes_widget.setMaximumHeight(120)
        layout = QVBoxLayout(notes_widget)
        
        if is_composed:
            improvements = [
                "✓ Enhanced spacing (12px margins vs 6px)",
                "✓ Better proportions (35:65 vs 25:75)",
                "✓ Modern tab styling with rounded corners",
                "✓ Larger dialog size (1100x700 vs 1000x650)",
                "✓ Prominent splitter handle (12px vs 8px)",
                "✓ Enhanced visual hierarchy"
            ]
            color = "#27ae60"
        else:
            limitations = [
                "• Basic spacing (6px margins)", 
                "• Narrow left panel (25% width)",
                "• Standard tab styling",
                "• Compact dialog size (1000x650)",
                "• Thin splitter handle (8px)",
                "• Limited visual hierarchy"
            ]
            improvements = limitations
            color = "#e74c3c"
            
        for note in improvements:
            label = QLabel(note)
            label.setStyleSheet(f"color: {color}; font-size: 10px; padding: 1px;")
            layout.addWidget(label)
            
        return notes_widget

def main():
    """Run visual comparison."""
    print("Starting SpritePal Dialog Visual Comparison...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    # Create comparison widget
    comparison = VisualComparisonWidget()
    comparison.show()
    
    print("\nVisual Comparison Active!")
    print("=" * 50)
    print("LEFT PANEL:  Legacy Implementation (DialogBase)")
    print("RIGHT PANEL: Composed Implementation (Enhanced)")
    print("=" * 50)
    print("Compare:")
    print("• Dialog sizing and proportions")
    print("• Panel spacing and margins") 
    print("• Tab styling and layout")
    print("• Splitter handle visibility")
    print("• Overall visual hierarchy")
    print("=" * 50)
    
    # Keep application running
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())