"""
Root conftest.py for all tests in the project.

Qt configuration is handled by pyproject.toml (qt_qpa_platform = "offscreen").
SpritePal tests are in spritepal/tests/ with their own conftest.py.
"""

import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
