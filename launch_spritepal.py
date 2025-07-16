#!/usr/bin/env python3
"""
Launch script for SpritePal
"""

import sys
import os
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run SpritePal
try:
    from spritepal.spritepal import main
    main()
except ImportError as e:
    print(f"Error importing SpritePal: {e}")
    print("\nMake sure you have the required dependencies:")
    print("  pip install PyQt6 Pillow")
    sys.exit(1)
except Exception as e:
    print(f"Error launching SpritePal: {e}")
    sys.exit(1)