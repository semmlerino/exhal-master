#!/usr/bin/env python3
"""Debug script to trace duplicate slider issue in manual offset dialog"""


import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Monkey patch imports to add debug logging
original_import = __builtins__.__import__

def debug_import(name, *args, **kwargs):
    result = original_import(name, *args, **kwargs)
    if "manual_offset" in name.lower():
        print(f"[DEBUG] Importing: {name}")
    return result

__builtins__.__import__ = debug_import

import traceback  # noqa: E402

from PyQt6.QtWidgets import (  # noqa: E402
    QApplication,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

# Patch QSlider creation to track instances
original_qslider_init = QSlider.__init__
slider_instances = []

def patched_slider_init(self, *args, **kwargs):
    original_qslider_init(self, *args, **kwargs)
    stack = traceback.extract_stack()
    caller_info = []
    for frame in stack[-10:]:  # Last 10 frames
        if "spritepal" in frame.filename:
            caller_info.append(f"{frame.filename}:{frame.lineno} in {frame.name}")

    slider_instances.append({
        "instance": self,
        "stack": caller_info,
        "parent": self.parent()
    })
    print(f"\n[DEBUG] QSlider created! Total sliders: {len(slider_instances)}")
    print("Called from:")
    for line in caller_info[-5:]:  # Show last 5 relevant frames
        print(f"  {line}")

QSlider.__init__ = patched_slider_init

# Now import the actual application components
from ui.rom_extraction_panel import ManualOffsetDialogSingleton, ROMExtractionPanel  # noqa: E402


class DebugWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Debug Duplicate Slider")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create ROM extraction panel
        self.rom_panel = ROMExtractionPanel(self)
        layout.addWidget(self.rom_panel)

        # Debug button to check dialog state
        debug_btn = QPushButton("Debug: Check Dialog State")
        debug_btn.clicked.connect(self.check_dialog_state)
        layout.addWidget(debug_btn)

        # Debug button to manually open dialog
        open_btn = QPushButton("Debug: Open Manual Offset Dialog")
        open_btn.clicked.connect(self.open_dialog)
        layout.addWidget(open_btn)

    def check_dialog_state(self):
        print("\n=== DIALOG STATE CHECK ===")
        print(f"Singleton instance exists: {ManualOffsetDialogSingleton._instance is not None}")
        if ManualOffsetDialogSingleton._instance:
            print(f"Dialog visible: {ManualOffsetDialogSingleton._instance.isVisible()}")
            print(f"Dialog ID: {getattr(ManualOffsetDialogSingleton._instance, '_debug_id', 'Unknown')}")

        print(f"\nTotal QSlider instances created: {len(slider_instances)}")
        for i, info in enumerate(slider_instances):
            print(f"\nSlider {i+1}:")
            print(f"  Parent: {info['parent']}")
            print(f"  Parent type: {type(info['parent']).__name__ if info['parent'] else 'None'}")
            if info["parent"] and hasattr(info["parent"], "window"):
                window = info["parent"].window()
                print(f"  Top-level window: {type(window).__name__}")
                if hasattr(window, "_debug_id"):
                    print(f"  Window debug ID: {window._debug_id}")

    def open_dialog(self):
        print("\n=== MANUALLY OPENING DIALOG ===")
        # Load a test ROM first
        test_rom = "/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master/spritepal/tests/fixtures/test_rom.sfc"
        if os.path.exists(test_rom):
            self.rom_panel._load_rom_file(test_rom)
        else:
            print("Warning: Test ROM not found, dialog may not work properly")

        # Now open the dialog
        self.rom_panel._open_manual_offset_dialog()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DebugWindow()
    window.show()

    # Initial state check
    window.check_dialog_state()

    sys.exit(app.exec())
