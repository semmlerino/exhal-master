# Root Cause Analysis: ROM Cache Not Integrated with Manual Offset Dialog

## Executive Summary

The manual offset dialog's preview system does not utilize the existing ROM caching infrastructure, resulting in repeated disk I/O operations during slider manipulation. This appears to be an architectural oversight rather than an intentional design decision.

## Current Architecture

### Two Separate Caching Systems

1. **PreviewCache** (Memory-only, used by manual offset dialog)
   - Location: `ui/common/preview_cache.py`
   - Type: In-memory LRU cache
   - Capacity: 20 entries or 2MB
   - Stores: Final preview data (tile_data, width, height, sprite_name)
   - Key: MD5 hash of ROM path + offset
   - Scope: Process lifetime only

2. **ROMCache** (Persistent disk cache, NOT used for previews)
   - Location: `utils/rom_cache.py`
   - Type: Disk-based JSON cache
   - Capacity: Unlimited (with expiration)
   - Stores: Sprite locations, ROM info, scan progress
   - Key: SHA-256 hash of entire ROM content
   - Scope: Persistent across sessions

### Preview Generation Workflow

```
User drags slider → SmartPreviewCoordinator → PreviewWorkerPool → PooledPreviewWorker
                                                                           ↓
                                              Preview displayed ← Read entire ROM from disk (!)
```

## Root Causes

### 1. Critical Performance Issue: Repeated ROM Reads

**Evidence**: In `ui/common/preview_worker_pool.py`, lines 103-105:
```python
# Read ROM data
try:
    with open(self.rom_path, "rb") as f:
        rom_data = f.read()  # <-- ENTIRE ROM READ FOR EACH PREVIEW!
```

**Impact**: During rapid slider movement, the system reads the entire ROM file (often 1-4MB) from disk multiple times per second.

### 2. Architectural Separation

The preview system was developed independently from the main caching infrastructure:
- Manual offset dialog uses `SmartPreviewCoordinator` with `PreviewCache`
- Main extraction uses `ExtractionManager` with `ROMCache`
- No shared caching layer between them

### 3. Missing Abstraction Layers

**What's Missing**:
1. **ROM Data Cache**: No caching of raw ROM file data in memory
2. **Decompressed Sprite Cache**: No caching of decompressed sprite data
3. **Unified Cache Interface**: No abstraction to use both memory and disk caching

**What Exists**:
- Only final preview bitmaps are cached (PreviewCache)
- Each worker reads and decompresses independently

### 4. Technical Mismatches

1. **Cache Key Incompatibility**:
   - PreviewCache: Uses ROM path + offset
   - ROMCache: Uses SHA-256 of entire ROM content
   - Integration would require key mapping

2. **Thread Model Differences**:
   - PreviewCache: Designed for real-time, thread-safe memory access
   - ROMCache: File I/O based, potential for blocking

3. **Data Format Mismatch**:
   - PreviewCache: Stores binary preview data
   - ROMCache: Stores JSON-serializable data

## Evidence This Is An Oversight

1. **ROMCache Already Provides Massive Benefits**
   - Comments mention "225x-2400x speedup"
   - Successfully used in other parts of the codebase

2. **Infrastructure Already Exists**
   - ROMCache has all necessary error handling
   - Thread-safe with proper locking
   - Could easily store decompressed sprite data

3. **Pattern Is Established**
   - `ExtractionManager` uses ROMCache for sprite locations
   - `ROMExtractor` uses ROMCache for scan progress
   - Manual offset dialog is the outlier

4. **No Documented Rationale**
   - No comments explaining why ROMCache isn't used
   - No technical barriers preventing integration
   - Appears to be parallel development oversight

## Performance Impact

### Current Behavior (Without ROM Cache)
- **Disk Reads**: ~60 per second during fast dragging (at 60 FPS)
- **Data Read**: 1-4MB × 60 = 60-240MB/second disk I/O
- **CPU Usage**: Repeated decompression of same data
- **User Experience**: Potential lag on slower storage

### Potential Behavior (With ROM Cache)
- **Disk Reads**: 1 initial read
- **Data Read**: 0 additional disk I/O during session
- **CPU Usage**: Cache decompressed sprites
- **User Experience**: Instant preview updates

## Integration Barriers

### 1. Architectural Refactoring Needed
- Preview workers need access to cached ROM data
- Need to prevent multiple workers from caching same data
- Must maintain real-time responsiveness

### 2. Memory Management
- ROM files can be large (4MB+)
- Need intelligent caching strategy
- Balance memory use vs performance

### 3. Cache Coherency
- Ensure cached data matches current ROM
- Handle ROM file changes during session
- Coordinate between memory and disk caches

## Recommendations

### Short-term (Quick Win)
1. Add ROM file caching to prevent repeated reads
2. Cache decompressed sprite data by offset
3. Share cache between preview workers

### Medium-term (Proper Integration)
1. Create unified caching interface
2. Integrate PreviewCache with ROMCache
3. Implement tiered caching (memory → disk)

### Long-term (Architecture Fix)
1. Redesign preview system to use extraction manager
2. Unify all caching under single system
3. Implement proper cache invalidation

## Conclusion

The lack of ROM caching in the manual offset dialog is a **critical performance oversight** resulting from parallel development of separate systems. The infrastructure exists to fix this issue, but requires architectural changes to integrate the two caching systems. The performance impact is significant enough to warrant immediate attention.