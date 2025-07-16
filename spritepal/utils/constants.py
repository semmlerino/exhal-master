"""
Constants for SpritePal
"""

# SNES Memory offsets
VRAM_SPRITE_OFFSET = 0xC000  # Default sprite offset in VRAM
VRAM_SPRITE_SIZE = 0x4000    # Default sprite data size (16KB)

# Sprite format
BYTES_PER_TILE = 32          # 4bpp format
TILE_WIDTH = 8               # Pixels
TILE_HEIGHT = 8              # Pixels
DEFAULT_TILES_PER_ROW = 16   # Default layout

# Palette information
COLORS_PER_PALETTE = 16
SPRITE_PALETTE_START = 8     # Sprite palettes start at index 8
SPRITE_PALETTE_END = 16      # Up to palette 15
CGRAM_PALETTE_SIZE = 32      # Bytes per palette in CGRAM (16 colors * 2 bytes)

# File formats
PALETTE_EXTENSION = ".pal.json"
METADATA_EXTENSION = ".metadata.json"
SPRITE_EXTENSION = ".png"

# Palette names and descriptions
PALETTE_INFO = {
    8: ("Kirby (Pink)", "Main character palette"),
    9: ("Kirby Alt", "Alternative Kirby palette"),
    10: ("Helper", "Helper character palette"),
    11: ("Enemy 1", "Common enemy palette"),
    12: ("UI/HUD", "User interface elements"),
    13: ("Enemy 2", "Special enemy palette"),
    14: ("Boss/Enemy", "Boss and large enemy palette"),
    15: ("Effects", "Special effects palette")
}

# Common dump file patterns
VRAM_PATTERNS = [
    "*VRAM*.dmp",
    "*VideoRam*.dmp",
    "*vram*.dmp"
]

CGRAM_PATTERNS = [
    "*CGRAM*.dmp",
    "*CgRam*.dmp",
    "*cgram*.dmp"
]

OAM_PATTERNS = [
    "*OAM*.dmp",
    "*SpriteRam*.dmp",
    "*oam*.dmp"
]