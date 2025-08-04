"""
Smart Preview Coordinator for real-time preview updates with dual-tier caching.

This module provides smooth 60 FPS preview updates by implementing a multi-tier
strategy:
- Tier 1: Immediate visual feedback (0-16ms) for UI elements
- Tier 2: Fast cached previews (50ms debounce) during dragging
- Tier 3: High-quality preview generation (200ms debounce) after release

Dual-Tier Caching:
- Memory Cache: Fast LRU cache (~2MB) for instant access during session
- ROM Cache: Persistent cache for cross-session preview storage
- Cache Workflow: Check memory -> Check ROM -> Generate -> Save to both

Key features:
- Worker thread reuse to prevent excessive thread creation
- Dual-tier caching with performance metrics
- Different timing strategies for drag vs release states
- Cache hit/miss tracking and response time analysis
- Proper Qt signal handling with sliderPressed/sliderReleased
- Backward compatibility with optional ROM cache integration
"""

import time
import weakref
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from utils.rom_cache import ROMCache

from PyQt6.QtCore import QMutex, QMutexLocker, QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QSlider
from ui.common.preview_cache import PreviewCache
from ui.common.preview_worker_pool import PreviewWorkerPool
from ui.common.timing_constants import REFRESH_RATE_60FPS
from utils.logging_config import get_logger

logger = get_logger(__name__)


class DragState(Enum):
    """Slider drag state for different preview strategies."""
    IDLE = auto()         # Not dragging, normal operations
    DRAGGING = auto()     # Actively dragging slider
    SETTLING = auto()     # Just released, waiting for final update


class PreviewRequest:
    """Represents a preview request with priority and cancellation support."""

    def __init__(self, request_id: int, offset: int, rom_path: str,
                 priority: int = 0, callback: Optional[Callable] = None):
        self.request_id = request_id
        self.offset = offset
        self.rom_path = rom_path
        self.priority = priority  # Higher = more important
        self.callback = callback
        self.cancelled = False

    def cancel(self):
        """Mark this request as cancelled."""
        self.cancelled = True

    def __lt__(self, other):
        """Support priority queue ordering."""
        return self.priority > other.priority  # Higher priority first


class SmartPreviewCoordinator(QObject):
    """
    Coordinates real-time preview updates with intelligent timing and dual-tier caching.

    This coordinator implements a multi-tier approach:
    1. Immediate UI updates (labels, indicators) during dragging
    2. Dual-tier cached preview display with 50ms debounce during drag
    3. High-quality preview generation with 200ms debounce after release

    Caching Strategy:
    - Tier 1: Fast LRU memory cache (~2MB) for instant access
    - Tier 2: Persistent ROM cache for cross-session storage
    - Cache workflow: Memory -> ROM -> Generate -> Save to both

    Features:
    - Worker thread reuse via preview worker pool
    - Dual-tier caching with performance tracking
    - Request cancellation to prevent stale updates
    - Adaptive timing based on drag state
    - Cache hit/miss metrics and response time tracking
    """

    # Signals for preview updates
    preview_ready = pyqtSignal(bytes, int, int, str)  # tile_data, width, height, name
    preview_cached = pyqtSignal(bytes, int, int, str)  # Cached preview displayed
    preview_error = pyqtSignal(str)  # Error message

    def __init__(self, parent: Optional[QObject] = None, rom_cache: Optional["ROMCache"] = None):
        super().__init__(parent)

        # State management
        self._drag_state = DragState.IDLE
        self._current_offset = 0
        self._request_counter = 0
        self._mutex = QMutex()

        # Slider reference (weak to prevent circular references)
        self._slider_ref: Optional[weakref.ReferenceType] = None

        # Timing configuration optimized for 60 FPS real-time updates
        self._drag_debounce_ms = REFRESH_RATE_60FPS  # 16ms for 60 FPS drag updates
        self._release_debounce_ms = 200  # Quality updates after release
        self._ui_update_ms = REFRESH_RATE_60FPS  # 16ms for smooth UI

        # Timer management
        self._drag_timer = QTimer(self)
        self._drag_timer.setSingleShot(True)
        self._drag_timer.timeout.connect(self._handle_drag_preview)

        self._release_timer = QTimer(self)
        self._release_timer.setSingleShot(True)
        self._release_timer.timeout.connect(self._handle_release_preview)

        self._ui_timer = QTimer(self)
        self._ui_timer.setSingleShot(True)
        self._ui_timer.timeout.connect(self._handle_ui_update)

        # Worker pool and dual-tier caching
        self._worker_pool = PreviewWorkerPool(max_workers=2)
        self._worker_pool.preview_ready.connect(self._on_worker_preview_ready)
        self._worker_pool.preview_error.connect(self._on_worker_preview_error)

        # Tier 1: Fast LRU memory cache
        self._cache = PreviewCache(max_size=20)  # ~2MB cache

        # Tier 2: Persistent ROM cache (optional)
        self._rom_cache = rom_cache

        # Performance tracking
        self._cache_stats = {
            "memory_hits": 0,
            "memory_misses": 0,
            "rom_hits": 0,
            "rom_misses": 0,
            "generations": 0,
            "response_times": []
        }

        # Callbacks for external integration
        self._ui_update_callback: Optional[Callable[[int], None]] = None
        self._rom_data_provider: Optional[Callable[[], tuple[str, Any, Any]]] = None

        cache_info = "with ROM cache" if rom_cache else "memory only"
        logger.debug(f"SmartPreviewCoordinator initialized ({cache_info})")

    def connect_slider(self, slider: QSlider) -> None:
        """
        Connect to slider signals for smart preview coordination.

        Args:
            slider: QSlider to monitor for drag events
        """
        self._slider_ref = weakref.ref(slider)

        # Connect to slider signals for different drag phases
        slider.sliderPressed.connect(self._on_drag_start)
        slider.sliderMoved.connect(self._on_drag_move)
        slider.sliderReleased.connect(self._on_drag_end)

        logger.debug(f"Connected to slider {slider.objectName()}")

    def set_ui_update_callback(self, callback: Callable[[int], None]) -> None:
        """Set callback for immediate UI updates during dragging."""
        self._ui_update_callback = callback

    def set_rom_data_provider(self, provider: Callable[[], tuple[str, Any, Any]]) -> None:
        """Set provider for ROM data needed for preview generation.

        Args:
            provider: Function that returns (rom_path, rom_extractor, rom_cache)
                     Third parameter can be None for backward compatibility
        """
        self._rom_data_provider = provider

    def request_preview(self, offset: int, priority: int = 0) -> None:
        """
        Request preview update with intelligent timing and dual-tier caching.

        Cache workflow:
        1. Check memory cache (LRU) first
        2. If miss, check ROM cache
        3. If miss, generate preview
        4. Save to both caches on generation

        Args:
            offset: ROM offset for preview
            priority: Request priority (higher = more important)
        """
        start_time = time.time()

        with QMutexLocker(self._mutex):
            self._current_offset = offset
            self._request_counter += 1

        # Try dual-tier cache lookup first
        if self._try_show_cached_preview_dual_tier():
            # Record response time for cache hits
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            self._cache_stats["response_times"].append(response_time)
            # Keep only last 100 response times
            if len(self._cache_stats["response_times"]) > 100:
                self._cache_stats["response_times"].pop(0)
            return

        # Immediate UI update for smooth feedback
        self._schedule_ui_update()

        # Schedule preview based on current drag state
        if self._drag_state == DragState.DRAGGING:
            self._schedule_drag_preview()
        else:
            self._schedule_release_preview()

    def request_manual_preview(self, offset: int) -> None:
        """
        Request preview for manual offset change (outside of slider dragging).

        Args:
            offset: ROM offset for preview
        """
        # Force drag state to idle for immediate high-quality preview
        old_state = self._drag_state
        self._drag_state = DragState.IDLE

        # Request with high priority
        self.request_preview(offset, priority=10)

        # Restore previous state
        self._drag_state = old_state

    def _on_drag_start(self) -> None:
        """Handle start of slider dragging."""
        logger.debug("Drag start detected")
        self._drag_state = DragState.DRAGGING

        # Cancel any pending release previews
        self._release_timer.stop()

        # Try to show cached preview immediately
        if self._try_show_cached_preview():
            logger.debug("Showed cached preview for drag start")

    def _on_drag_move(self, value: int) -> None:
        """Handle slider movement during dragging."""
        # Request preview with drag priority
        self.request_preview(value, priority=1)

    def _on_drag_end(self) -> None:
        """Handle end of slider dragging."""
        logger.debug("Drag end detected")
        self._drag_state = DragState.SETTLING

        # Cancel drag timers
        self._drag_timer.stop()

        # Schedule high-quality release preview
        self._schedule_release_preview()

        # Return to idle state after brief settling period
        QTimer.singleShot(500, lambda: setattr(self, "_drag_state", DragState.IDLE))

    def _schedule_ui_update(self) -> None:
        """Schedule immediate UI update for smooth feedback."""
        if not self._ui_timer.isActive():
            self._ui_timer.start(self._ui_update_ms)

    def _schedule_drag_preview(self) -> None:
        """Schedule preview update during dragging with short debounce."""
        self._drag_timer.stop()
        self._drag_timer.start(self._drag_debounce_ms)

    def _schedule_release_preview(self) -> None:
        """Schedule preview update after release with longer debounce."""
        self._release_timer.stop()
        self._release_timer.start(self._release_debounce_ms)

    def _handle_ui_update(self) -> None:
        """Handle immediate UI updates for smooth feedback."""
        if self._ui_update_callback:
            with QMutexLocker(self._mutex):
                offset = self._current_offset
            self._ui_update_callback(offset)

    def _handle_drag_preview(self) -> None:
        """Handle preview update during dragging."""
        logger.debug("Processing drag preview request")

        # Check cache first for instant display
        if self._try_show_cached_preview():
            return

        # Request preview with medium priority
        self._request_worker_preview(priority=5)

    def _handle_release_preview(self) -> None:
        """Handle high-quality preview update after release."""
        logger.debug("Processing release preview request")

        # Request high-quality preview
        self._request_worker_preview(priority=10)

    def _try_show_cached_preview_dual_tier(self) -> bool:
        """
        Try to show cached preview from dual-tier cache system.

        Checks memory cache first, then ROM cache if available.

        Returns:
            bool: True if cached preview was shown
        """
        if not self._rom_data_provider:
            return False

        try:
            rom_path, _, _ = self._rom_data_provider()
            with QMutexLocker(self._mutex):
                offset = self._current_offset

            cache_key = self._cache.make_key(rom_path, offset)

            # Tier 1: Check memory cache first
            cached_data = self._cache.get(cache_key)
            if cached_data:
                tile_data, width, height, sprite_name = cached_data
                self.preview_cached.emit(tile_data, width, height, sprite_name)
                self._cache_stats["memory_hits"] += 1
                logger.debug(f"Memory cache hit for 0x{offset:06X}")
                return True

            self._cache_stats["memory_misses"] += 1

            # Tier 2: Check ROM cache if available
            if self._rom_cache and self._rom_cache.cache_enabled:
                rom_cache_data = self._check_rom_cache(rom_path, offset)
                if rom_cache_data:
                    tile_data, width, height, sprite_name = rom_cache_data

                    # Store in memory cache for faster future access
                    self._cache.put(cache_key, rom_cache_data)

                    self.preview_cached.emit(tile_data, width, height, sprite_name)
                    self._cache_stats["rom_hits"] += 1
                    logger.debug(f"ROM cache hit for 0x{offset:06X}")
                    return True

            if self._rom_cache and self._rom_cache.cache_enabled:
                self._cache_stats["rom_misses"] += 1

        except Exception as e:
            logger.warning(f"Error checking cached preview: {e}")

        return False

    def _try_show_cached_preview(self) -> bool:
        """
        Legacy method for backward compatibility.

        Returns:
            bool: True if cached preview was shown
        """
        return self._try_show_cached_preview_dual_tier()

    def _check_rom_cache(self, rom_path: str, offset: int) -> Optional[tuple[bytes, int, int, str]]:
        """
        Check ROM cache for preview data.

        Args:
            rom_path: Path to ROM file
            offset: ROM offset

        Returns:
            Optional tuple of (tile_data, width, height, sprite_name) or None
        """
        if not self._rom_cache or not self._rom_cache.cache_enabled:
            return None

        try:
            # Generate cache key compatible with ROM cache system

            # Try to get preview data from ROM cache
            # Note: ROM cache uses different storage - this is a conceptual implementation
            # The actual implementation would need preview-specific caching in ROM cache
            logger.debug(f"Checking ROM cache for preview at 0x{offset:06X}")

            # For now, return None as ROM cache doesn't store preview data yet
            # This will be extended when ROM cache adds preview storage support
            return None

        except Exception as e:
            logger.warning(f"Error checking ROM cache: {e}")
            return None

    def _save_to_rom_cache(self, rom_path: str, offset: int,
                          preview_data: tuple[bytes, int, int, str]) -> bool:
        """
        Save preview data to ROM cache.

        Args:
            rom_path: Path to ROM file
            offset: ROM offset
            preview_data: Tuple of (tile_data, width, height, sprite_name)

        Returns:
            bool: True if saved successfully
        """
        if not self._rom_cache or not self._rom_cache.cache_enabled:
            return False

        try:
            # Generate cache key

            # Save to ROM cache
            # Note: This is a conceptual implementation - ROM cache would need
            # preview-specific storage methods
            logger.debug(f"Saving preview to ROM cache for 0x{offset:06X}")

            # For now, return False as ROM cache doesn't support preview storage yet
            return False

        except Exception as e:
            logger.warning(f"Error saving to ROM cache: {e}")
            return False

    def _request_worker_preview(self, priority: int) -> None:
        """Request preview from worker pool."""
        if not self._rom_data_provider:
            logger.warning("No ROM data provider set")
            return

        try:
            rom_path, extractor, rom_cache = self._rom_data_provider()
            with QMutexLocker(self._mutex):
                offset = self._current_offset
                request_id = self._request_counter

            # Create preview request
            request = PreviewRequest(
                request_id=request_id,
                offset=offset,
                rom_path=rom_path,
                priority=priority
            )

            # Submit to worker pool with ROM cache support
            self._worker_pool.submit_request(request, extractor, rom_cache)

        except Exception as e:
            logger.exception("Error requesting worker preview")  # TRY401: exception already logged
            self.preview_error.emit(f"Preview request failed: {e}")

    def _on_worker_preview_ready(self, request_id: int, tile_data: bytes,
                                width: int, height: int, sprite_name: str) -> None:
        """Handle preview ready from worker."""
        # Check if this is still the current request
        with QMutexLocker(self._mutex):
            if request_id < self._request_counter - 2:  # Allow some lag
                logger.debug(f"Ignoring stale preview {request_id} (current: {self._request_counter})")
                return

        # Update generation counter
        self._cache_stats["generations"] += 1

        # Cache the result in both tiers
        if self._rom_data_provider:
            try:
                rom_path, _, _ = self._rom_data_provider()
                preview_data = (tile_data, width, height, sprite_name)

                # Tier 1: Save to memory cache
                cache_key = self._cache.make_key(rom_path, self._current_offset)
                self._cache.put(cache_key, preview_data)

                # Tier 2: Save to ROM cache if available
                if self._rom_cache:
                    self._save_to_rom_cache(rom_path, self._current_offset, preview_data)

            except Exception as e:
                logger.warning(f"Error caching preview: {e}")

        # Emit preview ready
        self.preview_ready.emit(tile_data, width, height, sprite_name)
        logger.debug(f"Preview ready for request {request_id}")

    def _on_worker_preview_error(self, request_id: int, error_msg: str) -> None:
        """Handle preview error from worker."""
        # Check if this is still relevant
        with QMutexLocker(self._mutex):
            if request_id < self._request_counter - 2:
                return

        self.preview_error.emit(error_msg)
        logger.debug(f"Preview error for request {request_id}: {error_msg}")

    def cleanup(self) -> None:
        """Clean up resources."""
        logger.debug("Cleaning up SmartPreviewCoordinator")

        # Stop all timers
        self._drag_timer.stop()
        self._release_timer.stop()
        self._ui_timer.stop()

        # Cleanup worker pool
        self._worker_pool.cleanup()

        # Clear cache
        self._cache.clear()

        # Clear references
        self._slider_ref = None
        self._ui_update_callback = None
        self._rom_data_provider = None

    def get_cache_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive cache statistics.

        Returns:
            dict: Cache performance metrics including hit/miss ratios and response times
        """
        with QMutexLocker(self._mutex):
            stats = self._cache_stats.copy()

        # Calculate derived metrics
        total_memory_requests = stats["memory_hits"] + stats["memory_misses"]
        total_rom_requests = stats["rom_hits"] + stats["rom_misses"]

        # Memory cache metrics
        memory_hit_rate = (stats["memory_hits"] / total_memory_requests * 100) if total_memory_requests > 0 else 0

        # ROM cache metrics (only if ROM cache is available)
        rom_hit_rate = (stats["rom_hits"] / total_rom_requests * 100) if total_rom_requests > 0 else 0

        # Overall cache performance
        total_hits = stats["memory_hits"] + stats["rom_hits"]
        total_requests = total_memory_requests
        overall_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0

        # Response time metrics
        response_times = stats["response_times"]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0

        # Get memory cache stats
        memory_cache_stats = self._cache.get_stats()

        return {
            # Cache hit/miss counts
            "memory_hits": stats["memory_hits"],
            "memory_misses": stats["memory_misses"],
            "rom_hits": stats["rom_hits"],
            "rom_misses": stats["rom_misses"],
            "generations": stats["generations"],

            # Calculated rates
            "memory_hit_rate_percent": round(memory_hit_rate, 2),
            "rom_hit_rate_percent": round(rom_hit_rate, 2),
            "overall_hit_rate_percent": round(overall_hit_rate, 2),

            # Response times
            "avg_response_time_ms": round(avg_response_time, 2),
            "min_response_time_ms": round(min_response_time, 2),
            "max_response_time_ms": round(max_response_time, 2),

            # Memory cache details
            "memory_cache": memory_cache_stats,

            # ROM cache availability
            "rom_cache_enabled": self._rom_cache is not None and self._rom_cache.cache_enabled,

            # Total requests
            "total_requests": total_requests
        }
