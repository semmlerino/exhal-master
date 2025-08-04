"""
Smart Preview Coordinator for real-time preview updates during slider scrubbing.

This module provides smooth 60 FPS preview updates by implementing a multi-tier
strategy:
- Tier 1: Immediate visual feedback (0-16ms) for UI elements
- Tier 2: Fast preview updates (50ms debounce) during dragging
- Tier 3: High-quality preview (200ms debounce) after release

Key features:
- Worker thread reuse to prevent excessive thread creation
- LRU cache for instant preview display
- Different timing strategies for drag vs release states
- Proper Qt signal handling with sliderPressed/sliderReleased
"""

import weakref
from enum import Enum, auto
from typing import Optional, Callable, Any

from PyQt6.QtCore import QObject, QTimer, QMutex, QMutexLocker, pyqtSignal
from PyQt6.QtWidgets import QSlider

from ui.common.preview_worker_pool import PreviewWorkerPool
from ui.common.preview_cache import PreviewCache
from ui.common.timing_constants import REFRESH_RATE_60FPS, UI_UPDATE_INTERVAL
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
    Coordinates real-time preview updates with intelligent timing strategies.
    
    This coordinator implements a multi-tier approach:
    1. Immediate UI updates (labels, indicators) during dragging
    2. Cached preview display with 50ms debounce during drag
    3. High-quality preview generation with 200ms debounce after release
    
    Features:
    - Worker thread reuse via preview worker pool
    - LRU cache for instant preview display
    - Request cancellation to prevent stale updates
    - Adaptive timing based on drag state
    """
    
    # Signals for preview updates
    preview_ready = pyqtSignal(bytes, int, int, str)  # tile_data, width, height, name
    preview_cached = pyqtSignal(bytes, int, int, str)  # Cached preview displayed  
    preview_error = pyqtSignal(str)  # Error message
    
    def __init__(self, parent: Optional[QObject] = None):
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
        
        # Worker pool and cache
        self._worker_pool = PreviewWorkerPool(max_workers=2)
        self._worker_pool.preview_ready.connect(self._on_worker_preview_ready)
        self._worker_pool.preview_error.connect(self._on_worker_preview_error)
        
        self._cache = PreviewCache(max_size=20)  # ~2MB cache
        
        # Callbacks for external integration
        self._ui_update_callback: Optional[Callable[[int], None]] = None
        self._rom_data_provider: Optional[Callable[[], tuple[str, Any]]] = None
        
        logger.debug("SmartPreviewCoordinator initialized")
    
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
    
    def set_rom_data_provider(self, provider: Callable[[], tuple[str, Any]]) -> None:
        """Set provider for ROM data needed for preview generation."""
        self._rom_data_provider = provider
    
    def request_preview(self, offset: int, priority: int = 0) -> None:
        """
        Request preview update with intelligent timing.
        
        Args:
            offset: ROM offset for preview
            priority: Request priority (higher = more important)
        """
        with QMutexLocker(self._mutex):
            self._current_offset = offset
            self._request_counter += 1
        
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
        QTimer.singleShot(500, lambda: setattr(self, '_drag_state', DragState.IDLE))
    
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
    
    def _try_show_cached_preview(self) -> bool:
        """
        Try to show cached preview immediately.
        
        Returns:
            bool: True if cached preview was shown
        """
        if not self._rom_data_provider:
            return False
        
        try:
            rom_path, _ = self._rom_data_provider()
            with QMutexLocker(self._mutex):
                offset = self._current_offset
            
            cache_key = self._cache.make_key(rom_path, offset)
            cached_data = self._cache.get(cache_key)
            
            if cached_data:
                tile_data, width, height, sprite_name = cached_data
                self.preview_cached.emit(tile_data, width, height, sprite_name)
                logger.debug(f"Showed cached preview for 0x{offset:06X}")
                return True
                
        except Exception as e:
            logger.warning(f"Error showing cached preview: {e}")
        
        return False
    
    def _request_worker_preview(self, priority: int) -> None:
        """Request preview from worker pool."""
        if not self._rom_data_provider:
            logger.warning("No ROM data provider set")
            return
        
        try:
            rom_path, extractor = self._rom_data_provider()
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
            
            # Submit to worker pool
            self._worker_pool.submit_request(request, extractor)
            
        except Exception as e:
            logger.error(f"Error requesting worker preview: {e}")
            self.preview_error.emit(f"Preview request failed: {e}")
    
    def _on_worker_preview_ready(self, request_id: int, tile_data: bytes, 
                                width: int, height: int, sprite_name: str) -> None:
        """Handle preview ready from worker."""
        # Check if this is still the current request
        with QMutexLocker(self._mutex):
            if request_id < self._request_counter - 2:  # Allow some lag
                logger.debug(f"Ignoring stale preview {request_id} (current: {self._request_counter})")
                return
        
        # Cache the result
        if self._rom_data_provider:
            try:
                rom_path, _ = self._rom_data_provider()
                cache_key = self._cache.make_key(rom_path, self._current_offset)
                self._cache.put(cache_key, (tile_data, width, height, sprite_name))
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