#!/usr/bin/env python3
"""Convenience launcher for the pixel editor from root directory"""

import os
import subprocess
import sys

# Get the directory where this script is located (exhal-master)
script_dir = os.path.dirname(os.path.abspath(__file__))
launcher_path = os.path.join(script_dir, "pixel_editor", "launch_pixel_editor.py")

if os.path.exists(launcher_path):
    sys.exit(subprocess.call([sys.executable, launcher_path] + sys.argv[1:]))
else:
    print(f"Error: Pixel editor launcher not found at {launcher_path}")
    sys.exit(1)
