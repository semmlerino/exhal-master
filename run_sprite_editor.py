#!/usr/bin/env python3
"""
Launch script for Kirby Super Star Sprite Editor
Run this from the main exhal-master directory
"""

import sys
import os

# Add sprite_editor to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sprite_editor.sprite_editor_gui import main

if __name__ == "__main__":
    main()