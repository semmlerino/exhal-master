# Smart Preview System Design Guide

## Overview

The Smart Preview System provides real-time, 60 FPS preview updates during slider scrubbing in the manual offset dialog. This solution eliminates the laggy 100ms debounce delay and excessive thread creation that plagued the previous implementation.

## Architecture

### Multi-Tier Strategy

The system implements three distinct tiers for different interaction phases:

#### Tier 1: Immediate Visual Feedback (0-16ms)
- **Purpose**: Instant UI updates during dragging
- **Components**: Position labels, hex values, progress indicators
- **Implementation**: Direct UI updates via callback functions
- **Performance**: 60 FPS smooth feedback

#### Tier 2: Fast Preview Updates (50ms debounce)
- **Purpose**: Responsive previews during active dragging
- **Components**: Cached preview display, worker pool
- **Implementation**: LRU cache with worker thread reuse
- **Performance**: Sub-100ms preview updates

#### Tier 3: High-Quality Preview (200ms debounce)
- **Purpose**: Full-quality previews after positioning
- **Components**: Complete sprite validation, history updates
- **Implementation**: Enhanced worker with full decompression
- **Performance**: Quality over speed for final positioning

## Core Components

### 1. SmartPreviewCoordinator

**Location**: `ui/common/smart_preview_coordinator.py`

**Responsibilities**:
- Coordinate between UI events and preview generation
- Manage timing strategies based on drag state
- Handle request cancellation and priority queuing
- Integrate with existing Qt signal/slot patterns

**Key Features**:
```python
class SmartPreviewCoordinator(QObject):
    # Drag state management
    _drag_state: DragState  # IDLE, DRAGGING, SETTLING
    
    # Timing configuration
    _drag_debounce_ms = 50      # Fast updates during drag
    _release_debounce_ms = 200  # Quality updates after release
    _ui_update_ms = 16          # 60 FPS UI updates
    
    # Signal coordination
    def connect_slider(self, slider: QSlider)
    def request_preview(self, offset: int, priority: int = 0)
```

### 2. PreviewWorkerPool

**Location**: `ui/common/preview_worker_pool.py`

**Responsibilities**:
- Manage reusable worker threads (1-2 workers)
- Handle request queuing and cancellation
- Implement priority-based processing
- Auto-scale workers based on demand

**Key Features**:
```python
class PreviewWorkerPool(QObject):
    # Worker management
    _max_workers = 2
    _available_workers: queue.Queue
    _active_workers: set
    
    # Request handling
    def submit_request(self, request, extractor)
    def _cancel_lower_priority_requests(self, priority: int)
```

### 3. PreviewCache

**Location**: `ui/common/preview_cache.py`

**Responsibilities**:
- LRU cache for instant preview display
- Memory-aware eviction policies
- Thread-safe operations
- Efficient key generation

**Key Features**:
```python
class PreviewCache:
    # Cache configuration
    max_size = 20           # ~20 preview entries
    max_memory_mb = 2.0     # 2MB memory limit
    
    # Cache operations
    def get(self, key: str) -> Optional[PreviewData]
    def put(self, key: str, data: PreviewData)
```

## Qt Signal Handling

### Slider Signal Strategy

The system leverages Qt's built-in slider signals for optimal user experience:

```python
# Drag detection signals
slider.sliderPressed.connect(self._on_drag_start)     # User starts dragging
slider.sliderMoved.connect(self._on_drag_move)        # Dragging in progress  
slider.sliderReleased.connect(self._on_drag_end)      # User stops dragging
slider.valueChanged.connect(self._on_value_changed)   # Programmatic changes
```

### State Machine

```python
class DragState(Enum):
    IDLE = auto()         # Normal operations, no dragging
    DRAGGING = auto()     # Actively dragging slider
    SETTLING = auto()     # Just released, waiting for final update
```

### Timing Behavior

| State | UI Updates | Preview Strategy | Debounce |
|-------|-----------|------------------|----------|
| IDLE | Immediate | High-quality | 200ms |
| DRAGGING | 16ms (60 FPS) | Cached + Fast | 50ms |
| SETTLING | Immediate | High-quality | 200ms |

## Performance Optimizations

### Thread Reuse Pattern

**Problem**: Previous implementation created new worker threads for each update
**Solution**: Pool of 1-2 reusable workers with request queuing

```python
# Old approach (inefficient)
worker = SpritePreviewWorker(...)
worker.start()  # New thread for each request

# New approach (efficient)
pool.submit_request(request, extractor)  # Reuses existing workers
```

### Request Cancellation

**Problem**: Stale requests could overwrite newer previews
**Solution**: Atomic cancellation with request IDs

```python
class PreviewRequest:
    request_id: int        # Unique identifier
    cancelled: bool        # Atomic cancellation flag
    priority: int          # Higher = more important
```

### Memory Management

**Problem**: Unlimited memory usage for preview caching
**Solution**: LRU cache with size and memory limits

```python
# Cache eviction policies
while len(cache) > max_size or memory_usage > max_memory:
    evict_oldest_entry()
```

## Integration with Existing Code

### Dialog Integration

The smart preview system integrates seamlessly with the existing `UnifiedManualOffsetDialog`:

```python
class UnifiedManualOffsetDialog(DialogBase):
    def _setup_smart_preview_coordinator(self):
        self._smart_preview_coordinator = SmartPreviewCoordinator(self)
        
        # Connect to preview signals
        self._smart_preview_coordinator.preview_ready.connect(self._on_smart_preview_ready)
        self._smart_preview_coordinator.preview_cached.connect(self._on_smart_preview_cached)
        self._smart_preview_coordinator.preview_error.connect(self._on_smart_preview_error)
        
        # Setup ROM data provider
        self._smart_preview_coordinator.set_rom_data_provider(self._get_rom_data_for_preview)
```

### Browse Tab Enhancement

The `SimpleBrowseTab` connects the smart coordinator to the slider:

```python
def connect_smart_preview_coordinator(self, coordinator):
    self._smart_preview_coordinator = coordinator
    if coordinator:
        # Connect coordinator to slider for drag detection
        coordinator.connect_slider(self.position_slider)
        
        # Setup UI update callback for immediate feedback
        coordinator.set_ui_update_callback(self._on_smart_ui_update)
```

## Configuration

### Timing Constants

Located in `ui/common/timing_constants.py`:

```python
# Animation and UI update timings
REFRESH_RATE_60FPS = 16              # 16ms for ~60fps updates
UI_UPDATE_INTERVAL = 50              # 50ms for UI updates during operations
ANIMATION_DEBOUNCE_DELAY = 16        # 16ms debounce delay for UI changes

# Smart preview specific (new)
DRAG_PREVIEW_DEBOUNCE = 50           # 50ms for drag updates
RELEASE_PREVIEW_DEBOUNCE = 200       # 200ms for release updates
```

### Performance Tuning

Key parameters for optimization:

```python
PREVIEW_CACHE_SIZE = 20              # Number of cached previews
PREVIEW_CACHE_MEMORY_MB = 2.0        # Memory limit for cache
MAX_PREVIEW_WORKERS = 2              # Worker pool size
WORKER_IDLE_TIMEOUT_MS = 30000       # Auto-cleanup idle workers
```

## Implementation Phases

### Phase 1: Core Infrastructure
1. ✅ Create `SmartPreviewCoordinator`
2. ✅ Create `PreviewWorkerPool`
3. ✅ Create `PreviewCache`
4. ✅ Add timing constants

### Phase 2: Dialog Integration
1. ✅ Modify `UnifiedManualOffsetDialog`
2. ✅ Enhance `SimpleBrowseTab`
3. ✅ Connect signal flows
4. ✅ Add cleanup handling

### Phase 3: Testing & Validation
1. Create comprehensive test suite
2. Performance benchmarking
3. Memory usage validation
4. User experience testing

### Phase 4: Legacy Cleanup
1. Remove old preview timer logic
2. Deprecate `MinimalSignalCoordinator` 
3. Update documentation
4. Performance monitoring

## Testing Strategy

### Unit Tests

```python
class TestSmartPreviewCoordinator:
    def test_drag_state_transitions(self):
        # Test IDLE -> DRAGGING -> SETTLING -> IDLE
        
    def test_timing_strategies(self):
        # Test different debounce delays for each state
        
    def test_request_cancellation(self):
        # Test stale request cancellation
```

### Integration Tests

```python
class TestPreviewIntegration:
    def test_slider_drag_performance(self):
        # Measure actual FPS during dragging
        
    def test_cache_hit_ratio(self):
        # Validate cache effectiveness
        
    def test_memory_usage(self):
        # Ensure memory limits are respected
```

### Performance Benchmarks

```python
def benchmark_preview_updates():
    # Target: <50ms for cached previews
    # Target: <200ms for high-quality previews
    # Target: 60 FPS UI updates during dragging
```

## Troubleshooting

### Common Issues

1. **Laggy UI Updates**
   - Check UI update callback is connected
   - Verify 16ms timer interval
   - Ensure no blocking operations in UI thread

2. **Memory Growth**
   - Check cache eviction policies
   - Monitor cache statistics
   - Verify preview data cleanup

3. **Worker Thread Issues**
   - Check request cancellation logic
   - Verify worker pool cleanup
   - Monitor thread lifecycle

### Debug Tools

```python
# Cache statistics
stats = coordinator._cache.get_stats()
print(f"Cache hit ratio: {stats['hits']}/{stats['requests']}")

# Worker pool status
print(f"Active workers: {len(pool._active_workers)}")
print(f"Available workers: {pool._available_workers.qsize()}")

# Timing measurements
with performance_timer("preview_generation"):
    coordinator.request_preview(offset)
```

## Future Enhancements

### Adaptive Quality

Dynamically adjust preview quality based on drag speed:
- Fast dragging: Lower quality, higher speed
- Slow dragging: Higher quality, more detail

### Predictive Caching

Pre-generate previews for likely next positions:
- Cache previews around current position
- Predict user drag patterns
- Background preview generation

### GPU Acceleration

Offload sprite decompression to GPU:
- OpenGL-based decompression
- Parallel tile processing
- Hardware-accelerated preview generation

This design provides a solid foundation for smooth, responsive preview updates while maintaining code quality and following established Qt patterns.