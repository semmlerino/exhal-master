"""
Type-safe constants using Literal types for better type checking.

This module provides Literal type definitions for common constants
used throughout the SpritePal codebase, improving type safety and
enabling better IDE support.
"""
from __future__ import annotations

from typing import Literal

# Logging levels
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Compression types
CompressionType = Literal["hal", "lz77", "none"]

# Tile formats
TileFormat = Literal["4bpp", "8bpp", "2bpp", "1bpp"]

# Image formats
ImageFormat = Literal["PNG", "BMP", "TIFF", "JPEG"]

# Worker states
WorkerState = Literal["idle", "running", "paused", "cancelled", "finished", "error"]

# Cache types
CacheType = Literal["rom", "vram", "palette", "preview", "thumbnail"]

# Operation types
OperationType = Literal["extract", "inject", "scan", "preview", "validate"]

# Priority levels
Priority = Literal["low", "normal", "high", "critical"]

# Result status
ResultStatus = Literal["success", "failure", "partial", "cancelled"]
