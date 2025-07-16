#!/usr/bin/env python3
"""
Constants for the Indexed Pixel Editor
Centralizes all magic numbers and configuration values
"""

# ============================================================================
# PALETTE CONSTANTS
# ============================================================================

# Palette dimensions
PALETTE_COLORS_COUNT = 16  # Standard 4bpp palette size
MAX_COLORS = PALETTE_COLORS_COUNT  # Alias for backward compatibility
PALETTE_GRID_COLUMNS = 4  # Palette widget layout
PALETTE_GRID_ROWS = 4  # Palette widget layout
PALETTE_CELL_SIZE = 32  # Size of each color cell in pixels
PALETTE_WIDGET_PADDING = 10  # Padding around palette grid
PALETTE_BORDER_WIDTH = 2  # Border width for selected/external indicators
PALETTE_SELECTION_BORDER_WIDTH = 3  # Border width for selected color

# Palette color calculations
PALETTE_GRAY_INCREMENT = 17  # Grayscale step (255/15 = 17)
PALETTE_WHITE_TEXT_THRESHOLD = 384  # Sum of RGB below this = white text
PALETTE_DATA_SIZE = 768  # Full palette data size (256 colors * 3 channels)
PALETTE_CHANNEL_OFFSET = 3  # RGB channels per color

# Palette indicator sizes
PALETTE_INDICATOR_SIZE = 8  # Size of external palette indicator triangle

# ============================================================================
# SPRITE/IMAGE CONSTANTS
# ============================================================================

# Image format
BITS_PER_PIXEL = 4  # 4bpp indexed color format
MAX_COLOR_INDEX = 15  # Maximum color index (0-15 for 4bpp)
MIN_COLOR_INDEX = 0  # Minimum color index

# Default image dimensions
DEFAULT_IMAGE_WIDTH = 8  # Default new image width
DEFAULT_IMAGE_HEIGHT = 8  # Default new image height

# ============================================================================
# UI DIMENSIONS
# ============================================================================

# Main window
MAIN_WINDOW_WIDTH = 800
MAIN_WINDOW_HEIGHT = 600
MAIN_WINDOW_X = 100
MAIN_WINDOW_Y = 100

# Dialog windows
STARTUP_DIALOG_WIDTH = 500
STARTUP_DIALOG_HEIGHT = 400
PALETTE_SWITCHER_WIDTH = 400
PALETTE_SWITCHER_HEIGHT = 500

# Panel dimensions
LEFT_PANEL_MAX_WIDTH = 200
CANVAS_MIN_SIZE = 200
PREVIEW_MIN_HEIGHT = 100
RECENT_FILES_LIST_MAX_HEIGHT = 150
COLOR_PREVIEW_MIN_HEIGHT = 50

# Button sizes
ZOOM_BUTTON_MAX_WIDTH = 35

# ============================================================================
# ZOOM CONSTANTS
# ============================================================================

# Zoom levels
ZOOM_MIN = 1
ZOOM_MAX = 64
ZOOM_DEFAULT = 4  # Default zoom for sprite sheets
ZOOM_LEVELS = [1, 2, 4, 8, 16, 32, 64]  # Predefined zoom levels
ZOOM_PRESET_1X = 1
ZOOM_PRESET_2X = 2
ZOOM_PRESET_4X = 4
ZOOM_PRESET_8X = 8
ZOOM_PRESET_16X = 16

# Grid visibility
GRID_VISIBLE_THRESHOLD = 4  # Show grid when zoom > this value

# ============================================================================
# PREVIEW CONSTANTS
# ============================================================================

# Preview scaling
PREVIEW_MAX_SIZE = 100  # Maximum preview dimension
PREVIEW_MAX_SCALE = 8  # Maximum scale factor for preview
PREVIEW_VIEWPORT_PADDING = 20  # Padding when fitting to viewport

# ============================================================================
# FILE MANAGEMENT CONSTANTS
# ============================================================================

# Recent files
MAX_RECENT_FILES = 10
MAX_RECENT_PALETTE_FILES = 10

# ============================================================================
# UNDO/REDO CONSTANTS
# ============================================================================

UNDO_STACK_SIZE = 50
REDO_STACK_SIZE = 50

# ============================================================================
# TIMING CONSTANTS
# ============================================================================

STATUS_MESSAGE_TIMEOUT = 3000  # Status bar message duration in milliseconds

# ============================================================================
# SPRITE PALETTE INDICES
# ============================================================================

# Special palette indices (for sprite palettes)
PALETTE_INDEX_KIRBY = 8  # Kirby's default palette (Purple/Pink)
PALETTE_INDEX_COMMON = 11  # Common palette (Yellow/Brown)
PALETTE_INDEX_BLUE = 14  # Palette with blue colors
SPRITE_PALETTE_START = 8  # First sprite palette index
SPRITE_PALETTE_END = 15  # Last sprite palette index

# ============================================================================
# COLOR CONSTANTS
# ============================================================================

# Default grayscale values (RGB tuples for 16 shades)
DEFAULT_GRAYSCALE_PALETTE = [
    (0, 0, 0),  # 0 - Black (transparent)
    (17, 17, 17),  # 1
    (34, 34, 34),  # 2
    (51, 51, 51),  # 3
    (68, 68, 68),  # 4
    (85, 85, 85),  # 5
    (102, 102, 102),  # 6
    (119, 119, 119),  # 7
    (136, 136, 136),  # 8
    (153, 153, 153),  # 9
    (170, 170, 170),  # 10
    (187, 187, 187),  # 11
    (204, 204, 204),  # 12
    (221, 221, 221),  # 13
    (238, 238, 238),  # 14
    (255, 255, 255),  # 15 - White
]

# Default color palette (for color mode)
DEFAULT_COLOR_PALETTE = [
    (0, 0, 0),  # 0 - Black (transparent)
    (255, 183, 197),  # 1 - Kirby pink
    (255, 255, 255),  # 2 - White
    (64, 64, 64),  # 3 - Dark gray (outline)
    (255, 0, 0),  # 4 - Red
    (0, 0, 255),  # 5 - Blue
    (255, 220, 220),  # 6 - Light pink
    (200, 120, 150),  # 7 - Dark pink
    (255, 255, 0),  # 8 - Yellow
    (0, 255, 0),  # 9 - Green
    (255, 128, 0),  # 10 - Orange
    (128, 0, 255),  # 11 - Purple
    (0, 128, 128),  # 12 - Teal
    (128, 128, 0),  # 13 - Olive
    (128, 128, 128),  # 14 - Gray
    (192, 192, 192),  # 15 - Light gray
]

# Special colors
COLOR_INVALID_INDEX = (255, 0, 255)  # Magenta for invalid palette indices
COLOR_GRID_LINES = (128, 128, 128, 128)  # Semi-transparent gray for grid

# ============================================================================
# TOOL CONSTANTS
# ============================================================================

# Tool names
TOOL_PENCIL = "pencil"
TOOL_FILL = "fill"
TOOL_PICKER = "picker"

# Tool indices (for button group)
TOOL_INDEX_PENCIL = 0
TOOL_INDEX_FILL = 1
TOOL_INDEX_PICKER = 2

# ============================================================================
# FILE EXTENSIONS
# ============================================================================

# Supported file types
IMAGE_EXTENSION_PNG = ".png"
PALETTE_EXTENSION_JSON = ".pal.json"
METADATA_EXTENSION_JSON = "_metadata.json"

# File filters
PNG_FILE_FILTER = "PNG Files (*.png);;All Files (*)"
PALETTE_FILE_FILTER = "Palette Files (*.pal.json);;JSON Files (*.json);;All Files (*)"

# ============================================================================
# KEYBOARD SHORTCUTS
# ============================================================================

# Single key shortcuts
KEY_TOGGLE_COLOR_MODE = "C"
KEY_TOGGLE_GRID = "G"
KEY_COLOR_PICKER = "I"
KEY_PALETTE_SWITCHER = "P"

# Zoom shortcuts
KEY_ZOOM_RESET = "Ctrl+0"
KEY_ZOOM_FIT = "Ctrl+Shift+0"

# ============================================================================
# UI STYLING
# ============================================================================

# Font sizes
TITLE_FONT_SIZE = 18
BUTTON_PADDING = 8

# Colors (as style strings)
STYLE_COLOR_SUBTITLE = "#666"
STYLE_COLOR_DISABLED = "#888"
STYLE_COLOR_PREVIEW_BG = "#202020"
STYLE_COLOR_PREVIEW_BORDER = "#666"

# ============================================================================
# VALIDATION CONSTANTS
# ============================================================================

# Minimum valid dimensions
MIN_IMAGE_WIDTH = 1
MIN_IMAGE_HEIGHT = 1

# Maximum dimensions (to prevent memory issues)
MAX_IMAGE_WIDTH = 1024
MAX_IMAGE_HEIGHT = 1024
