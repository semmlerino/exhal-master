# ROM Offset Timing Debug Guide

This guide provides a systematic approach to debugging timing-sensitive ROM offset detection issues where Lua script DMA monitoring shows different results compared to SpritePal's static ROM analysis.

## Problem Overview

**Scenario**: Lua scripts monitoring DMA transfers during gameplay detect sprites at specific ROM offsets, but SpritePal's static analysis shows different or no sprite data at those same offsets.

**Root Causes**: This discrepancy typically results from:
1. **Timing-sensitive data access** - Different data states during live vs static access
2. **Multi-layered caching** - Stale cached data vs live ROM state
3. **Memory banking** - SNES address mapping changes during gameplay
4. **HAL compression state** - Partially loaded or streamed compressed data
5. **Race conditions** - Threading issues affecting data consistency

## Diagnostic Tools

### 1. General ROM Timing Profiler
```bash
python rom_offset_timing_profiler.py <rom_path> <offset>
```

**Purpose**: Analyzes general ROM access timing patterns and identifies potential discrepancies between different access methods.

**Example Usage**:
```bash
# Analyze timing issues at offset where Lua script detected sprite
python rom_offset_timing_profiler.py kirby_dreamland_3.smc 0x50000

# Save detailed results for analysis
python rom_offset_timing_profiler.py smw.sfc 0xC0000 --output timing_analysis.json
```

### 2. SpritePal-Specific Analyzer  
```bash
python spritepal_timing_analyzer.py <rom_path> <offset>
```

**Purpose**: Analyzes SpritePal's specific ROM access components (caching, mmap, HAL compression) for timing-related issues.

**Example Usage**:
```bash
# Analyze SpritePal's components for timing issues
python spritepal_timing_analyzer.py kirby_dreamland_3.smc 0x50000

# Compare with Lua script findings
python spritepal_timing_analyzer.py rom.smc 0x51000 --output spritepal_analysis.json
```

## Systematic Debugging Process

### Step 1: Baseline Data Comparison
1. **Extract data from Lua script** - Get exact byte sequences DMA monitoring detected
2. **Extract same data from SpritePal** - Use Manual Offset Dialog at same offset
3. **Compare byte-by-byte** - Identify specific differences

```bash
# Use profilers to get data hashes for comparison
python rom_offset_timing_profiler.py rom.smc 0x50000 | grep "sample_hash"
```

### Step 2: Timing Analysis
Run comprehensive timing analysis to identify access pattern differences:

```bash
# Full timing analysis with verbose output
python rom_offset_timing_profiler.py rom.smc 0x50000 --verbose
python spritepal_timing_analyzer.py rom.smc 0x50000
```

**Key Metrics to Analyze**:
- **Data consistency across access methods** - Should be 100%
- **Cache hit rates** - High rates might indicate stale data
- **Threading consistency** - Race conditions affect data integrity
- **HAL decompression timing** - Variance indicates potential issues

### Step 3: Cache Invalidation Test
1. **Clear all SpritePal caches**
2. **Re-analyze the problematic offset**
3. **Compare results with fresh cache state**

```python
# Manual cache clearing (add to test script)
from utils.rom_cache import get_rom_cache
from core.async_rom_cache import AsyncROMCache

rom_cache = get_rom_cache()
if rom_cache:
    rom_cache.clear_all_cache()

async_cache = AsyncROMCache()
async_cache.clear_memory_cache()
```

### Step 4: Memory Banking Simulation
SNES uses different memory banking modes that could affect address interpretation:

```python
# Address mapping simulation
def snes_address_to_rom_offset(snes_addr, rom_mode="LoROM"):
    """Convert SNES address to ROM file offset considering banking."""
    if rom_mode == "LoROM":
        bank = (snes_addr >> 16) & 0xFF
        addr = snes_addr & 0xFFFF
        if addr >= 0x8000:
            return ((bank & 0x7F) << 15) + (addr - 0x8000)
    elif rom_mode == "HiROM":
        return snes_addr & 0x3FFFFF
    return snes_addr

# Test different interpretations of Lua script addresses
lua_detected_addr = 0x85000  # Example SNES address from Lua
rom_offset_lorom = snes_address_to_rom_offset(lua_detected_addr, "LoROM")
rom_offset_hirom = snes_address_to_rom_offset(lua_detected_addr, "HiROM")

print(f"Lua SNES Address: 0x{lua_detected_addr:06X}")
print(f"LoROM Offset: 0x{rom_offset_lorom:06X}")
print(f"HiROM Offset: 0x{rom_offset_hirom:06X}")
```

### Step 5: HAL Compression State Analysis
HAL compressed data might be in different states during live vs static access:

```python
# HAL compression state testing
from core.hal_compression import HALCompression

hal = HALCompression()

# Test if data is compressed at offset
def test_hal_compression_state(rom_path, offset):
    try:
        # Attempt decompression
        decompressed = hal.decompress_from_rom(rom_path, offset)
        print(f"Offset 0x{offset:06X}: HAL compressed, size: {len(decompressed)} bytes")
        return True, decompressed
    except:
        # Not compressed or invalid
        print(f"Offset 0x{offset:06X}: Not HAL compressed or invalid")
        return False, None

# Test the problematic offset
is_compressed, data = test_hal_compression_state("rom.smc", 0x50000)
```

## Common Timing Issues and Solutions

### Issue 1: Stale Cache Data
**Symptoms**: 
- SpritePal shows old/different data compared to Lua script
- Data consistency percentage < 100% in timing analysis

**Solution**:
```python
# Add cache invalidation to Manual Offset Dialog
def invalidate_caches_before_analysis(self):
    """Call before critical sprite detection operations."""
    if hasattr(self, 'rom_cache_component'):
        self.rom_cache_component.clear_cache()
    if hasattr(self, 'async_cache'):
        self.async_cache.clear_memory_cache()
```

### Issue 2: Memory Mapping Inconsistencies  
**Symptoms**:
- Different data hashes between mmap and direct file access
- Timing variance > 50ms in access methods

**Solution**:
```python
# Use direct file access for critical operations
def bypass_mmap_for_critical_read(rom_path, offset, size):
    """Bypass memory mapping for consistent reads."""
    with open(rom_path, 'rb') as f:
        f.seek(offset)
        return f.read(size)
```

### Issue 3: Threading Race Conditions
**Symptoms**:
- Async cache success rate < 95%
- Data inconsistency in concurrent access tests

**Solution**:
```python
# Add synchronization for critical reads
import threading

class ThreadSafeROMReader:
    def __init__(self, rom_path):
        self.rom_path = rom_path
        self._read_lock = threading.RLock()
    
    def critical_read(self, offset, size):
        """Thread-safe critical read operation."""
        with self._read_lock:
            return self._read_direct(offset, size)
```

### Issue 4: HAL Compression Timing
**Symptoms**:
- HAL decompression timing variance > 50ms
- Inconsistent decompression results

**Solution**:
```python
# Implement HAL compression retry with timeout
def robust_hal_decompress(rom_path, offset, max_retries=3, timeout_ms=1000):
    """Robust HAL decompression with retry logic."""
    for attempt in range(max_retries):
        try:
            start_time = time.perf_counter()
            result = hal.decompress_from_rom(rom_path, offset)
            elapsed = (time.perf_counter() - start_time) * 1000
            
            if elapsed < timeout_ms:
                return result
            else:
                print(f"HAL decompression took {elapsed:.1f}ms (timeout: {timeout_ms}ms)")
                
        except Exception as e:
            print(f"HAL decompression attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.1)  # Brief delay before retry
    
    return None
```

## Performance Optimization Recommendations

### 1. Minimize Cache Layers During Debug
```python
# Disable caching for debugging
def debug_mode_rom_access(rom_path, offset, size):
    """Direct ROM access for debugging - bypasses all caches."""
    with open(rom_path, 'rb') as f:
        f.seek(offset)
        data = f.read(size)
    
    # Log access for comparison with Lua script
    print(f"DEBUG: Direct read at 0x{offset:06X}, size: {size}, hash: {hashlib.md5(data).hexdigest()}")
    return data
```

### 2. Add ROM Access Logging
```python
# Add to Manual Offset Dialog for DMA comparison
class ROMAccessLogger:
    def __init__(self):
        self.access_log = []
    
    def log_access(self, method, offset, size, data_hash, timing_ms):
        self.access_log.append({
            "timestamp": time.time(),
            "method": method,
            "offset": f"0x{offset:06X}",
            "size": size,
            "data_hash": data_hash,
            "timing_ms": timing_ms
        })
    
    def compare_with_lua_log(self, lua_log_file):
        """Compare ROM access patterns with Lua script log."""
        # Implementation for log comparison
        pass
```

### 3. Real-time Data Consistency Verification
```python
# Add to sprite detection pipeline
def verify_data_consistency(rom_path, offset, size):
    """Verify data consistency across different access methods."""
    methods = {
        "direct": lambda: direct_file_read(rom_path, offset, size),
        "mmap": lambda: mmap_read(rom_path, offset, size),
        "cached": lambda: cached_read(rom_path, offset, size)
    }
    
    results = {}
    for method_name, method_func in methods.items():
        try:
            data = method_func()
            results[method_name] = hashlib.md5(data).hexdigest()
        except Exception as e:
            results[method_name] = f"ERROR: {e}"
    
    # Check consistency
    unique_hashes = set(v for v in results.values() if not v.startswith("ERROR"))
    consistent = len(unique_hashes) == 1
    
    if not consistent:
        print(f"WARNING: Data inconsistency at offset 0x{offset:06X}:")
        for method, hash_or_error in results.items():
            print(f"  {method}: {hash_or_error}")
    
    return consistent, results
```

## Integration with SpritePal

### Adding Debug Mode to Manual Offset Dialog
```python
# Add to ui/dialogs/manual_offset_unified_integrated.py
class ManualOffsetDialog:
    def __init__(self, ...):
        # ... existing code ...
        self.debug_mode = False
        self.rom_access_logger = ROMAccessLogger()
    
    def enable_debug_mode(self):
        """Enable debug mode for timing analysis."""
        self.debug_mode = True
        print("Manual Offset Dialog: Debug mode enabled")
        
        # Clear all caches
        if hasattr(self, 'rom_cache_component'):
            self.rom_cache_component.clear_cache()
    
    def debug_sprite_at_offset(self, offset):
        """Debug sprite detection at specific offset."""
        if not self.debug_mode:
            return
        
        rom_path = self.current_rom_path
        
        # Verify data consistency
        consistent, results = verify_data_consistency(rom_path, offset, 0x1000)
        
        if not consistent:
            print(f"TIMING ISSUE: Data inconsistency detected at 0x{offset:06X}")
            
        # Log access for comparison
        start_time = time.perf_counter()
        data = debug_mode_rom_access(rom_path, offset, 0x1000)
        elapsed = (time.perf_counter() - start_time) * 1000
        
        self.rom_access_logger.log_access("debug_direct", offset, 0x1000, 
                                        hashlib.md5(data).hexdigest(), elapsed)
```

## Expected Results and Next Steps

After running the diagnostic tools and implementing the debugging approach:

1. **Identify root cause** - Determine whether the issue is caching, threading, HAL compression, or memory banking
2. **Implement targeted fix** - Apply specific solution based on root cause analysis
3. **Verify fix** - Re-run timing analysis to confirm discrepancy resolution
4. **Add monitoring** - Implement ongoing monitoring to prevent regression

The profiler tools will provide quantitative data to pinpoint the exact timing-related factors causing the discrepancy between live DMA monitoring and static ROM analysis, enabling targeted performance optimizations and bug fixes.
