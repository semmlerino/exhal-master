#!/usr/bin/env python3
"""
Wrapper for indexed_pixel_editor_v3 to maintain backward compatibility
"""

# Import everything from the v3 module
# Import the entire pixel_editor_utils module to allow tests to modify DEBUG_MODE
from . import pixel_editor_utils
from .indexed_pixel_editor_v3 import *

# Also explicitly import the specific items that tests might expect

# Re-export DEBUG_MODE as an attribute of this module
DEBUG_MODE = pixel_editor_utils.DEBUG_MODE

# Standard library imports
# Override the module attribute to use the pixel_editor_utils module's attribute
import sys

sys.modules[__name__].pixel_editor_utils = pixel_editor_utils
