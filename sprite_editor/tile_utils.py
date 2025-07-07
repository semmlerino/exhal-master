#!/usr/bin/env python3
"""
SNES tile encoding/decoding utilities
Consolidated from various sprite editor modules
"""

from typing import List
try:
    from .constants import (
        TILE_WIDTH, TILE_HEIGHT, BYTES_PER_TILE_4BPP,
        PIXELS_PER_TILE, TILE_BITPLANE_OFFSET
    )
except ImportError:
    from constants import (
        TILE_WIDTH, TILE_HEIGHT, BYTES_PER_TILE_4BPP,
        PIXELS_PER_TILE, TILE_BITPLANE_OFFSET
    )


def decode_4bpp_tile(data: bytes, offset: int) -> List[int]:
    """
    Decode a single 8x8 4bpp SNES tile.
    
    Args:
        data: Raw tile data bytes
        offset: Starting offset in the data
        
    Returns:
        List of 64 pixel values (0-15)
        
    Raises:
        IndexError: If offset + BYTES_PER_TILE_4BPP exceeds data length
    """
    if offset + BYTES_PER_TILE_4BPP > len(data):
        raise IndexError(f"Tile data out of bounds at offset {offset}")
        
    tile = []
    for y in range(TILE_HEIGHT):
        row = []
        # Read bitplanes for this row
        bp0 = data[offset + y * 2]
        bp1 = data[offset + y * 2 + 1]
        bp2 = data[offset + TILE_BITPLANE_OFFSET + y * 2]
        bp3 = data[offset + TILE_BITPLANE_OFFSET + y * 2 + 1]

        # Decode each pixel in the row
        for x in range(TILE_WIDTH):
            bit = 7 - x
            pixel = ((bp0 >> bit) & 1) | \
                   (((bp1 >> bit) & 1) << 1) | \
                   (((bp2 >> bit) & 1) << 2) | \
                   (((bp3 >> bit) & 1) << 3)
            row.append(pixel)
        tile.extend(row)
    
    return tile


def encode_4bpp_tile(tile_pixels: List[int]) -> bytes:
    """
    Encode an 8x8 tile to SNES 4bpp format.
    
    Args:
        tile_pixels: List of 64 pixel values (0-15)
        
    Returns:
        32 bytes of encoded tile data
        
    Raises:
        ValueError: If tile_pixels doesn't contain exactly 64 values
    """
    if len(tile_pixels) != PIXELS_PER_TILE:
        raise ValueError(f"Expected {PIXELS_PER_TILE} pixels, got {len(tile_pixels)}")
    
    output = bytearray(BYTES_PER_TILE_4BPP)

    for y in range(TILE_HEIGHT):
        bp0 = 0
        bp1 = 0
        bp2 = 0
        bp3 = 0

        # Encode each pixel in the row
        for x in range(TILE_WIDTH):
            pixel = tile_pixels[y * TILE_WIDTH + x] & 0x0F  # Ensure 4-bit value
            bp0 |= ((pixel & 1) >> 0) << (7 - x)
            bp1 |= ((pixel & 2) >> 1) << (7 - x)
            bp2 |= ((pixel & 4) >> 2) << (7 - x)
            bp3 |= ((pixel & 8) >> 3) << (7 - x)

        # Store bitplanes in SNES format
        output[y * 2] = bp0
        output[y * 2 + 1] = bp1
        output[TILE_BITPLANE_OFFSET + y * 2] = bp2
        output[TILE_BITPLANE_OFFSET + y * 2 + 1] = bp3

    return bytes(output)


def decode_tiles(data: bytes, num_tiles: int, start_offset: int = 0) -> List[List[int]]:
    """
    Decode multiple 4bpp tiles from data.
    
    Args:
        data: Raw tile data bytes
        num_tiles: Number of tiles to decode
        start_offset: Starting offset in the data
        
    Returns:
        List of decoded tiles (each tile is a list of 64 pixels)
    """
    tiles = []
    for i in range(num_tiles):
        offset = start_offset + (i * BYTES_PER_TILE_4BPP)
        if offset + BYTES_PER_TILE_4BPP <= len(data):
            tile = decode_4bpp_tile(data, offset)
            tiles.append(tile)
        else:
            break
    
    return tiles


def encode_tiles(tiles: List[List[int]]) -> bytes:
    """
    Encode multiple tiles to SNES 4bpp format.
    
    Args:
        tiles: List of tiles (each tile is a list of 64 pixels)
        
    Returns:
        Encoded tile data
    """
    output = bytearray()
    for tile in tiles:
        encoded = encode_4bpp_tile(tile)
        output.extend(encoded)
    
    return bytes(output)