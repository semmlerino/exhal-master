#!/usr/bin/env python3
"""
Launch script for Kirby Super Star Sprite Editor
Run this from the main exhal-master directory
Uses the refactored MVC architecture
"""

import os
import sys

# Add sprite_editor to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sprite_editor.application import main

if __name__ == "__main__":
    main()
