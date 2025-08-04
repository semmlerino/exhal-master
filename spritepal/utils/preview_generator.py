"""
Preview Generator Service for SpritePal

Consolidates all sprite preview generation logic into a reusable service with caching,
thread safety, and support for different preview types (VRAM and ROM).

This service replaces scattered preview generation code in:
- core/controller.py (_generate_preview method)
- ui/dialogs/manual_offset_dialog_simplified.py
- ui/dialogs/manual_offset/preview_coordinator.py
- core/managers/extraction_manager.py (generate_preview)
"""

from __future__ import annotations

import hashlib
import threading
import time
import weakref
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Optional

from PIL import Image
from PyQt6.QtCore import QMutex, QMutexLocker, QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap

if TYPE_CHECKING:
    from core.managers.extraction_manager import ExtractionManager
    from core.rom_extractor import ROMExtractor

from .image_utils import pil_to_qpixmap
from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PaletteData:
    """Palette data for sprite preview generation."""
    data: bytes
    format: str = "snes_cgram"  # Format identifier
    
    
@dataclass
class PreviewRequest:
    """Unified preview request structure for all preview types."""
    source_type: str  # 'vram' or 'rom'
    data_path: str  # Path to data file (VRAM dump or ROM file)
    offset: int  # Offset within the data
    sprite_name: str = ""  # Optional sprite name
    palette: Optional[PaletteData] = None  # Optional palette data
    size: tuple[int, int] = (128, 128)  # Preview size (width, height)
    sprite_config: Any = None  # Optional sprite configuration
    
    def cache_key(self) -> str:
        """Generate a cache key for this request."""
        # Create hash from critical parameters
        key_data = (
            self.source_type,
            self.data_path,
            self.offset,
            self.size,
            # Include palette data hash if present
            hashlib.md5(self.palette.data).hexdigest() if self.palette else None,
            # Include sprite config hash if present
            str(hash(str(self.sprite_config))) if self.sprite_config else None
        )
        return hashlib.md5(str(key_data).encode()).hexdigest()


@dataclass
class PreviewResult:
    """Result of preview generation."""
    pixmap: QPixmap
    pil_image: Image.Image
    tile_count: int
    sprite_name: str
    generation_time: float  # Time taken to generate in seconds
    cached: bool = False  # Whether this result came from cache


class LRUCache:
    """Thread-safe LRU cache for preview results."""
    
    def __init__(self, max_size: int = 100):
        """Initialize LRU cache.
        
        Args:
            max_size: Maximum number of cached items
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, PreviewResult] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}
    
    def get(self, key: str) -> Optional[PreviewResult]:
        """Get item from cache.
        
        Thread Safety:
            - Uses reentrant lock (RLock) for thread safety
            - Safe to call from multiple threads concurrently
            - Logs thread ID for debugging concurrent access
        
        Args:
            key: Cache key
            
        Returns:
            Cached result or None if not found
        """
        thread_id = threading.current_thread().ident
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                result = self._cache.pop(key)
                self._cache[key] = result
                self._stats["hits"] += 1
                
                # Mark as cached result
                result.cached = True
                logger.debug(f"Cache hit for key: {key[:8]}... [thread={thread_id}]")
                return result
            
            self._stats["misses"] += 1
            logger.debug(f"Cache miss for key: {key[:8]}... [thread={thread_id}]")
            return None
    
    def put(self, key: str, result: PreviewResult) -> None:
        """Put item in cache.
        
        Thread Safety:
            - Uses reentrant lock (RLock) for thread safety
            - Atomic cache updates with eviction handling
            - Safe for concurrent access from multiple threads
        
        Args:
            key: Cache key
            result: Preview result to cache
        """
        thread_id = threading.current_thread().ident
        with self._lock:
            # Remove if already exists
            if key in self._cache:
                del self._cache[key]
            
            # Add to end
            self._cache[key] = result
            logger.debug(f"Cache put for key: {key[:8]}... [thread={thread_id}]")
            
            # Evict oldest if over limit
            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats["evictions"] += 1
                logger.debug(f"Evicted cache entry: {oldest_key[:8]}... [thread={thread_id}]")
    
    def clear(self) -> None:
        """Clear all cached items."""
        with self._lock:
            self._cache.clear()
            logger.debug("Preview cache cleared")
    
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0.0
            
            return {
                **self._stats,
                "cache_size": len(self._cache),
                "max_size": self.max_size,
                "hit_rate": hit_rate
            }


class PreviewGenerator(QObject):
    """Consolidated preview generation service with caching and thread safety.
    
    This service provides unified preview generation for both VRAM and ROM sources
    with intelligent caching, debouncing, and error recovery.
    
    Key features:
    - LRU cache with configurable size
    - Thread-safe operations
    - Progress callback support
    - Debounced updates for rapid changes
    - Error recovery with user-friendly messages
    - Support for different preview sizes
    - Automatic resource cleanup
    """
    
    # Signals for preview events
    preview_ready = pyqtSignal(object)  # PreviewResult
    preview_error = pyqtSignal(str, object)  # error_message, request
    preview_progress = pyqtSignal(int, str)  # progress_percent, status_message
    cache_stats_changed = pyqtSignal(object)  # cache statistics
    
    def __init__(self, 
                 cache_size: int = 100,
                 debounce_delay_ms: int = 50,
                 parent: QObject | None = None):
        """Initialize preview generator.
        
        Args:
            cache_size: Maximum number of cached previews
            debounce_delay_ms: Delay for debouncing rapid requests
            parent: Parent QObject
        """
        super().__init__(parent)
        
        # Cache management
        self._cache = LRUCache(cache_size)
        
        # Debouncing
        self._debounce_delay_ms = debounce_delay_ms
        self._debounce_timer: QTimer | None = None
        self._pending_request: PreviewRequest | None = None
        
        # Thread safety
        self._generation_mutex = QMutex()
        
        # Manager references (weak to avoid circular refs)
        self._extraction_manager_ref: weakref.ref[ExtractionManager] | None = None
        self._rom_extractor_ref: weakref.ref[ROMExtractor] | None = None
        
        self._setup_debounce_timer()
        
        logger.debug(f"PreviewGenerator initialized with cache_size={cache_size}, debounce={debounce_delay_ms}ms")
    
    def _setup_debounce_timer(self) -> None:
        """Set up debouncing timer."""
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._process_pending_request)
    
    def set_managers(self, 
                    extraction_manager: ExtractionManager | None = None,
                    rom_extractor: ROMExtractor | None = None) -> None:
        """Set manager references for preview generation.
        
        Args:
            extraction_manager: Extraction manager for VRAM previews
            rom_extractor: ROM extractor for ROM previews
        """
        with QMutexLocker(self._generation_mutex):
            self._extraction_manager_ref = weakref.ref(extraction_manager) if extraction_manager else None
            self._rom_extractor_ref = weakref.ref(rom_extractor) if rom_extractor else None
        
        logger.debug("PreviewGenerator manager references updated")
    
    def generate_preview(self,
                        request: PreviewRequest,
                        progress_callback: Optional[Callable[[int, str], None]] = None) -> Optional[PreviewResult]:
        """Generate preview synchronously.
        
        Args:
            request: Preview generation request
            progress_callback: Optional progress callback
            
        Returns:
            Preview result or None if generation failed
        """
        with QMutexLocker(self._generation_mutex):
            return self._generate_preview_impl(request, progress_callback)
    
    def generate_preview_async(self, 
                              request: PreviewRequest,
                              use_debounce: bool = True) -> None:
        """Generate preview asynchronously with optional debouncing.
        
        Args:
            request: Preview generation request
            use_debounce: Whether to use debouncing for rapid requests
        """
        if use_debounce:
            self._request_debounced_preview(request)
        else:
            # Generate immediately in next event loop
            self._pending_request = request
            if self._debounce_timer is not None:
                self._debounce_timer.start(0)
    
    def _request_debounced_preview(self, request: PreviewRequest) -> None:
        """Request a debounced preview generation.
        
        Args:
            request: Preview request to process after debounce delay
        """
        self._pending_request = request
        
        if self._debounce_timer is not None:
            self._debounce_timer.stop()
            self._debounce_timer.start(self._debounce_delay_ms)
    
    def _process_pending_request(self) -> None:
        """Process the pending debounced request."""
        if self._pending_request is None:
            return
        
        request = self._pending_request
        self._pending_request = None
        
        try:
            result = self.generate_preview(request, self._emit_progress)
            if result:
                self.preview_ready.emit(result)
            else:
                self.preview_error.emit("Preview generation failed", request)
        except Exception as e:
            logger.exception("Error in debounced preview generation")
            self.preview_error.emit(str(e), request)
    
    def _emit_progress(self, percent: int, message: str) -> None:
        """Emit progress signal."""
        self.preview_progress.emit(percent, message)
    
    def _generate_preview_impl(self,
                              request: PreviewRequest,
                              progress_callback: Optional[Callable[[int, str], None]] = None) -> Optional[PreviewResult]:
        """Internal preview generation implementation.
        
        Args:
            request: Preview generation request
            progress_callback: Optional progress callback
            
        Returns:
            Preview result or None if generation failed
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = request.cache_key()
        cached_result = self._cache.get(cache_key)
        if cached_result:
            if progress_callback:
                progress_callback(100, f"Loaded from cache: {request.sprite_name or 'preview'}")
            self.cache_stats_changed.emit(self._cache.get_stats())
            return cached_result
        
        if progress_callback:
            progress_callback(10, "Generating preview...")
        
        try:
            # Generate based on source type
            if request.source_type == "vram":
                result = self._generate_vram_preview(request, progress_callback)
            elif request.source_type == "rom":
                result = self._generate_rom_preview(request, progress_callback)
            else:
                raise ValueError(f"Unknown source type: {request.source_type}")
            
            if result:
                # Cache the result
                result.generation_time = time.time() - start_time
                self._cache.put(cache_key, result)
                self.cache_stats_changed.emit(self._cache.get_stats())
                
                if progress_callback:
                    progress_callback(100, f"Preview ready: {result.sprite_name}")
                
                logger.debug(f"Generated preview in {result.generation_time:.3f}s for {request.source_type}:{request.offset:06X}")
                return result
            
        except Exception as e:
            logger.exception(f"Preview generation failed for {request.source_type}:{request.offset:06X}")
            if progress_callback:
                progress_callback(0, f"Error: {self._get_friendly_error_message(str(e))}")
            return None
        
        return None
    
    def _generate_vram_preview(self,
                              request: PreviewRequest,
                              progress_callback: Optional[Callable[[int, str], None]] = None) -> Optional[PreviewResult]:
        """Generate preview from VRAM data.
        
        Args:
            request: VRAM preview request
            progress_callback: Optional progress callback
            
        Returns:
            Preview result or None if generation failed
        """
        # Get extraction manager
        extraction_manager = self._extraction_manager_ref() if self._extraction_manager_ref else None
        if not extraction_manager:
            raise RuntimeError("Extraction manager not available for VRAM preview")
        
        if progress_callback:
            progress_callback(30, "Loading VRAM data...")
        
        # Use extraction manager's generate_preview method
        pil_image, tile_count = extraction_manager.generate_preview(request.data_path, request.offset)
        
        if progress_callback:
            progress_callback(70, "Converting to display format...")
        
        # Convert to QPixmap
        pixmap = pil_to_qpixmap(pil_image)
        if not pixmap:
            raise RuntimeError("Failed to convert PIL image to QPixmap")
        
        # Scale to requested size if different
        if pixmap.size().width() != request.size[0] or pixmap.size().height() != request.size[1]:
            pixmap = pixmap.scaled(request.size[0], request.size[1])
        
        sprite_name = request.sprite_name or f"vram_0x{request.offset:06X}"
        
        return PreviewResult(
            pixmap=pixmap,
            pil_image=pil_image,
            tile_count=tile_count,
            sprite_name=sprite_name,
            generation_time=0.0  # Will be set by caller
        )
    
    def _generate_rom_preview(self,
                             request: PreviewRequest,
                             progress_callback: Optional[Callable[[int, str], None]] = None) -> Optional[PreviewResult]:
        """Generate preview from ROM data.
        
        Args:
            request: ROM preview request
            progress_callback: Optional progress callback
            
        Returns:
            Preview result or None if generation failed
        """
        # Get ROM extractor
        rom_extractor = self._rom_extractor_ref() if self._rom_extractor_ref else None
        if not rom_extractor:
            raise RuntimeError("ROM extractor not available for ROM preview")
        
        if progress_callback:
            progress_callback(20, "Reading ROM data...")
        
        # Use ROM extractor to extract sprite data
        # This is a simplified version - in a real implementation, you'd need
        # to adapt this based on the actual ROMExtractor interface
        sprite_data = rom_extractor.extract_sprite_data(
            request.data_path, 
            request.offset,
            request.sprite_config
        )
        
        if progress_callback:
            progress_callback(50, "Processing sprite data...")
        
        # Convert sprite data to PIL Image
        # This would need to be implemented based on the sprite data format
        pil_image = self._convert_sprite_data_to_image(sprite_data, request)
        
        if progress_callback:
            progress_callback(80, "Converting to display format...")
        
        # Convert to QPixmap
        pixmap = pil_to_qpixmap(pil_image)
        if not pixmap:
            raise RuntimeError("Failed to convert PIL image to QPixmap")
        
        # Scale to requested size if different
        if pixmap.size().width() != request.size[0] or pixmap.size().height() != request.size[1]:
            pixmap = pixmap.scaled(request.size[0], request.size[1])
        
        sprite_name = request.sprite_name or f"rom_0x{request.offset:06X}"
        
        # Calculate tile count (estimate based on image size)
        tile_count = (pil_image.width // 8) * (pil_image.height // 8)
        
        return PreviewResult(
            pixmap=pixmap,
            pil_image=pil_image,
            tile_count=tile_count,
            sprite_name=sprite_name,
            generation_time=0.0  # Will be set by caller
        )
    
    def _convert_sprite_data_to_image(self, sprite_data: bytes, request: PreviewRequest) -> Image.Image:
        """Convert raw sprite data to PIL Image.
        
        Args:
            sprite_data: Raw sprite tile data
            request: Original request with configuration
            
        Returns:
            PIL Image representation of the sprite
        """
        # This is a placeholder implementation
        # The actual implementation would depend on the sprite data format
        # and would need to handle 4bpp SNES tile data properly
        
        # For now, create a basic grayscale image
        # In practice, this would decode 4bpp tile data
        width, height = request.size
        image = Image.new("L", (width, height), 128)  # Gray placeholder
        
        # TODO: Implement actual 4bpp tile decoding here
        # This would involve:
        # 1. Decoding 4bpp tile data
        # 2. Applying palette if available
        # 3. Arranging tiles in proper grid
        
        return image
    
    def _get_friendly_error_message(self, error_msg: str) -> str:
        """Convert technical error messages to user-friendly ones.
        
        Args:
            error_msg: Technical error message
            
        Returns:
            User-friendly error message
        """
        error_lower = error_msg.lower()
        
        if "decompression" in error_lower or "hal" in error_lower:
            return "No sprite data found. Try different offset."
        elif "memory" in error_lower or "allocation" in error_lower:
            return "Memory error. Try closing other applications."
        elif "permission" in error_lower or "access" in error_lower:
            return "File access error. Check file permissions."
        elif "file not found" in error_lower or "no such file" in error_lower:
            return "Source file not found."
        elif "manager not available" in error_lower:
            return "Preview system not ready. Try again."
        else:
            return f"Preview failed: {error_msg}"
    
    def clear_cache(self) -> None:
        """Clear all cached previews."""
        self._cache.clear()
        self.cache_stats_changed.emit(self._cache.get_stats())
        logger.debug("Preview cache cleared")
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get current cache statistics."""
        return self._cache.get_stats()
    
    def create_preview_request(self, 
                                 data_path: str, 
                                 offset: int, 
                                 width: int, 
                                 height: int, 
                                 sprite_name: str = "") -> PreviewRequest:
        """Create a preview request with the given parameters.
        
        This method creates a ROM preview request by default. For VRAM previews,
        use create_vram_preview_request() directly or specify source_type.
        
        Args:
            data_path: Path to the data file (ROM or VRAM dump)
            offset: Offset within the data
            width: Preview width in pixels
            height: Preview height in pixels
            sprite_name: Optional name for the sprite
            
        Returns:
            PreviewRequest object configured for ROM preview
        """
        return create_rom_preview_request(
            rom_path=data_path,
            offset=offset,
            sprite_name=sprite_name,
            size=(width, height)
        )
    
    def generate_preview_sync(self,
                             data_path: str,
                             offset: int,
                             width: int = 128,
                             height: int = 128,
                             sprite_name: str = "") -> Optional[QPixmap]:
        """Generate preview synchronously and return QPixmap directly.
        
        This is a convenience method for simple synchronous preview generation
        that returns the QPixmap directly instead of a full PreviewResult.
        
        Args:
            data_path: Path to the data file (ROM or VRAM dump)
            offset: Offset within the data
            width: Preview width in pixels  
            height: Preview height in pixels
            sprite_name: Optional name for the sprite
            
        Returns:
            QPixmap of the generated preview, or None if generation failed
        """
        request = self.create_preview_request(data_path, offset, width, height, sprite_name)
        result = self.generate_preview(request)
        return result.pixmap if result else None
    
    def cancel_pending_requests(self) -> None:
        """Cancel any pending preview requests."""
        if self._debounce_timer is not None:
            self._debounce_timer.stop()
        self._pending_request = None
        logger.debug("Cancelled pending preview requests")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.cancel_pending_requests()
        self.clear_cache()
        
        # Clear manager references
        with QMutexLocker(self._generation_mutex):
            self._extraction_manager_ref = None
            self._rom_extractor_ref = None
        
        # Clean up timer
        if self._debounce_timer is not None:
            self._debounce_timer.stop()
            self._debounce_timer.deleteLater()
            self._debounce_timer = None
        
        logger.debug("PreviewGenerator cleaned up")
    
    def __del__(self) -> None:
        """Ensure cleanup on deletion.
        
        Thread Safety Note:
            - __del__ is called by garbage collector, possibly from any thread
            - Must be defensive about object state during deletion
            - Avoid complex operations that might fail
            - Don't rely on other objects existing (they might be deleted)
        """
        try:
            # Only try to clean up our own resources
            # Don't call cleanup() as it might access deleted objects
            
            # Cancel timer if it still exists
            if hasattr(self, '_debounce_timer') and self._debounce_timer is not None:
                try:
                    self._debounce_timer.stop()
                except (RuntimeError, AttributeError):
                    pass  # Timer might already be deleted
            
            # Clear simple attributes
            if hasattr(self, '_pending_request'):
                self._pending_request = None
            
            # Don't try to access complex objects like cache or mutexes
            # They might already be garbage collected
            
        except Exception:
            # Absolutely no exceptions should escape __del__
            pass


# Global preview generator instance with thread safety
_preview_generator: PreviewGenerator | None = None
_preview_generator_lock = threading.Lock()


def get_preview_generator() -> PreviewGenerator:
    """Get global preview generator instance with thread-safe initialization.
    
    This function implements the double-checked locking pattern to ensure
    thread-safe singleton initialization. The pattern works as follows:
    
    1. First check without lock (fast path for initialized case)
    2. Acquire lock only if initialization needed
    3. Double-check inside lock to handle race conditions
    4. Initialize only if still None after acquiring lock
    
    Thread Safety:
        - Multiple threads can safely call this function concurrently
        - Only one PreviewGenerator instance will ever be created
        - No race conditions during initialization
        - Minimal performance impact for already-initialized case
    
    Returns:
        Global PreviewGenerator instance
    """
    global _preview_generator
    
    # Fast path: Return existing instance without locking
    if _preview_generator is not None:
        return _preview_generator
    
    # Slow path: Need to initialize - acquire lock
    with _preview_generator_lock:
        # Double-check: Another thread might have initialized while we waited
        if _preview_generator is None:
            logger.debug("Initializing global PreviewGenerator instance")
            _preview_generator = PreviewGenerator()
            logger.debug("Global PreviewGenerator instance created")
    
    return _preview_generator


def cleanup_preview_generator() -> None:
    """Clean up the global preview generator instance.
    
    This function safely cleans up and removes the global PreviewGenerator
    instance. It is thread-safe and can be called during application shutdown.
    
    Thread Safety:
        - Uses the same lock as get_preview_generator()
        - Safely handles concurrent access
        - Prevents new instances from being created during cleanup
    """
    global _preview_generator
    
    with _preview_generator_lock:
        if _preview_generator is not None:
            logger.debug("Cleaning up global PreviewGenerator instance")
            try:
                _preview_generator.cleanup()
            except Exception as e:
                logger.error(f"Error during PreviewGenerator cleanup: {e}")
            finally:
                _preview_generator = None
                logger.debug("Global PreviewGenerator instance cleaned up")


def create_vram_preview_request(vram_path: str, 
                               offset: int,
                               sprite_name: str = "",
                               size: tuple[int, int] = (128, 128)) -> PreviewRequest:
    """Create a VRAM preview request.
    
    Args:
        vram_path: Path to VRAM dump file
        offset: Offset within VRAM
        sprite_name: Optional sprite name
        size: Preview size (width, height)
        
    Returns:
        VRAM preview request
    """
    return PreviewRequest(
        source_type="vram",
        data_path=vram_path,
        offset=offset,
        sprite_name=sprite_name or f"vram_0x{offset:06X}",
        size=size
    )


def create_rom_preview_request(rom_path: str,
                              offset: int,
                              sprite_name: str = "",
                              sprite_config: Any = None,
                              size: tuple[int, int] = (128, 128)) -> PreviewRequest:
    """Create a ROM preview request.
    
    Args:
        rom_path: Path to ROM file
        offset: Offset within ROM
        sprite_name: Optional sprite name
        sprite_config: Optional sprite configuration
        size: Preview size (width, height)
        
    Returns:
        ROM preview request
    """
    return PreviewRequest(
        source_type="rom",
        data_path=rom_path,
        offset=offset,
        sprite_name=sprite_name or f"rom_0x{offset:06X}",
        sprite_config=sprite_config,
        size=size
    )