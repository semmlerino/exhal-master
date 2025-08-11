"""
Batch thumbnail worker for generating sprite thumbnails asynchronously.
Handles queue management and priority-based generation.
"""

import builtins
import contextlib
from dataclasses import dataclass
from queue import PriorityQueue
from typing import Optional

from PIL import Image
from PySide6.QtCore import QMutex, QMutexLocker, Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap

from core.rom_extractor import ROMExtractor
from core.tile_renderer import TileRenderer
from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ThumbnailRequest:
    """Request for thumbnail generation."""
    offset: int
    size: int
    priority: int = 0

    def __lt__(self, other):
        """For priority queue sorting (lower priority value = higher priority)."""
        return self.priority < other.priority


class BatchThumbnailWorker(QThread):
    """Worker thread for batch thumbnail generation."""

    # Signals
    thumbnail_ready = Signal(int, QPixmap)  # offset, pixmap
    progress = Signal(int, int)  # current, total
    error = Signal(str)

    def __init__(
        self,
        rom_path: str,
        rom_extractor: Optional[ROMExtractor] = None,
        parent: Optional[QThread] = None
    ):
        """
        Initialize the batch thumbnail worker.

        Args:
            rom_path: Path to ROM file
            rom_extractor: ROM extractor instance
            parent: Parent thread
        """
        super().__init__(parent)

        self.rom_path = rom_path
        self.rom_extractor = rom_extractor or ROMExtractor()
        self.tile_renderer = TileRenderer()

        # Thread control
        self._stop_requested = False
        self._pause_requested = False
        self._mutex = QMutex()

        # Request queue
        self._request_queue: PriorityQueue = PriorityQueue()
        self._pending_count = 0
        self._completed_count = 0

        # Cache for recently generated thumbnails
        self._cache: dict[tuple[int, int], QPixmap] = {}
        self._cache_size_limit = 100

        # ROM data
        self._rom_data: Optional[bytes] = None

    def queue_thumbnail(
        self,
        offset: int,
        size: int = 128,
        priority: int = 0
    ):
        """
        Queue a thumbnail for generation.

        Args:
            offset: ROM offset of sprite
            size: Thumbnail size in pixels
            priority: Priority (0 = highest)
        """
        request = ThumbnailRequest(offset, size, priority)

        with QMutexLocker(self._mutex):
            self._request_queue.put(request)
            self._pending_count += 1

    def queue_batch(
        self,
        offsets: list[int],
        size: int = 128,
        priority_start: int = 0
    ):
        """
        Queue multiple thumbnails for generation.

        Args:
            offsets: List of ROM offsets
            size: Thumbnail size for all
            priority_start: Starting priority (increments for each)
        """
        for i, offset in enumerate(offsets):
            self.queue_thumbnail(offset, size, priority_start + i)

    def clear_queue(self):
        """Clear all pending requests."""
        with QMutexLocker(self._mutex):
            # Clear the queue
            while not self._request_queue.empty():
                try:
                    self._request_queue.get_nowait()
                except:
                    break
            self._pending_count = 0

    def stop(self):
        """Request the worker to stop."""
        self._stop_requested = True

    def pause(self):
        """Pause thumbnail generation."""
        self._pause_requested = True

    def resume(self):
        """Resume thumbnail generation."""
        self._pause_requested = False

    def run(self):
        """Main worker thread execution."""
        logger.info("BatchThumbnailWorker thread started")
        try:
            # Load ROM data once
            self._load_rom_data()
            logger.info(f"ROM data loaded: {len(self._rom_data) if self._rom_data else 0} bytes")

            processed_count = 0
            while not self._stop_requested:
                # Check for pause
                if self._pause_requested:
                    self.msleep(100)
                    continue

                # Get next request
                request = self._get_next_request()
                if not request:
                    if processed_count > 0:
                        logger.debug(f"No more requests, processed {processed_count} thumbnails")
                    self.msleep(50)  # No requests, wait a bit
                    continue

                logger.debug(f"Processing thumbnail request: offset=0x{request.offset:06X}, size={request.size}")

                # Check cache first
                cache_key = (request.offset, request.size)
                if cache_key in self._cache:
                    pixmap = self._cache[cache_key]
                    self.thumbnail_ready.emit(request.offset, pixmap)
                    self._completed_count += 1
                    self._emit_progress()
                    continue

                # Generate thumbnail
                pixmap = self._generate_thumbnail(request)

                if pixmap and not pixmap.isNull():
                    logger.debug(f"Generated valid thumbnail for 0x{request.offset:06X} (size: {pixmap.width()}x{pixmap.height()})")
                    # Cache it
                    self._add_to_cache(cache_key, pixmap)

                    # Emit result
                    self.thumbnail_ready.emit(request.offset, pixmap)
                    processed_count += 1
                else:
                    logger.warning(f"Failed to generate thumbnail for 0x{request.offset:06X} - pixmap is null or None")

                self._completed_count += 1
                self._emit_progress()

        except Exception as e:
            logger.error(f"Thumbnail worker error: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            logger.info("BatchThumbnailWorker thread stopped")

    def _load_rom_data(self):
        """Load ROM data into memory."""
        try:
            with open(self.rom_path, 'rb') as f:
                self._rom_data = f.read()
        except Exception as e:
            logger.error(f"Failed to load ROM: {e}")
            self.error.emit(f"Failed to load ROM: {e}")

    def _get_next_request(self) -> Optional[ThumbnailRequest]:
        """Get the next request from the queue."""
        with QMutexLocker(self._mutex):
            if not self._request_queue.empty():
                try:
                    return self._request_queue.get_nowait()
                except:
                    pass
        return None

    def _generate_thumbnail(self, request: ThumbnailRequest) -> Optional[QPixmap]:
        """
        Generate a thumbnail for a sprite.

        Args:
            request: Thumbnail request

        Returns:
            Generated pixmap or None
        """
        if not self._rom_data:
            return None

        try:
            # Try to decompress sprite at offset
            decompressed_data = None

            if self.rom_extractor and hasattr(self.rom_extractor, 'rom_injector'):
                # Try HAL decompression
                with contextlib.suppress(builtins.BaseException):
                    _, decompressed_data = self.rom_extractor.rom_injector.find_compressed_sprite(
                        self._rom_data,
                        request.offset,
                        expected_size=None
                    )
                    if decompressed_data:
                        logger.debug(f"HAL decompressed {len(decompressed_data)} bytes from 0x{request.offset:06X}")

            # If no decompressed data, use raw data
            if not decompressed_data:
                # Read raw tile data (up to 256 tiles)
                max_size = 32 * 256  # 32 bytes per tile, max 256 tiles
                end_offset = min(request.offset + max_size, len(self._rom_data))
                decompressed_data = self._rom_data[request.offset:end_offset]
                logger.debug(f"Using raw data: {len(decompressed_data)} bytes from 0x{request.offset:06X}")

            if not decompressed_data:
                return None

            # Render tiles to image
            tile_count = len(decompressed_data) // 32
            if tile_count == 0:
                logger.debug(f"No tiles to render for 0x{request.offset:06X}")
                return None

            # Calculate dimensions (try to make roughly square)
            width_tiles = min(16, tile_count)
            height_tiles = (tile_count + width_tiles - 1) // width_tiles
            logger.debug(f"Rendering {tile_count} tiles as {width_tiles}x{height_tiles} grid")

            # Render using tile renderer
            # Use palette_index=None for grayscale (will trigger grayscale fallback)
            image = self.tile_renderer.render_tiles(
                decompressed_data,
                width_tiles,
                height_tiles,
                palette_index=None  # Grayscale by default
            )

            if not image:
                logger.warning(f"TileRenderer returned None for 0x{request.offset:06X}")
                return None

            # Convert PIL Image to QPixmap
            pixmap = self._pil_to_qpixmap(image)

            # Scale to requested size
            if pixmap and not pixmap.isNull():
                pixmap = pixmap.scaled(
                    request.size,
                    request.size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

            return pixmap

        except Exception as e:
            logger.debug(f"Failed to generate thumbnail for offset {request.offset:06X}: {e}")
            return None

    def _pil_to_qpixmap(self, image: Image.Image) -> QPixmap:
        """
        Convert PIL Image to QPixmap.

        Args:
            image: PIL Image

        Returns:
            QPixmap
        """
        # Convert to RGBA if needed
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        # Get image data
        width, height = image.size
        bytes_data = image.tobytes("raw", "RGBA")

        # Create QImage
        qimage = QImage(
            bytes_data,
            width,
            height,
            QImage.Format.Format_RGBA8888
        )

        # Convert to QPixmap
        return QPixmap.fromImage(qimage)

    def _add_to_cache(self, key: tuple[int, int], pixmap: QPixmap):
        """Add a pixmap to the cache."""
        # Limit cache size
        if len(self._cache) >= self._cache_size_limit:
            # Remove oldest entry (simple FIFO for now)
            first_key = next(iter(self._cache))
            del self._cache[first_key]

        self._cache[key] = pixmap

    def _emit_progress(self):
        """Emit progress signal."""
        total = self._pending_count + self._completed_count
        if total > 0:
            self.progress.emit(self._completed_count, total)

    def get_cache_size(self) -> int:
        """Get the current cache size."""
        return len(self._cache)

    def clear_cache(self):
        """Clear the thumbnail cache."""
        self._cache.clear()
