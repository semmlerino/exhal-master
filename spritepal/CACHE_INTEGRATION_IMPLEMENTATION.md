# ROM Cache Integration - Implementation Examples

## Implementation Roadmap

This document provides concrete implementation examples for integrating ROM caching with the manual offset dialog, following the architecture outlined in `ROM_CACHE_INTEGRATION_ARCHITECTURE.md`.

## Phase 1: ROM Cache Extensions

### 1.1 Core Data Structures

```python
# File: utils/cache_data_structures.py
"""Data structures for ROM cache preview integration."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import hashlib
import json

@dataclass
class PreviewData:
    """Structured preview data for efficient caching."""
    offset: int
    tile_data: bytes
    width: int
    height: int
    sprite_name: str
    generated_at: datetime
    generation_time_ms: float
    rom_hash: str
    compression_info: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "offset": self.offset,
            "width": self.width,
            "height": self.height,
            "sprite_name": self.sprite_name,
            "generated_at": self.generated_at.isoformat(),
            "generation_time_ms": self.generation_time_ms,
            "rom_hash": self.rom_hash,
            "compression_info": self.compression_info,
            "metadata": self.metadata,
            # tile_data handled separately due to size
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], tile_data: bytes) -> 'PreviewData':
        """Create from dictionary and tile data."""
        return cls(
            offset=data["offset"],
            tile_data=tile_data,
            width=data["width"],
            height=data["height"],
            sprite_name=data["sprite_name"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            generation_time_ms=data["generation_time_ms"],
            rom_hash=data["rom_hash"],
            compression_info=data.get("compression_info"),
            metadata=data.get("metadata")
        )

@dataclass
class SuggestedOffset:
    """Intelligent offset suggestion with confidence scoring."""
    offset: int
    confidence: float  # 0.0 to 1.0
    reason: str       # "scan_result", "pattern_match", "user_history"
    sprite_name: Optional[str] = None
    preview_available: bool = False
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "offset": self.offset,
            "confidence": self.confidence,
            "reason": self.reason,
            "sprite_name": self.sprite_name,
            "preview_available": self.preview_available,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SuggestedOffset':
        """Create from dictionary."""
        return cls(
            offset=data["offset"],
            confidence=data["confidence"],
            reason=data["reason"],
            sprite_name=data.get("sprite_name"),
            preview_available=data.get("preview_available", False),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) 
                         if data.get("last_accessed") else None,
            metadata=data.get("metadata", {})
        )

@dataclass
class BatchPreviewData:
    """Batch preview data for range operations."""
    start_offset: int
    end_offset: int
    step_size: int
    previews: Dict[int, PreviewData] = field(default_factory=dict)
    cache_strategy: str = "adaptive"
    total_size_bytes: int = 0
    cached_at: datetime = field(default_factory=datetime.now)
    
    def add_preview(self, preview: PreviewData) -> None:
        """Add a preview to the batch."""
        self.previews[preview.offset] = preview
        self.total_size_bytes += len(preview.tile_data)
```

### 1.2 ROM Cache Extensions Implementation

```python
# File: utils/rom_cache_extensions.py
"""Extensions to ROM cache for preview data management."""

import base64
import json
import os
import threading
import time
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Any

from utils.cache_data_structures import PreviewData, SuggestedOffset, BatchPreviewData
from utils.rom_cache import ROMCache
from utils.logging_config import get_logger

logger = get_logger(__name__)

class ROMCachePreviewExtensions:
    """Preview-specific extensions for ROM cache."""
    
    PREVIEW_CACHE_VERSION = "2.0"
    COMPRESSION_LEVEL = 6  # Balance between compression and speed
    
    def __init__(self, rom_cache: ROMCache):
        self._rom_cache = rom_cache
        self._preview_lock = threading.RLock()
        self._batch_lock = threading.RLock()
        self._suggestion_lock = threading.RLock()
    
    def save_preview_data(self, rom_path: str, offset: int, 
                         preview_data: PreviewData) -> bool:
        """
        Save individual preview data to persistent cache.
        
        Thread-safe implementation with compression and atomic writes.
        """
        if not self._rom_cache.cache_enabled:
            return False
            
        with self._preview_lock:
            try:
                rom_hash = self._rom_cache._get_rom_hash(rom_path)
                cache_key = f"preview_{offset:08X}"
                cache_file = self._rom_cache._get_cache_file_path(rom_hash, cache_key)
                
                # Prepare cache data with compression
                cache_data = {
                    "version": self.PREVIEW_CACHE_VERSION,
                    "rom_path": os.path.abspath(rom_path),
                    "rom_hash": rom_hash,
                    "cached_at": time.time(),
                    "preview": {
                        **preview_data.to_dict(),
                        "tile_data": self._compress_tile_data(preview_data.tile_data),
                        "compressed": True
                    }
                }
                
                # Atomic write with error handling
                success = self._rom_cache._save_cache_data(cache_file, cache_data)
                
                if success:
                    logger.debug(f"Cached preview for offset 0x{offset:X} "
                               f"({len(preview_data.tile_data)} bytes -> "
                               f"{len(cache_data['preview']['tile_data'])} compressed)")
                
                return success
                
            except Exception as e:
                logger.warning(f"Failed to save preview data for offset 0x{offset:X}: {e}")
                return False
    
    def get_preview_data(self, rom_path: str, offset: int) -> Optional[PreviewData]:
        """
        Retrieve preview data from persistent cache.
        
        Thread-safe with decompression and validation.
        """
        if not self._rom_cache.cache_enabled:
            return None
            
        with self._preview_lock:
            try:
                rom_hash = self._rom_cache._get_rom_hash(rom_path)
                cache_key = f"preview_{offset:08X}"
                cache_file = self._rom_cache._get_cache_file_path(rom_hash, cache_key)
                
                # Check cache validity
                if not self._rom_cache._is_cache_valid(cache_file, rom_path):
                    return None
                
                # Load and validate cache data
                cache_data = self._rom_cache._load_cache_data(cache_file)
                if not cache_data or "preview" not in cache_data:
                    return None
                
                if cache_data.get("version") != self.PREVIEW_CACHE_VERSION:
                    return None
                
                preview_dict = cache_data["preview"]
                
                # Decompress tile data
                if preview_dict.get("compressed", False):
                    tile_data = self._decompress_tile_data(preview_dict["tile_data"])
                else:
                    # Legacy format compatibility
                    tile_data = base64.b64decode(preview_dict["tile_data"])
                
                # Create PreviewData object
                preview_data = PreviewData.from_dict(preview_dict, tile_data)
                
                logger.debug(f"Loaded cached preview for offset 0x{offset:X}")
                return preview_data
                
            except Exception as e:
                logger.warning(f"Failed to load preview data for offset 0x{offset:X}: {e}")
                return None
    
    def save_offset_suggestions(self, rom_path: str, 
                               suggestions: List[SuggestedOffset]) -> bool:
        """Save intelligent offset suggestions based on analysis."""
        if not self._rom_cache.cache_enabled:
            return False
            
        with self._suggestion_lock:
            try:
                rom_hash = self._rom_cache._get_rom_hash(rom_path)
                cache_file = self._rom_cache._get_cache_file_path(rom_hash, "offset_suggestions")
                
                # Sort suggestions by confidence
                sorted_suggestions = sorted(suggestions, 
                                          key=lambda s: s.confidence, reverse=True)
                
                # Serialize suggestions
                suggestions_data = [s.to_dict() for s in sorted_suggestions]
                
                cache_data = {
                    "version": self.PREVIEW_CACHE_VERSION,
                    "rom_path": os.path.abspath(rom_path),
                    "rom_hash": rom_hash,
                    "cached_at": time.time(),
                    "suggestions": suggestions_data,
                    "total_suggestions": len(suggestions_data),
                    "generation_context": {
                        "scan_results_available": self._has_scan_results(rom_path),
                        "history_available": self._has_access_history(rom_path),
                        "pattern_analysis_done": True
                    }
                }
                
                success = self._rom_cache._save_cache_data(cache_file, cache_data)
                
                if success:
                    logger.info(f"Cached {len(suggestions)} offset suggestions")
                
                return success
                
            except Exception as e:
                logger.warning(f"Failed to save offset suggestions: {e}")
                return False
    
    def get_offset_suggestions(self, rom_path: str, 
                              limit: int = 50,
                              min_confidence: float = 0.1) -> List[SuggestedOffset]:
        """Get intelligent offset suggestions from cache."""
        if not self._rom_cache.cache_enabled:
            return []
            
        with self._suggestion_lock:
            try:
                rom_hash = self._rom_cache._get_rom_hash(rom_path)
                cache_file = self._rom_cache._get_cache_file_path(rom_hash, "offset_suggestions")
                
                if not self._rom_cache._is_cache_valid(cache_file, rom_path):
                    return []
                
                cache_data = self._rom_cache._load_cache_data(cache_file)
                if not cache_data or "suggestions" not in cache_data:
                    return []
                
                suggestions = []
                for suggestion_dict in cache_data["suggestions"]:
                    suggestion = SuggestedOffset.from_dict(suggestion_dict)
                    
                    # Filter by confidence and limit
                    if suggestion.confidence >= min_confidence:
                        # Update preview availability
                        suggestion.preview_available = self._has_cached_preview(rom_path, suggestion.offset)
                        suggestions.append(suggestion)
                        
                    if len(suggestions) >= limit:
                        break
                
                logger.debug(f"Loaded {len(suggestions)} offset suggestions")
                return suggestions
                
            except Exception as e:
                logger.warning(f"Failed to load offset suggestions: {e}")
                return []
    
    def save_preview_batch(self, rom_path: str, batch_data: BatchPreviewData) -> bool:
        """Save batch preview data for efficient range operations."""
        if not self._rom_cache.cache_enabled:
            return False
            
        with self._batch_lock:
            try:
                rom_hash = self._rom_cache._get_rom_hash(rom_path)
                batch_id = f"batch_{batch_data.start_offset:08X}_{batch_data.end_offset:08X}_{batch_data.step_size:04X}"
                cache_file = self._rom_cache._get_cache_file_path(rom_hash, batch_id)
                
                # Serialize batch with compressed previews
                previews_data = {}
                total_raw_size = 0
                total_compressed_size = 0
                
                for offset, preview in batch_data.previews.items():
                    compressed_tiles = self._compress_tile_data(preview.tile_data)
                    previews_data[str(offset)] = {
                        **preview.to_dict(),
                        "tile_data": compressed_tiles,
                        "compressed": True
                    }
                    total_raw_size += len(preview.tile_data)
                    total_compressed_size += len(compressed_tiles)
                
                cache_data = {
                    "version": self.PREVIEW_CACHE_VERSION,
                    "rom_path": os.path.abspath(rom_path),
                    "rom_hash": rom_hash,
                    "cached_at": time.time(),
                    "batch": {
                        "start_offset": batch_data.start_offset,
                        "end_offset": batch_data.end_offset,
                        "step_size": batch_data.step_size,
                        "previews": previews_data,
                        "cache_strategy": batch_data.cache_strategy,
                        "total_size_bytes": batch_data.total_size_bytes,
                        "preview_count": len(previews_data),
                        "compression_stats": {
                            "raw_size_bytes": total_raw_size,
                            "compressed_size_bytes": total_compressed_size,
                            "compression_ratio": total_compressed_size / total_raw_size if total_raw_size > 0 else 1.0
                        }
                    }
                }
                
                success = self._rom_cache._save_cache_data(cache_file, cache_data)
                
                if success:
                    compression_ratio = cache_data["batch"]["compression_stats"]["compression_ratio"]
                    logger.info(f"Cached batch: {len(previews_data)} previews, "
                              f"compression ratio: {compression_ratio:.2f}")
                
                return success
                
            except Exception as e:
                logger.warning(f"Failed to save preview batch: {e}")
                return False
    
    def get_preview_batch(self, rom_path: str, start_offset: int, 
                         end_offset: int, step_size: int = 0x1000) -> Optional[BatchPreviewData]:
        """Get batch preview data for range operations."""
        if not self._rom_cache.cache_enabled:
            return None
            
        with self._batch_lock:
            try:
                rom_hash = self._rom_cache._get_rom_hash(rom_path)
                batch_id = f"batch_{start_offset:08X}_{end_offset:08X}_{step_size:04X}"
                cache_file = self._rom_cache._get_cache_file_path(rom_hash, batch_id)
                
                if not self._rom_cache._is_cache_valid(cache_file, rom_path):
                    return None
                
                cache_data = self._rom_cache._load_cache_data(cache_file)
                if not cache_data or "batch" not in cache_data:
                    return None
                
                batch_dict = cache_data["batch"]
                
                # Deserialize previews with decompression
                previews = {}
                for offset_str, preview_dict in batch_dict["previews"].items():
                    offset = int(offset_str)
                    
                    if preview_dict.get("compressed", False):
                        tile_data = self._decompress_tile_data(preview_dict["tile_data"])
                    else:
                        tile_data = base64.b64decode(preview_dict["tile_data"])
                    
                    preview = PreviewData.from_dict(preview_dict, tile_data)
                    previews[offset] = preview
                
                batch_data = BatchPreviewData(
                    start_offset=batch_dict["start_offset"],
                    end_offset=batch_dict["end_offset"],
                    step_size=batch_dict["step_size"],
                    previews=previews,
                    cache_strategy=batch_dict.get("cache_strategy", "adaptive"),
                    total_size_bytes=batch_dict.get("total_size_bytes", 0),
                    cached_at=datetime.fromtimestamp(cache_data["cached_at"])
                )
                
                logger.debug(f"Loaded batch: {len(previews)} previews")
                return batch_data
                
            except Exception as e:
                logger.warning(f"Failed to load preview batch: {e}")
                return None
    
    def invalidate_preview_cache(self, rom_path: str, 
                                offset_pattern: str = "*") -> int:
        """Invalidate preview cache entries matching pattern."""
        if not self._rom_cache.cache_enabled:
            return 0
            
        try:
            rom_hash = self._rom_cache._get_rom_hash(rom_path)
            invalidated_count = 0
            
            # Individual preview caches
            if offset_pattern == "*":
                pattern = f"{rom_hash}_preview_*.json"
            else:
                pattern = f"{rom_hash}_preview_{offset_pattern}.json"
            
            for cache_file in self._rom_cache.cache_dir.glob(pattern):
                try:
                    cache_file.unlink()
                    invalidated_count += 1
                except OSError:
                    pass
            
            # Batch caches that might contain these offsets
            batch_pattern = f"{rom_hash}_batch_*.json"
            for cache_file in self._rom_cache.cache_dir.glob(batch_pattern):
                if self._batch_contains_pattern(cache_file, offset_pattern):
                    try:
                        cache_file.unlink()
                        invalidated_count += 1
                    except OSError:
                        pass
            
            if invalidated_count > 0:
                logger.info(f"Invalidated {invalidated_count} cache entries")
            
            return invalidated_count
            
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")
            return 0
    
    def _compress_tile_data(self, tile_data: bytes) -> str:
        """Compress tile data for storage efficiency."""
        try:
            compressed = zlib.compress(tile_data, level=self.COMPRESSION_LEVEL)
            return base64.b64encode(compressed).decode('ascii')
        except Exception as e:
            logger.warning(f"Compression failed, storing uncompressed: {e}")
            return base64.b64encode(tile_data).decode('ascii')
    
    def _decompress_tile_data(self, compressed_data: str) -> bytes:
        """Decompress tile data from storage."""
        try:
            compressed = base64.b64decode(compressed_data.encode('ascii'))
            return zlib.decompress(compressed)
        except zlib.error:
            # Fallback: assume it's uncompressed base64
            return base64.b64decode(compressed_data.encode('ascii'))
    
    def _has_cached_preview(self, rom_path: str, offset: int) -> bool:
        """Check if preview is cached for given offset."""
        return self.get_preview_data(rom_path, offset) is not None
    
    def _has_scan_results(self, rom_path: str) -> bool:
        """Check if ROM has cached scan results."""
        # Implementation depends on existing scan cache structure
        return len(list(self._rom_cache.cache_dir.glob(f"*_scan_progress_*.json"))) > 0
    
    def _has_access_history(self, rom_path: str) -> bool:
        """Check if ROM has access history."""
        # Could be implemented by tracking preview access times
        return False  # Placeholder
    
    def _batch_contains_pattern(self, cache_file: Path, offset_pattern: str) -> bool:
        """Check if batch cache contains offsets matching pattern."""
        if offset_pattern == "*":
            return True
        
        # For more specific patterns, would need to parse the batch cache
        # This is a simplified implementation
        return False

# Global instance factory
def get_rom_cache_extensions() -> ROMCachePreviewExtensions:
    """Get ROM cache extensions instance."""
    from utils.rom_cache import get_rom_cache
    return ROMCachePreviewExtensions(get_rom_cache())
```

## Phase 2: Cache-Aware Preview Coordinator

### 2.1 Enhanced Preview Coordinator

```python
# File: ui/common/cache_aware_preview_coordinator.py
"""Cache-aware preview coordinator with dual-tier caching."""

import time
import weakref
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Callable

from PyQt6.QtCore import QObject, QTimer, QThread, pyqtSignal, QMutex, QMutexLocker
from PyQt6.QtWidgets import QSlider

from ui.common.smart_preview_coordinator import SmartPreviewCoordinator, DragState
from ui.common.preview_cache import PreviewCache
from ui.common.preview_worker_pool import PreviewWorkerPool
from utils.cache_data_structures import PreviewData, SuggestedOffset
from utils.rom_cache_extensions import get_rom_cache_extensions
from utils.logging_config import get_logger

logger = get_logger(__name__)

class CacheStrategy(Enum):
    """Cache population strategies."""
    IMMEDIATE = auto()      # Only memory cache, instant response
    STANDARD = auto()       # Memory + persistent cache
    PREEMPTIVE = auto()     # Standard + predictive caching
    BATCH = auto()          # Bulk operations with range caching

class CacheAwarePreviewCoordinator(SmartPreviewCoordinator):
    """
    Enhanced preview coordinator with ROM cache integration.
    
    Provides dual-tier caching strategy:
    - Tier 1: Memory cache (PreviewCache) for instant access
    - Tier 2: Persistent cache (ROM cache) for cross-session persistence
    
    Features:
    - Intelligent cache population
    - Batch preview operations  
    - Thread-safe cache coordination
    - Performance metrics tracking
    """
    
    # Enhanced signals for cache operations
    cache_hit = pyqtSignal(str, int, float)     # cache_type, offset, response_time_ms
    cache_miss = pyqtSignal(str, int)           # cache_type, offset
    batch_cache_ready = pyqtSignal(int, int, int)  # start_offset, end_offset, count
    suggestions_loaded = pyqtSignal(list)       # List[SuggestedOffset]
    cache_performance = pyqtSignal(dict)        # Performance statistics
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        # ROM cache integration
        self._rom_cache_ext = get_rom_cache_extensions()
        self._current_rom_path: str = ""
        
        # Cache strategy and configuration
        self._cache_strategy = CacheStrategy.STANDARD
        self._batch_preload_enabled = True
        self._suggestion_generation_enabled = True
        
        # Cache coordination
        self._cache_warm_worker: Optional['CacheWarmingWorker'] = None
        self._suggestion_worker: Optional['SuggestionWorker'] = None
        
        # Performance tracking
        self._cache_stats = {
            "memory_hits": 0,
            "persistent_hits": 0,
            "cache_misses": 0,
            "total_requests": 0,
            "avg_response_time_ms": 0.0
        }
        self._performance_timer = QTimer(self)
        self._performance_timer.timeout.connect(self._emit_performance_stats)
        self._performance_timer.start(5000)  # Report every 5 seconds
        
        # Thread safety
        self._cache_mutex = QMutex()
    
    def set_rom_context(self, rom_path: str) -> None:
        """Set ROM context and initialize cache-aware features."""
        if self._current_rom_path == rom_path:
            return
            
        with QMutexLocker(self._cache_mutex):
            self._current_rom_path = rom_path
            
            # Reset cache statistics for new ROM
            self._cache_stats = {
                "memory_hits": 0,
                "persistent_hits": 0, 
                "cache_misses": 0,
                "total_requests": 0,
                "avg_response_time_ms": 0.0
            }
        
        # Load cached offset suggestions
        if self._suggestion_generation_enabled:
            self._load_cached_suggestions()
        
        # Start cache warming if enabled
        if self._batch_preload_enabled:
            self._start_predictive_caching()
        
        logger.info(f"ROM context set: {rom_path}")
    
    def set_cache_strategy(self, strategy: CacheStrategy) -> None:
        """Set cache population strategy."""
        self._cache_strategy = strategy
        logger.debug(f"Cache strategy set to: {strategy.name}")
    
    def request_preview(self, offset: int, priority: int = 0) -> int:
        """Enhanced preview request with dual-tier cache checking."""
        request_start_time = time.time()
        request_id = self._request_counter
        self._request_counter += 1
        
        with QMutexLocker(self._cache_mutex):
            self._cache_stats["total_requests"] += 1
        
        # Strategy 1: Check memory cache first (fastest)
        cache_key = self._preview_cache.make_key(self._current_rom_path, offset)
        cached_data = self._preview_cache.get(cache_key)
        
        if cached_data:
            response_time = (time.time() - request_start_time) * 1000
            self._update_cache_stats("memory_hits", response_time)
            
            # Emit cached preview immediately
            tile_data, width, height, sprite_name = cached_data
            self.preview_cached.emit(tile_data, width, height, sprite_name)
            self.cache_hit.emit("memory", offset, response_time)
            
            return request_id
        
        # Strategy 2: Check persistent cache (still fast)
        persistent_data = self._rom_cache_ext.get_preview_data(self._current_rom_path, offset)
        if persistent_data:
            response_time = (time.time() - request_start_time) * 1000
            self._update_cache_stats("persistent_hits", response_time)
            
            # Restore to memory cache for future access
            cached_data = (persistent_data.tile_data, persistent_data.width,
                          persistent_data.height, persistent_data.sprite_name)
            self._preview_cache.put(cache_key, cached_data)
            
            # Emit cached preview
            self.preview_cached.emit(persistent_data.tile_data, persistent_data.width,
                                   persistent_data.height, persistent_data.sprite_name)
            self.cache_hit.emit("persistent", offset, response_time)
            
            return request_id
        
        # Cache miss - fall back to generation
        self._update_cache_stats("cache_misses", 0)
        self.cache_miss.emit("all", offset)
        
        # Use parent's generation logic
        return super().request_preview(offset, priority)
    
    def request_batch_preview(self, start_offset: int, end_offset: int,
                            step_size: int = 0x1000, priority: int = 0) -> None:
        """Request batch preview generation with intelligent caching."""
        if not self._batch_preload_enabled:
            return
        
        # Check if batch is already cached
        batch_data = self._rom_cache_ext.get_preview_batch(
            self._current_rom_path, start_offset, end_offset, step_size)
        
        if batch_data and len(batch_data.previews) > 0:
            # Load batch into memory cache
            loaded_count = 0
            for offset, preview in batch_data.previews.items():
                cache_key = self._preview_cache.make_key(self._current_rom_path, offset)
                cached_data = (preview.tile_data, preview.width,
                              preview.height, preview.sprite_name)
                self._preview_cache.put(cache_key, cached_data)
                loaded_count += 1
            
            self.batch_cache_ready.emit(start_offset, end_offset, loaded_count)
            logger.info(f"Loaded batch cache: {loaded_count} previews")
            return
        
        # Submit batch generation job
        if self._cache_warm_worker is None or not self._cache_warm_worker.isRunning():
            self._cache_warm_worker = CacheWarmingWorker(
                self._current_rom_path, start_offset, end_offset, step_size,
                priority, parent=self)
            self._cache_warm_worker.batch_completed.connect(self._on_batch_completed)
            self._cache_warm_worker.progress_updated.connect(self._on_batch_progress)
            self._cache_warm_worker.start()
    
    def _on_preview_generated(self, tile_data: bytes, width: int, height: int,
                            sprite_name: str, offset: int, generation_time_ms: float):
        """Handle preview generation completion with dual caching."""
        # Store in memory cache
        cache_key = self._preview_cache.make_key(self._current_rom_path, offset)
        cached_data = (tile_data, width, height, sprite_name)
        self._preview_cache.put(cache_key, cached_data)
        
        # Store in persistent cache asynchronously
        if self._rom_cache_ext._rom_cache.cache_enabled:
            preview_data = PreviewData(
                offset=offset,
                tile_data=tile_data,
                width=width,
                height=height,
                sprite_name=sprite_name,
                generated_at=time.time(),
                generation_time_ms=generation_time_ms,
                rom_hash=self._rom_cache_ext._rom_cache._get_rom_hash(self._current_rom_path)
            )
            
            # Save asynchronously to avoid blocking UI
            self._async_save_preview(preview_data)
        
        # Emit result
        self.preview_ready.emit(tile_data, width, height, sprite_name)
    
    def _async_save_preview(self, preview_data: PreviewData) -> None:
        """Save preview data asynchronously."""
        # Use thread pool for async save to avoid blocking
        if hasattr(self, '_worker_pool') and self._worker_pool:
            def save_operation():
                return self._rom_cache_ext.save_preview_data(
                    self._current_rom_path, preview_data.offset, preview_data)
            
            # Submit to thread pool (implementation depends on worker pool design)
            # self._worker_pool.submit(save_operation)
        else:
            # Fallback: save synchronously (may cause brief UI pause)
            self._rom_cache_ext.save_preview_data(
                self._current_rom_path, preview_data.offset, preview_data)
    
    def _load_cached_suggestions(self) -> None:
        """Load cached offset suggestions asynchronously."""
        if self._suggestion_worker is None or not self._suggestion_worker.isRunning():
            self._suggestion_worker = SuggestionWorker(self._current_rom_path, parent=self)
            self._suggestion_worker.suggestions_ready.connect(self.suggestions_loaded.emit)
            self._suggestion_worker.error_occurred.connect(self._on_suggestion_error)
            self._suggestion_worker.start()
    
    def _start_predictive_caching(self) -> None:
        """Start predictive caching based on ROM analysis."""
        # Common sprite areas to pre-warm
        common_ranges = [
            (0x200000, 0x210000, 0x1000),  # Common sprite data area
            (0x300000, 0x310000, 0x1000),  # Secondary sprite area
        ]
        
        for start, end, step in common_ranges:
            self.request_batch_preview(start, end, step, priority=-1)  # Low priority
    
    def _update_cache_stats(self, stat_type: str, response_time_ms: float) -> None:
        """Update cache performance statistics."""
        with QMutexLocker(self._cache_mutex):
            self._cache_stats[stat_type] += 1
            
            # Update average response time
            total_requests = self._cache_stats["total_requests"]
            if total_requests > 0:
                current_avg = self._cache_stats["avg_response_time_ms"]
                self._cache_stats["avg_response_time_ms"] = (
                    (current_avg * (total_requests - 1) + response_time_ms) / total_requests
                )
    
    def _emit_performance_stats(self) -> None:
        """Emit cache performance statistics."""
        with QMutexLocker(self._cache_mutex):
            if self._cache_stats["total_requests"] > 0:
                hit_rate = ((self._cache_stats["memory_hits"] + 
                           self._cache_stats["persistent_hits"]) / 
                          self._cache_stats["total_requests"]) * 100
                
                performance_data = {
                    **self._cache_stats,
                    "cache_hit_rate_percent": hit_rate,
                    "memory_cache_size": len(self._preview_cache._cache) if hasattr(self._preview_cache, '_cache') else 0
                }
                
                self.cache_performance.emit(performance_data)
    
    def _on_batch_completed(self, batch_data) -> None:
        """Handle batch caching completion."""
        # Load completed batch into memory cache
        loaded_count = 0
        for offset, preview in batch_data.previews.items():
            cache_key = self._preview_cache.make_key(self._current_rom_path, offset)
            cached_data = (preview.tile_data, preview.width,
                          preview.height, preview.sprite_name)
            self._preview_cache.put(cache_key, cached_data)
            loaded_count += 1
        
        self.batch_cache_ready.emit(batch_data.start_offset, batch_data.end_offset, loaded_count)
        logger.info(f"Batch caching completed: {loaded_count} previews")
    
    def _on_batch_progress(self, current: int, total: int) -> None:
        """Handle batch caching progress updates."""
        # Could emit progress signal for UI feedback
        pass
    
    def _on_suggestion_error(self, error_message: str) -> None:
        """Handle suggestion loading errors."""
        logger.warning(f"Suggestion loading failed: {error_message}")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get current cache performance statistics."""
        with QMutexLocker(self._cache_mutex):
            return self._cache_stats.copy()
    
    def clear_cache(self, cache_type: str = "all") -> int:
        """Clear cache entries."""
        cleared_count = 0
        
        if cache_type in ["all", "memory"]:
            if hasattr(self._preview_cache, 'clear'):
                cleared_count += self._preview_cache.clear()
        
        if cache_type in ["all", "persistent"]:
            cleared_count += self._rom_cache_ext.invalidate_preview_cache(
                self._current_rom_path, "*")
        
        logger.info(f"Cleared {cleared_count} cache entries ({cache_type})")
        return cleared_count


# Worker classes for background operations
class CacheWarmingWorker(QThread):
    """Background worker for cache warming operations."""
    
    batch_completed = pyqtSignal(object)  # BatchPreviewData
    progress_updated = pyqtSignal(int, int)  # current, total
    error_occurred = pyqtSignal(str)
    
    def __init__(self, rom_path: str, start_offset: int, end_offset: int,
                 step_size: int, priority: int = 0, parent=None):
        super().__init__(parent)
        self._rom_path = rom_path
        self._start_offset = start_offset
        self._end_offset = end_offset
        self._step_size = step_size
        self._priority = priority
        self._cancelled = False
    
    def run(self):
        """Execute cache warming with efficient batch operations."""
        try:
            from core.managers.registry import get_manager_registry
            from utils.cache_data_structures import BatchPreviewData
            from datetime import datetime
            
            extraction_manager = get_manager_registry().get_extraction_manager()
            rom_cache_ext = get_rom_cache_extensions()
            
            previews = {}
            total_offsets = (self._end_offset - self._start_offset) // self._step_size
            current_count = 0
            
            logger.info(f"Starting cache warming: 0x{self._start_offset:X} to 0x{self._end_offset:X}, step 0x{self._step_size:X}")
            
            for offset in range(self._start_offset, self._end_offset, self._step_size):
                if self._cancelled:
                    break
                
                # Check if already cached
                existing = rom_cache_ext.get_preview_data(self._rom_path, offset)
                if existing:
                    previews[offset] = existing
                else:
                    # Generate new preview
                    try:
                        start_time = time.time()
                        tile_data, width, height = extraction_manager.get_sprite_preview(
                            self._rom_path, offset, f"batch_0x{offset:X}")
                        generation_time = (time.time() - start_time) * 1000
                        
                        preview_data = PreviewData(
                            offset=offset,
                            tile_data=tile_data,
                            width=width,
                            height=height,
                            sprite_name=f"sprite_0x{offset:X}",
                            generated_at=datetime.now(),
                            generation_time_ms=generation_time,
                            rom_hash=rom_cache_ext._rom_cache._get_rom_hash(self._rom_path)
                        )
                        
                        previews[offset] = preview_data
                        
                        # Save individual preview
                        rom_cache_ext.save_preview_data(self._rom_path, offset, preview_data)
                        
                    except Exception as e:
                        logger.warning(f"Failed to generate preview for offset 0x{offset:X}: {e}")
                
                current_count += 1
                if current_count % 10 == 0:  # Update progress every 10 items
                    self.progress_updated.emit(current_count, total_offsets)
            
            # Save batch data if we have previews
            if previews and not self._cancelled:
                batch_data = BatchPreviewData(
                    start_offset=self._start_offset,
                    end_offset=self._end_offset,
                    step_size=self._step_size,
                    previews=previews,
                    cache_strategy="batch_warming",
                    total_size_bytes=sum(len(p.tile_data) for p in previews.values()),
                    cached_at=datetime.now()
                )
                
                rom_cache_ext.save_preview_batch(self._rom_path, batch_data)
                self.batch_completed.emit(batch_data)
                
                logger.info(f"Cache warming completed: {len(previews)} previews generated")
                
        except Exception as e:
            self.error_occurred.emit(str(e))
            logger.error(f"Cache warming failed: {e}")
    
    def cancel(self):
        """Cancel the cache warming operation."""
        self._cancelled = True


class SuggestionWorker(QThread):
    """Background worker for loading offset suggestions."""
    
    suggestions_ready = pyqtSignal(list)  # List[SuggestedOffset]
    error_occurred = pyqtSignal(str)
    
    def __init__(self, rom_path: str, parent=None):
        super().__init__(parent)
        self._rom_path = rom_path
    
    def run(self):
        """Load offset suggestions from cache."""
        try:
            rom_cache_ext = get_rom_cache_extensions()
            suggestions = rom_cache_ext.get_offset_suggestions(self._rom_path, limit=100)
            
            if suggestions:
                self.suggestions_ready.emit(suggestions)
                logger.info(f"Loaded {len(suggestions)} offset suggestions")
            else:
                # Generate suggestions if none cached
                self._generate_suggestions()
                
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _generate_suggestions(self):
        """Generate new offset suggestions."""
        # Implementation would analyze ROM structure and generate suggestions
        # This is a placeholder for the actual suggestion generation logic
        pass
```

This implementation provides a solid foundation for integrating ROM caching with the manual offset dialog. The key features include:

## Key Implementation Features

1. **Dual-Tier Caching**: Memory cache for instant access, persistent cache for cross-session storage
2. **Thread Safety**: Proper mutex usage and thread-safe operations
3. **Compression**: Efficient storage with zlib compression
4. **Performance Tracking**: Detailed cache performance metrics
5. **Batch Operations**: Efficient range-based preview generation
6. **Async Operations**: Background workers for cache warming and suggestion loading
7. **Error Handling**: Comprehensive error handling with fallbacks
8. **Configurable Strategies**: Different cache population strategies

## Next Steps for Full Integration

1. **Update Manual Offset Dialog**: Replace `SmartPreviewCoordinator` with `CacheAwarePreviewCoordinator`
2. **Extend ExtractionManager**: Add cache coordination methods
3. **Implement Suggestion Engine**: Complete the offset suggestion generation
4. **Add UI Feedback**: Show cache performance and batch loading progress
5. **Testing**: Comprehensive tests for cache operations and thread safety

The architecture provides excellent performance improvements while maintaining clean separation of concerns and robust error handling patterns.