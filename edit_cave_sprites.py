#!/usr/bin/env python3
"""Launch pixel editor with cave sprites and palettes."""
import subprocess
import sys

# Launch the pixel editor with the grayscale sprites
# It will auto-detect the .pal.json files
subprocess.run([
    sys.executable,
    "launch_pixel_editor.py",
    "cave_sprites_editor.png"
])
