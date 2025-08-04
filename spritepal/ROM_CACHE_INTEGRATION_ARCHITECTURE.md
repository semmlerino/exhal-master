# ROM Cache Integration Architecture for Manual Offset Dialog

## Executive Summary

This document outlines a comprehensive architecture for integrating ROM caching with the manual offset dialog, providing persistent preview data caching, intelligent cache population strategies, and thread-safe coordination between UI and worker components.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Manual Offset Dialog                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │ SimpleBrowseTab │  │ SmartPreviewTab  │  │  HistoryTab     │ │
│  │                 │  │                  │  │                 │ │
│  │ - Slider        │  │ - Auto-suggest  │  │ - Recent        │ │
│  │ - Navigation    │  │ - Batch preview  │  │ - Favorites     │ │
│  └─────────────────┘  └──────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Cache-Aware Preview Coordinator                   │
├─────────────────────────────────────────────────────────────────┤
│  ├─ Cache Check Strategy                                        │
│  ├─ Request Batching & Prioritization                          │
│  ├─ Worker Thread Coordination                                 │
│  └─ Fallback & Error Handling                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Dual-Cache Architecture                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐        ┌─────────────────────────────┐ │
│  │   Memory Cache      │        │      Persistent Cache       │ │
│  │  (PreviewCache)     │        │       (ROMCache)            │ │
│  │                     │        │                             │ │
│  │ - LRU Eviction      │◄──────►│ - Preview Data              │ │
│  │ - 20 entries        │        │ - Offset Suggestions        │ │
│  │ - 2MB limit         │        │ - Batch Cache Regions       │ │
│  │ - Sub-second access │        │ - Cross-session persistence │ │
│  └─────────────────────┘        └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Enhanced ROM Cache API                        │
├─────────────────────────────────────────────────────────────────┤
│  ├─ save_preview_data(rom_path, offset, preview_data)          │
│  ├─ get_preview_data(rom_path, offset) -> PreviewData          │
│  ├─ save_offset_suggestions(rom_path, suggestions)             │
│  ├─ get_offset_suggestions(rom_path) -> List[SuggestedOffset]  │
│  ├─ save_preview_batch(rom_path, offset_range, batch_data)     │
│  ├─ get_preview_batch(rom_path, offset_range) -> BatchData     │
│  └─ invalidate_preview_cache(rom_path, offset_pattern)         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Core Integration Layer                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐        ┌─────────────────────────────┐ │
│  │ ExtractionManager   │        │    Worker Threads           │ │
│  │                     │        │                             │ │
│  │ - Cache-aware       │        │ - PreviewWorker             │ │
│  │   preview generation│        │ - BatchPreloadWorker        │ │
│  │ - Batch operations  │        │ - SuggestionWorker          │ │
│  │ - Thread coordination│       │ - Cache warming threads     │ │
│  └─────────────────────┘        └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 1. Cache API Extensions for Preview Data

### 1.1 Preview Data Structures

```python
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class PreviewData:
    """Structured preview data for caching."""
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

@dataclass 
class SuggestedOffset:
    """Offset suggestion with confidence scoring."""
    offset: int
    confidence: float  # 0.0 to 1.0
    reason: str       # "scan_result", "pattern_match", "user_history" 
    sprite_name: Optional[str] = None
    preview_available: bool = False
    last_accessed: Optional[datetime] = None

@dataclass
class BatchPreviewData:
    """Batch preview data for efficient range caching."""
    start_offset: int
    end_offset: int
    step_size: int
    previews: Dict[int, PreviewData]
    cache_strategy: str  # "full", "sparse", "adaptive"
    total_size_bytes: int
    cached_at: datetime
```

### 1.2 Enhanced ROM Cache API

```python
class ROMCacheExtensions:
    """Extensions to ROM cache for preview data management."""
    
    PREVIEW_CACHE_VERSION = "2.0"
    
    def save_preview_data(self, rom_path: str, offset: int, 
                         preview_data: PreviewData) -> bool:
        """
        Save individual preview data to persistent cache.
        
        Args:
            rom_path: Path to ROM file
            offset: ROM offset for sprite
            preview_data: Structured preview data
            
        Returns:
            True if saved successfully
        """
        if not self._cache_enabled:
            return False
            
        try:
            rom_hash = self._get_rom_hash(rom_path)
            cache_key = f"preview_{offset:08X}"
            cache_file = self._get_cache_file_path(rom_hash, cache_key)
            
            # Serialize preview data with compression for tile data
            cache_data = {
                "version": self.PREVIEW_CACHE_VERSION,
                "rom_path": os.path.abspath(rom_path),
                "rom_hash": rom_hash,
                "cached_at": time.time(),
                "preview": {
                    "offset": preview_data.offset,
                    "tile_data": self._compress_tile_data(preview_data.tile_data),
                    "width": preview_data.width, 
                    "height": preview_data.height,
                    "sprite_name": preview_data.sprite_name,
                    "generated_at": preview_data.generated_at.isoformat(),
                    "generation_time_ms": preview_data.generation_time_ms,
                    "rom_hash": preview_data.rom_hash,
                    "compression_info": preview_data.compression_info,
                    "metadata": preview_data.metadata
                }
            }
            
            # Save with atomic write
            return self._save_cache_data(cache_file, cache_data)
            
        except Exception as e:
            logger.warning(f"Failed to save preview data for offset 0x{offset:X}: {e}")
            return False
    
    def get_preview_data(self, rom_path: str, offset: int) -> Optional[PreviewData]:
        """
        Retrieve preview data from persistent cache.
        
        Args:
            rom_path: Path to ROM file  
            offset: ROM offset for sprite
            
        Returns:
            PreviewData if cached and valid, None otherwise
        """
        if not self._cache_enabled:
            return None
            
        try:
            rom_hash = self._get_rom_hash(rom_path)
            cache_key = f"preview_{offset:08X}"
            cache_file = self._get_cache_file_path(rom_hash, cache_key)
            
            if not self._is_cache_valid(cache_file, rom_path):
                return None
                
            cache_data = self._load_cache_data(cache_file)
            if not cache_data:
                return None
                
            # Validate cache format
            if (cache_data.get("version") != self.PREVIEW_CACHE_VERSION or
                "preview" not in cache_data):
                return None
                
            preview_dict = cache_data["preview"]
            
            # Deserialize with decompression
            return PreviewData(
                offset=preview_dict["offset"],
                tile_data=self._decompress_tile_data(preview_dict["tile_data"]),
                width=preview_dict["width"],
                height=preview_dict["height"], 
                sprite_name=preview_dict["sprite_name"],
                generated_at=datetime.fromisoformat(preview_dict["generated_at"]),
                generation_time_ms=preview_dict["generation_time_ms"],
                rom_hash=preview_dict["rom_hash"],
                compression_info=preview_dict.get("compression_info"),
                metadata=preview_dict.get("metadata")
            )
            
        except Exception as e:
            logger.warning(f"Failed to load preview data for offset 0x{offset:X}: {e}")
            return None
    
    def save_offset_suggestions(self, rom_path: str, 
                               suggestions: List[SuggestedOffset]) -> bool:
        """Save intelligent offset suggestions based on scan results."""
        if not self._cache_enabled:
            return False
            
        try:
            rom_hash = self._get_rom_hash(rom_path)
            cache_file = self._get_cache_file_path(rom_hash, "offset_suggestions")
            
            # Serialize suggestions with ranking
            suggestions_data = []
            for suggestion in sorted(suggestions, key=lambda s: s.confidence, reverse=True):
                suggestions_data.append({
                    "offset": suggestion.offset,
                    "confidence": suggestion.confidence,
                    "reason": suggestion.reason,
                    "sprite_name": suggestion.sprite_name,
                    "preview_available": suggestion.preview_available,
                    "last_accessed": suggestion.last_accessed.isoformat() if suggestion.last_accessed else None
                })
            
            cache_data = {
                "version": self.PREVIEW_CACHE_VERSION,
                "rom_path": os.path.abspath(rom_path),
                "rom_hash": rom_hash,
                "cached_at": time.time(),
                "suggestions": suggestions_data,
                "total_suggestions": len(suggestions_data)
            }
            
            return self._save_cache_data(cache_file, cache_data)
            
        except Exception as e:
            logger.warning(f"Failed to save offset suggestions: {e}")
            return False
    
    def get_offset_suggestions(self, rom_path: str, 
                              limit: int = 50) -> List[SuggestedOffset]:
        """Get intelligent offset suggestions from cache."""
        if not self._cache_enabled:
            return []
            
        try:
            rom_hash = self._get_rom_hash(rom_path)
            cache_file = self._get_cache_file_path(rom_hash, "offset_suggestions")
            
            if not self._is_cache_valid(cache_file, rom_path):
                return []
                
            cache_data = self._load_cache_data(cache_file)
            if not cache_data or "suggestions" not in cache_data:
                return []
                
            suggestions = []
            for suggestion_dict in cache_data["suggestions"][:limit]:
                suggestions.append(SuggestedOffset(
                    offset=suggestion_dict["offset"],
                    confidence=suggestion_dict["confidence"],
                    reason=suggestion_dict["reason"],
                    sprite_name=suggestion_dict.get("sprite_name"),
                    preview_available=suggestion_dict.get("preview_available", False),
                    last_accessed=datetime.fromisoformat(suggestion_dict["last_accessed"]) 
                                 if suggestion_dict.get("last_accessed") else None
                ))
                
            return suggestions
            
        except Exception as e:
            logger.warning(f"Failed to load offset suggestions: {e}")
            return []
    
    def save_preview_batch(self, rom_path: str, batch_data: BatchPreviewData) -> bool:
        """Save batch preview data for efficient range operations."""
        if not self._cache_enabled:
            return False
            
        try:
            rom_hash = self._get_rom_hash(rom_path)
            batch_id = f"batch_{batch_data.start_offset:08X}_{batch_data.end_offset:08X}"
            cache_file = self._get_cache_file_path(rom_hash, batch_id)
            
            # Serialize batch with preview data compression
            previews_data = {}
            for offset, preview in batch_data.previews.items():
                previews_data[str(offset)] = {
                    "offset": preview.offset,
                    "tile_data": self._compress_tile_data(preview.tile_data),
                    "width": preview.width,
                    "height": preview.height,
                    "sprite_name": preview.sprite_name,
                    "generated_at": preview.generated_at.isoformat(),
                    "generation_time_ms": preview.generation_time_ms,
                    "rom_hash": preview.rom_hash
                }
            
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
                    "preview_count": len(previews_data)
                }
            }
            
            return self._save_cache_data(cache_file, cache_data)
            
        except Exception as e:
            logger.warning(f"Failed to save preview batch: {e}")
            return False
    
    def _compress_tile_data(self, tile_data: bytes) -> str:
        """Compress tile data for storage efficiency."""
        import base64
        import zlib
        compressed = zlib.compress(tile_data, level=6)  # Good compression/speed balance
        return base64.b64encode(compressed).decode('ascii')
    
    def _decompress_tile_data(self, compressed_data: str) -> bytes:
        """Decompress tile data from storage."""
        import base64
        import zlib
        compressed = base64.b64decode(compressed_data.encode('ascii'))
        return zlib.decompress(compressed)
```

## 2. Integration Architecture

### 2.1 Cache-Aware Preview Coordinator

```python
class CacheAwarePreviewCoordinator(SmartPreviewCoordinator):
    """
    Enhanced preview coordinator with ROM cache integration.
    
    Provides:
    - Dual-tier caching (memory + persistent)
    - Intelligent cache population
    - Batch preview operations
    - Thread-safe cache coordination  
    """
    
    # Enhanced signals for cache operations
    cache_hit = pyqtSignal(str, int)  # cache_type, offset
    cache_miss = pyqtSignal(str, int)  # cache_type, offset
    batch_cache_ready = pyqtSignal(int, int, int)  # start_offset, end_offset, count
    suggestions_loaded = pyqtSignal(list)  # List[SuggestedOffset]
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        # ROM cache integration
        self._rom_cache = get_rom_cache()
        self._current_rom_path: str = ""
        
        # Enhanced cache coordination
        self._cache_warm_worker: Optional[CacheWarmingWorker] = None
        self._suggestion_worker: Optional[SuggestionWorker] = None
        
        # Cache strategy configuration
        self._cache_strategy = CacheStrategy.ADAPTIVE
        self._batch_preload_enabled = True
        self._suggestion_generation_enabled = True
        
    def set_rom_context(self, rom_path: str) -> None:
        """Set ROM context and initialize cache-aware features."""
        if self._current_rom_path == rom_path:
            return
            
        self._current_rom_path = rom_path
        
        # Load cached offset suggestions
        if self._suggestion_generation_enabled:
            self._load_cached_suggestions()
            
        # Start cache warming if enabled
        if self._batch_preload_enabled:
            self._start_cache_warming()
    
    @override 
    def request_preview(self, offset: int, priority: int = 0) -> int:
        """Enhanced preview request with cache checking."""
        request_id = self._request_counter
        self._request_counter += 1
        
        # Check memory cache first (fastest)
        cache_key = self._preview_cache.make_key(self._current_rom_path, offset)
        cached_data = self._preview_cache.get(cache_key)
        
        if cached_data:
            # Emit cached preview immediately  
            tile_data, width, height, sprite_name = cached_data
            self.preview_cached.emit(tile_data, width, height, sprite_name)
            self.cache_hit.emit("memory", offset)
            return request_id
            
        # Check persistent cache second (still fast)
        persistent_data = self._rom_cache.get_preview_data(self._current_rom_path, offset)
        if persistent_data:
            # Restore to memory cache and emit
            cached_data = (persistent_data.tile_data, persistent_data.width, 
                          persistent_data.height, persistent_data.sprite_name)
            self._preview_cache.put(cache_key, cached_data)
            self.preview_cached.emit(persistent_data.tile_data, persistent_data.width,
                                   persistent_data.height, persistent_data.sprite_name)
            self.cache_hit.emit("persistent", offset)
            return request_id
        
        # Cache miss - fall back to generation
        self.cache_miss.emit("all", offset)
        return super().request_preview(offset, priority)
    
    def _on_preview_generated(self, tile_data: bytes, width: int, height: int, 
                            sprite_name: str, offset: int, generation_time_ms: float):
        """Handle preview generation completion with caching."""
        # Store in memory cache
        cache_key = self._preview_cache.make_key(self._current_rom_path, offset) 
        cached_data = (tile_data, width, height, sprite_name)
        self._preview_cache.put(cache_key, cached_data)
        
        # Store in persistent cache asynchronously
        if self._rom_cache.cache_enabled:
            preview_data = PreviewData(
                offset=offset,
                tile_data=tile_data,
                width=width,
                height=height,
                sprite_name=sprite_name,
                generated_at=datetime.now(),
                generation_time_ms=generation_time_ms,
                rom_hash=self._rom_cache._get_rom_hash(self._current_rom_path)
            )
            
            # Use thread pool for async cache save
            self._worker_pool.submit_cache_save(self._current_rom_path, offset, preview_data)
        
        # Emit result
        self.preview_ready.emit(tile_data, width, height, sprite_name)
    
    def request_batch_preview(self, start_offset: int, end_offset: int, 
                            step_size: int = 0x1000) -> None:
        """Request batch preview generation with intelligent caching."""
        if not self._batch_preload_enabled:
            return
            
        # Check if batch is already cached
        batch_data = self._rom_cache.get_preview_batch(
            self._current_rom_path, start_offset, end_offset, step_size)
            
        if batch_data and len(batch_data.previews) > 0:
            # Load batch into memory cache
            for offset, preview in batch_data.previews.items():
                cache_key = self._preview_cache.make_key(self._current_rom_path, offset)
                cached_data = (preview.tile_data, preview.width, 
                              preview.height, preview.sprite_name)
                self._preview_cache.put(cache_key, cached_data)
                
            self.batch_cache_ready.emit(start_offset, end_offset, len(batch_data.previews))
            return
        
        # Submit batch generation job
        if self._cache_warm_worker is None or not self._cache_warm_worker.isRunning():
            self._cache_warm_worker = CacheWarmingWorker(
                self._current_rom_path, start_offset, end_offset, step_size, parent=self)
            self._cache_warm_worker.batch_completed.connect(self._on_batch_completed)
            self._cache_warm_worker.start()
    
    def _load_cached_suggestions(self) -> None:
        """Load cached offset suggestions asynchronously.""" 
        if self._suggestion_worker is None or not self._suggestion_worker.isRunning():
            self._suggestion_worker = SuggestionWorker(self._current_rom_path, parent=self)
            self._suggestion_worker.suggestions_ready.connect(self.suggestions_loaded.emit)
            self._suggestion_worker.start()
```

### 2.2 Manual Offset Dialog Integration

```python
class CacheIntegratedManualOffsetDialog(QDialog):
    """Manual offset dialog with full cache integration."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize cache-aware coordinator
        self._preview_coordinator = CacheAwarePreviewCoordinator(self)
        self._extraction_manager = None  # Set via dependency injection
        
        # Cache status tracking
        self._cache_stats = {"hits": 0, "misses": 0, "batch_loads": 0}
        
        self._setup_cache_integration()
        self._setup_ui()
    
    def _setup_cache_integration(self):
        """Set up cache integration signals and workflows."""
        # Connect cache signals for user feedback
        self._preview_coordinator.cache_hit.connect(self._on_cache_hit)
        self._preview_coordinator.cache_miss.connect(self._on_cache_miss)
        self._preview_coordinator.batch_cache_ready.connect(self._on_batch_ready)
        self._preview_coordinator.suggestions_loaded.connect(self._on_suggestions_loaded)
        
        # Connect standard preview signals
        self._preview_coordinator.preview_ready.connect(self._update_preview_widget)
        self._preview_coordinator.preview_cached.connect(self._update_preview_widget) 
        self._preview_coordinator.preview_error.connect(self._handle_preview_error)
    
    def set_rom_context(self, rom_path: str, extraction_manager):
        """Set ROM context with extraction manager integration."""
        self._extraction_manager = extraction_manager
        self._preview_coordinator.set_rom_context(rom_path)
        
        # Configure extraction manager for cache-aware operations
        if hasattr(extraction_manager, 'set_cache_coordinator'):
            extraction_manager.set_cache_coordinator(self._preview_coordinator)
    
    def _on_cache_hit(self, cache_type: str, offset: int):
        """Handle cache hit feedback."""
        self._cache_stats["hits"] += 1
        
        # Visual feedback for cache performance
        if cache_type == "memory":
            self._status_panel.show_message(f"✓ Memory cache hit (0x{offset:X})", 1000)
        elif cache_type == "persistent": 
            self._status_panel.show_message(f"✓ Disk cache hit (0x{offset:X})", 1500)
    
    def _on_cache_miss(self, cache_type: str, offset: int):
        """Handle cache miss feedback."""
        self._cache_stats["misses"] += 1
        self._status_panel.show_message(f"⟳ Generating preview (0x{offset:X})", 2000)
    
    def _on_batch_ready(self, start_offset: int, end_offset: int, count: int):
        """Handle batch cache ready notification."""
        self._cache_stats["batch_loads"] += 1
        range_size = (end_offset - start_offset) // 1024
        self._status_panel.show_message(
            f"✓ Batch cached: {count} previews ({range_size}KB range)", 3000)
    
    def _on_suggestions_loaded(self, suggestions: List[SuggestedOffset]):
        """Handle loaded offset suggestions."""
        if hasattr(self, '_smart_tab'):
            self._smart_tab.update_suggestions(suggestions)
        
        if hasattr(self, '_history_tab'):
            self._history_tab.update_recent_offsets(suggestions)
```

## 3. Cache-Aware Preview Workflow

### 3.1 Multi-Tier Preview Strategy

```python
class PreviewStrategy(Enum):
    """Preview generation and caching strategies."""
    IMMEDIATE = "immediate"      # Memory cache only, instant response
    STANDARD = "standard"        # Memory + persistent cache  
    PREEMPTIVE = "preemptive"   # Standard + predictive caching
    BATCH = "batch"             # Bulk operations with range caching

class CacheAwarePreviewWorkflow:
    """Orchestrates cache-aware preview workflows."""
    
    def __init__(self, coordinator: CacheAwarePreviewCoordinator):
        self._coordinator = coordinator
        self._strategy = PreviewStrategy.STANDARD
        
    async def execute_preview_request(self, offset: int, 
                                    strategy: PreviewStrategy = None) -> PreviewResult:
        """Execute preview request with specified strategy."""
        strategy = strategy or self._strategy
        
        if strategy == PreviewStrategy.IMMEDIATE:
            return await self._immediate_preview(offset)
        elif strategy == PreviewStrategy.STANDARD:
            return await self._standard_preview(offset)
        elif strategy == PreviewStrategy.PREEMPTIVE:
            return await self._preemptive_preview(offset)
        elif strategy == PreviewStrategy.BATCH:
            return await self._batch_preview(offset)
    
    async def _immediate_preview(self, offset: int) -> PreviewResult:
        """Immediate preview from memory cache only."""
        cache_key = self._coordinator._preview_cache.make_key(
            self._coordinator._current_rom_path, offset)
        cached_data = self._coordinator._preview_cache.get(cache_key)
        
        if cached_data:
            return PreviewResult.success(cached_data, source="memory_cache")
        else:
            return PreviewResult.not_available("No cached preview available")
    
    async def _standard_preview(self, offset: int) -> PreviewResult:
        """Standard preview with dual cache checking."""
        # Try memory cache first
        result = await self._immediate_preview(offset)
        if result.success:
            return result
            
        # Try persistent cache 
        persistent_data = self._coordinator._rom_cache.get_preview_data(
            self._coordinator._current_rom_path, offset)
        if persistent_data:
            # Restore to memory and return
            cached_data = (persistent_data.tile_data, persistent_data.width,
                          persistent_data.height, persistent_data.sprite_name)
            cache_key = self._coordinator._preview_cache.make_key(
                self._coordinator._current_rom_path, offset)
            self._coordinator._preview_cache.put(cache_key, cached_data)
            return PreviewResult.success(cached_data, source="persistent_cache")
        
        # Generate new preview
        return await self._generate_preview(offset)
    
    async def _preemptive_preview(self, offset: int) -> PreviewResult:
        """Preemptive preview with predictive caching."""
        # Get standard preview first
        result = await self._standard_preview(offset)
        
        # If successful, start preemptive caching of nearby offsets
        if result.success:
            self._start_preemptive_caching(offset)
        
        return result
    
    def _start_preemptive_caching(self, base_offset: int, 
                                 window_size: int = 0x10000):
        """Start preemptive caching around the current offset."""
        # Calculate nearby offsets likely to be accessed
        step_size = 0x1000  # 4KB steps
        start_offset = max(0, base_offset - window_size // 2)
        end_offset = base_offset + window_size // 2
        
        # Submit background batch job
        self._coordinator.request_batch_preview(start_offset, end_offset, step_size)
```

### 3.2 Async Cache Population Strategy

```python
class CacheWarmingWorker(QThread):
    """Background worker for cache warming operations."""
    
    batch_completed = pyqtSignal(object)  # BatchPreviewData
    progress_updated = pyqtSignal(int, int)  # current, total
    error_occurred = pyqtSignal(str)
    
    def __init__(self, rom_path: str, start_offset: int, end_offset: int, 
                 step_size: int, parent=None):
        super().__init__(parent)
        self._rom_path = rom_path
        self._start_offset = start_offset
        self._end_offset = end_offset
        self._step_size = step_size
        self._cancelled = False
    
    def run(self):
        """Execute cache warming with efficient batch operations."""
        try:
            from core.managers.registry import get_manager_registry
            extraction_manager = get_manager_registry().get_extraction_manager()
            rom_cache = get_rom_cache()
            
            previews = {}
            total_offsets = (self._end_offset - self._start_offset) // self._step_size
            current_count = 0
            
            for offset in range(self._start_offset, self._end_offset, self._step_size):
                if self._cancelled:
                    break
                    
                # Check if already cached
                existing = rom_cache.get_preview_data(self._rom_path, offset)
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
                            rom_hash=rom_cache._get_rom_hash(self._rom_path)
                        )
                        
                        previews[offset] = preview_data
                        
                        # Save individual preview
                        rom_cache.save_preview_data(self._rom_path, offset, preview_data)
                        
                    except Exception as e:
                        logger.warning(f"Failed to generate preview for offset 0x{offset:X}: {e}")
                
                current_count += 1
                self.progress_updated.emit(current_count, total_offsets)
            
            # Save batch data
            if previews and not self._cancelled:
                batch_data = BatchPreviewData(
                    start_offset=self._start_offset,
                    end_offset=self._end_offset,
                    step_size=self._step_size,
                    previews=previews,
                    cache_strategy="full",
                    total_size_bytes=sum(len(p.tile_data) for p in previews.values()),
                    cached_at=datetime.now()
                )
                
                rom_cache.save_preview_batch(self._rom_path, batch_data)
                self.batch_completed.emit(batch_data)
                
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def cancel(self):
        """Cancel the cache warming operation."""
        self._cancelled = True
```

### 3.3 Cache Invalidation Policies

```python
class CacheInvalidationManager:
    """Manages cache invalidation policies and cleanup."""
    
    def __init__(self, rom_cache: ROMCache):
        self._rom_cache = rom_cache
        
    def invalidate_preview_cache(self, rom_path: str, 
                               offset_pattern: str = "*") -> int:
        """
        Invalidate preview cache entries matching pattern.
        
        Args:
            rom_path: ROM file path
            offset_pattern: Offset pattern (* for all, specific ranges)
            
        Returns:
            Number of entries invalidated
        """
        if not self._rom_cache.cache_enabled:
            return 0
            
        try:
            rom_hash = self._rom_cache._get_rom_hash(rom_path)
            invalidated_count = 0
            
            # Pattern matching for cache files
            if offset_pattern == "*":
                # Invalidate all preview caches for this ROM
                pattern = f"{rom_hash}_preview_*.json"
            else:
                # Specific offset or range pattern
                pattern = f"{rom_hash}_preview_{offset_pattern}.json" 
            
            # Remove matching cache files
            for cache_file in self._rom_cache.cache_dir.glob(pattern):
                try:
                    cache_file.unlink()
                    invalidated_count += 1
                except OSError:
                    pass
                    
            # Also invalidate batch caches that might contain these offsets
            batch_pattern = f"{rom_hash}_batch_*.json"
            for cache_file in self._rom_cache.cache_dir.glob(batch_pattern):
                # Check if batch overlaps with invalidation pattern
                if self._batch_overlaps_pattern(cache_file, offset_pattern):
                    try:
                        cache_file.unlink()
                        invalidated_count += 1
                    except OSError:
                        pass
            
            logger.info(f"Invalidated {invalidated_count} cache entries for pattern {offset_pattern}")
            return invalidated_count
            
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")
            return 0
    
    def cleanup_stale_caches(self, max_age_days: int = 7) -> int:
        """Clean up stale preview caches older than specified days."""
        if not self._rom_cache.cache_enabled:
            return 0
            
        try:
            cutoff_time = time.time() - (max_age_days * 24 * 3600)
            removed_count = 0
            
            # Clean preview caches
            for cache_file in self._rom_cache.cache_dir.glob("*_preview_*.json"):
                try:
                    if cache_file.stat().st_mtime < cutoff_time:
                        cache_file.unlink()
                        removed_count += 1
                except OSError:
                    pass
            
            # Clean batch caches
            for cache_file in self._rom_cache.cache_dir.glob("*_batch_*.json"):
                try:
                    if cache_file.stat().st_mtime < cutoff_time:
                        cache_file.unlink()
                        removed_count += 1
                except OSError:
                    pass
                    
            logger.info(f"Cleaned up {removed_count} stale cache entries")
            return removed_count
            
        except Exception as e:
            logger.warning(f"Cache cleanup failed: {e}")
            return 0
```

## 4. Advanced Features

### 4.1 Offset Suggestion System

```python
class OffsetSuggestionEngine:
    """Generates intelligent offset suggestions from cached data."""
    
    def __init__(self, rom_cache: ROMCache):
        self._rom_cache = rom_cache
        
    def generate_suggestions(self, rom_path: str) -> List[SuggestedOffset]:
        """Generate offset suggestions from multiple data sources."""
        suggestions = []
        
        # From cached scan results  
        suggestions.extend(self._suggestions_from_scan_results(rom_path))
        
        # From user history
        suggestions.extend(self._suggestions_from_history(rom_path))
        
        # From pattern analysis
        suggestions.extend(self._suggestions_from_patterns(rom_path))
        
        # Sort by confidence and remove duplicates
        unique_suggestions = {}
        for suggestion in suggestions:
            key = suggestion.offset
            if key not in unique_suggestions or suggestion.confidence > unique_suggestions[key].confidence:
                unique_suggestions[key] = suggestion
                
        return sorted(unique_suggestions.values(), 
                     key=lambda s: s.confidence, reverse=True)
    
    def _suggestions_from_scan_results(self, rom_path: str) -> List[SuggestedOffset]:
        """Generate suggestions from cached scan results."""
        suggestions = []
        
        # Get all cached scan results for this ROM
        scan_results = self._rom_cache.get_all_scan_results(rom_path)
        
        for scan_result in scan_results:
            for sprite in scan_result.get("found_sprites", []):
                offset = sprite.get("offset")
                if offset:
                    suggestions.append(SuggestedOffset(
                        offset=offset,
                        confidence=0.9,  # High confidence from scan results
                        reason="scan_result",
                        sprite_name=sprite.get("name"),
                        preview_available=self._has_cached_preview(rom_path, offset)
                    ))
                    
        return suggestions
    
    def _suggestions_from_history(self, rom_path: str) -> List[SuggestedOffset]:
        """Generate suggestions from user access history."""
        suggestions = []
        
        # Check preview cache for recently accessed offsets
        history_data = self._rom_cache.get_access_history(rom_path)
        
        for entry in history_data:
            suggestions.append(SuggestedOffset(
                offset=entry["offset"],
                confidence=0.7,  # Medium confidence from history
                reason="user_history", 
                last_accessed=datetime.fromisoformat(entry["last_accessed"]),
                preview_available=True  # Must be true if in history
            ))
            
        return suggestions
    
    def _suggestions_from_patterns(self, rom_path: str) -> List[SuggestedOffset]:
        """Generate suggestions from ROM pattern analysis."""
        suggestions = []
        
        # Analyze ROM structure for common sprite locations
        common_offsets = [
            0x200000,  # Common sprite data start
            0x300000,  # Secondary sprite area
            0x400000,  # Extended sprite data
        ]
        
        for offset in common_offsets:
            suggestions.append(SuggestedOffset(
                offset=offset,
                confidence=0.5,  # Lower confidence for pattern-based
                reason="pattern_match",
                preview_available=self._has_cached_preview(rom_path, offset)
            ))
            
        return suggestions
```

### 4.2 Progressive Enhancement Patterns

```python
class ProgressiveEnhancementManager:
    """Manages progressive enhancement of cached data."""
    
    def __init__(self, coordinator: CacheAwarePreviewCoordinator):
        self._coordinator = coordinator
        self._enhancement_queue = []
        self._enhancement_worker: Optional[EnhancementWorker] = None
        
    def schedule_enhancement(self, rom_path: str, offset: int, 
                           enhancement_type: str) -> None:
        """Schedule progressive enhancement for an offset."""
        enhancement_task = {
            "rom_path": rom_path,
            "offset": offset,
            "type": enhancement_type,
            "priority": self._calculate_priority(offset, enhancement_type),
            "scheduled_at": time.time()
        }
        
        self._enhancement_queue.append(enhancement_task)
        self._process_enhancement_queue()
    
    def _calculate_priority(self, offset: int, enhancement_type: str) -> int:
        """Calculate enhancement priority based on context."""
        base_priority = 0
        
        # Recent access increases priority
        if self._was_recently_accessed(offset):
            base_priority += 10
            
        # Enhancement type priorities
        if enhancement_type == "high_quality_preview":
            base_priority += 5
        elif enhancement_type == "metadata_analysis":
            base_priority += 3
        elif enhancement_type == "compression_analysis":
            base_priority += 2
            
        return base_priority
    
    def _process_enhancement_queue(self) -> None:
        """Process enhancement queue with background worker."""
        if (self._enhancement_worker is None or 
            not self._enhancement_worker.isRunning()) and self._enhancement_queue:
            
            # Sort by priority
            self._enhancement_queue.sort(key=lambda x: x["priority"], reverse=True)
            
            # Start enhancement worker
            self._enhancement_worker = EnhancementWorker(
                self._enhancement_queue[:10], parent=self)  # Process top 10
            self._enhancement_worker.enhancement_completed.connect(
                self._on_enhancement_completed)
            self._enhancement_worker.start()
            
            # Remove processed items
            self._enhancement_queue = self._enhancement_queue[10:]

class EnhancementWorker(QThread):
    """Background worker for progressive enhancements."""
    
    enhancement_completed = pyqtSignal(str, int, dict)  # rom_path, offset, enhanced_data
    
    def __init__(self, tasks: List[Dict], parent=None):
        super().__init__(parent)
        self._tasks = tasks
        
    def run(self):
        """Execute enhancement tasks."""
        rom_cache = get_rom_cache()
        
        for task in self._tasks:
            try:
                enhanced_data = self._enhance_preview_data(
                    task["rom_path"], task["offset"], task["type"])
                    
                if enhanced_data:
                    # Update cached data with enhancements
                    self._update_cached_preview(task["rom_path"], 
                                              task["offset"], enhanced_data)
                    
                    self.enhancement_completed.emit(
                        task["rom_path"], task["offset"], enhanced_data)
                        
            except Exception as e:
                logger.warning(f"Enhancement failed for offset 0x{task['offset']:X}: {e}")
    
    def _enhance_preview_data(self, rom_path: str, offset: int, 
                            enhancement_type: str) -> Dict[str, Any]:
        """Perform specific enhancement on preview data."""
        if enhancement_type == "high_quality_preview":
            return self._generate_high_quality_preview(rom_path, offset)
        elif enhancement_type == "metadata_analysis":
            return self._analyze_sprite_metadata(rom_path, offset)
        elif enhancement_type == "compression_analysis":
            return self._analyze_compression_info(rom_path, offset)
        
        return {}
```

## 5. Implementation Guidelines

### 5.1 Thread Safety Patterns

```python
class ThreadSafeROMCacheExtensions:
    """Thread-safe extensions ensuring proper synchronization."""
    
    def __init__(self):
        self._preview_cache_lock = threading.RLock()
        self._batch_operation_lock = threading.RLock()
        self._suggestion_cache_lock = threading.RLock()
    
    def save_preview_data_threadsafe(self, rom_path: str, offset: int, 
                                   preview_data: PreviewData) -> bool:
        """Thread-safe preview data saving."""
        with self._preview_cache_lock:
            return self.save_preview_data(rom_path, offset, preview_data)
    
    def get_preview_data_threadsafe(self, rom_path: str, 
                                  offset: int) -> Optional[PreviewData]:
        """Thread-safe preview data retrieval."""
        with self._preview_cache_lock:
            return self.get_preview_data(rom_path, offset)
    
    def batch_operation_threadsafe(self, operation: Callable) -> Any:
        """Execute batch operations with proper locking."""
        with self._batch_operation_lock:
            return operation()
```

### 5.2 Error Handling and Fallback Mechanisms

```python
class CacheErrorHandler:
    """Comprehensive error handling for cache operations."""
    
    @staticmethod
    def with_fallback(cache_operation: Callable, 
                     fallback_operation: Callable) -> Any:
        """Execute cache operation with fallback on failure."""
        try:
            return cache_operation()
        except CacheError as e:
            logger.warning(f"Cache operation failed, using fallback: {e}")
            return fallback_operation()
        except Exception as e:
            logger.error(f"Unexpected cache error, using fallback: {e}")
            return fallback_operation()
    
    @staticmethod
    def retry_with_backoff(operation: Callable, max_retries: int = 3) -> Any:
        """Retry cache operations with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return operation()
            except (OSError, IOError) as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 0.1 * (2 ** attempt)
                time.sleep(wait_time)
                logger.debug(f"Retrying cache operation (attempt {attempt + 1})")
```

## 6. Performance Considerations

### 6.1 Memory Management

- **Preview Cache**: 20 entries max, 2MB memory limit with LRU eviction
- **Batch Operations**: Process in chunks to prevent memory exhaustion
- **Compression**: Use zlib level 6 for balanced compression/speed 
- **Cleanup**: Automatic cleanup of stale caches every 7 days

### 6.2 I/O Optimization

- **Atomic Writes**: Use temporary files and atomic rename for cache writes
- **Concurrent Access**: Reader-writer locks for cache file access
- **Lazy Loading**: Load cache data only when needed
- **Background Operations**: Use thread pools for cache warming

### 6.3 Cache Sizing Strategy

```python
class CacheSizingStrategy:
    """Dynamic cache sizing based on available resources."""
    
    @staticmethod
    def calculate_optimal_cache_size() -> Tuple[int, float]:
        """Calculate optimal cache parameters based on system resources."""
        import psutil
        
        # Get available memory
        available_memory_mb = psutil.virtual_memory().available / 1024 / 1024
        
        # Use 0.5% of available memory for preview cache, max 10MB
        cache_memory_mb = min(available_memory_mb * 0.005, 10.0)
        
        # Calculate entry count based on average preview size (100KB)
        avg_preview_size_kb = 100
        max_entries = int((cache_memory_mb * 1024) / avg_preview_size_kb)
        
        return max_entries, cache_memory_mb
```

This comprehensive architecture provides a robust foundation for integrating ROM caching with the manual offset dialog, ensuring high performance, thread safety, and excellent user experience through intelligent caching strategies.