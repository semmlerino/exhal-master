# SpritePal Memory Leak Profiling Guide

This guide explains how to use the comprehensive memory leak profiling system to detect, measure, and track memory leaks in SpritePal.

## Overview

The memory profiling system provides:
- **Baseline measurements** - Establish memory usage patterns
- **Dialog lifecycle profiling** - Track memory leaks during dialog open/close cycles
- **Worker thread profiling** - Monitor worker cleanup and thread leaks
- **Qt object tracking** - Monitor Qt object lifecycle and orphaned objects
- **Concrete metrics** - Quantifiable measurements for tracking improvements

## Quick Start

### 1. Install Dependencies

```bash
# Install required profiling packages
python scripts/install_memory_profiling_deps.py
```

### 2. Run Baseline Profile

```bash
# Quick baseline (30 seconds)
python run_baseline_memory_profile.py --quick

# Full baseline with critical components (2-3 minutes)
python run_baseline_memory_profile.py

# Include ROM extraction testing
python run_baseline_memory_profile.py --rom "path/to/rom.sfc"
```

### 3. Run Comprehensive Tests

```bash
# Full test suite (5-10 minutes)
python scripts/run_memory_leak_tests.py

# Custom test cycles
python scripts/run_memory_leak_tests.py --cycles 20 --operations 30
```

## Key Metrics Tracked

### Memory Leak Metrics
- **Bytes leaked per dialog open/close cycle**
- **Objects not garbage collected**
- **Growing reference counts**
- **Signal connections not cleaned up**

### Severity Levels
- **None**: < 500 KB total leaked
- **Minor**: 500 KB - 5 MB total leaked  
- **Moderate**: 5 MB - 20 MB total leaked
- **Severe**: > 20 MB total leaked

### Example Output
```
ManualOffsetDialog:
  Memory per cycle: 15.3 KB    <- Track this number
  Total leaked: 0.153 MB
  Severity: minor
  Objects leaked: 47           <- Count of leaked objects
```

## Using Individual Components

### Profile Specific Dialogs

```bash
# Test manual offset dialog with detailed output
python scripts/profile_dialog_leaks.py --dialog ManualOffsetDialog --cycles 20 --verbose

# Test advanced search dialog
python scripts/profile_dialog_leaks.py --dialog AdvancedSearchDialog --cycles 15

# List available dialogs
python scripts/profile_dialog_leaks.py --list-dialogs
```

### Custom Profiling in Code

```python
from memory_leak_profiler import MemoryLeakProfiler

# Create profiler
profiler = MemoryLeakProfiler()

# Establish baseline
baseline = profiler.establish_baseline()

# Profile dialog lifecycle
result = profiler.profile_dialog_lifecycle(
    "MyDialog", MyDialogClass, cycles=10
)

# Check results
if result.leak_detected:
    print(f"Leak detected: {result.memory_leaked_per_cycle_mb * 1000:.1f} KB per cycle")
```

## Understanding Results

### Memory Snapshots
Each test provides detailed snapshots showing:
- Process memory usage (RSS)
- Python object counts by type
- Qt object counts by type
- Thread counts
- Garbage collection statistics

### Object Leak Analysis
```
Object Deltas:
  QWidget: +5              <- 5 widgets not cleaned up
  QTimer: +2               <- 2 timers still running
  SpritePreviewWidget: +1  <- 1 preview widget leaked
```

### Qt Object Tracking
```
Orphaned Objects (no parent, age > 30s):
  QPushButton: 45.2s old   <- Button without parent for 45 seconds
  QVBoxLayout: 32.1s old   <- Layout not properly destroyed
```

## Leak Patterns to Look For

### 1. Dialog Cleanup Issues
- **Pattern**: Objects increase after each dialog close
- **Cause**: Missing `deleteLater()` calls or parent relationships
- **Fix**: Ensure proper Qt object hierarchy and cleanup

### 2. Signal Connection Leaks  
- **Pattern**: Connection counts grow over time
- **Cause**: Signals connected but not disconnected
- **Fix**: Use `QObject.destroyed` signal or manual disconnection

### 3. Worker Thread Leaks
- **Pattern**: Thread count increases, workers not terminated
- **Cause**: `quit()` and `wait()` not called properly
- **Fix**: Implement proper worker cleanup in try/finally blocks

### 4. Cache/Reference Cycles
- **Pattern**: Specific object types accumulate
- **Cause**: Circular references preventing garbage collection
- **Fix**: Use weak references or manual cleanup

## Tracking Improvements

### Before Fixing Leaks
```bash
# Run baseline to establish metrics
python run_baseline_memory_profile.py --output before_fixes.txt
```

### After Implementing Fixes  
```bash
# Run same tests to measure improvement
python run_baseline_memory_profile.py --output after_fixes.txt

# Compare results
diff before_fixes.txt after_fixes.txt
```

### Target Improvements
- **Dialog cycles**: < 1 KB per cycle (currently: varies by dialog)
- **Worker operations**: < 0.5 KB per operation
- **No leaked workers**: 0 workers should remain after cleanup
- **Qt orphaned objects**: < 5 objects after test completion

## Integration with CI/CD

### Regression Testing
```bash
# Add to CI pipeline
python run_baseline_memory_profile.py --quick
if [ $? -eq 2 ]; then
    echo "CRITICAL: Severe memory leaks detected!"
    exit 1
fi
```

### Performance Monitoring
```bash
# Weekly memory leak report
python scripts/run_memory_leak_tests.py --output weekly_leak_report_$(date +%Y%m%d).txt
```

## Advanced Usage

### Custom Dialog Testing
```python
# Test your own dialog
from memory_leak_profiler import MemoryLeakProfiler
from my_module import MyCustomDialog

profiler = MemoryLeakProfiler()
profiler.establish_baseline()

result = profiler.profile_dialog_lifecycle(
    "MyCustomDialog", 
    MyCustomDialog, 
    cycles=15,
    custom_param="value"  # Pass constructor parameters
)
```

### Memory Timeline Analysis
```python
# Track memory over time during operations
snapshots = []
for i in range(10):
    # Perform operation
    do_operation()
    
    # Take snapshot
    snapshot = profiler.take_memory_snapshot(f"operation_{i}")
    snapshots.append(snapshot)

# Analyze memory growth pattern
for i, snapshot in enumerate(snapshots[1:], 1):
    delta = snapshot.memory_delta_mb(snapshots[0])
    print(f"Operation {i}: {delta:.2f} MB delta")
```

## Troubleshooting

### Common Issues

1. **"objgraph not available"**
   ```bash
   pip install objgraph
   ```

2. **"No display detected"**
   - Automatically handled with `QT_QPA_PLATFORM=offscreen`
   - Tests run in headless mode

3. **"Import errors"**
   - Ensure virtual environment is activated
   - Check that all SpritePal dependencies are installed

4. **"Tests fail to start dialogs"**
   - Some dialogs may require specific parameters
   - Check dialog constructor requirements

### Getting Help

1. **Check logs**: Profiler outputs detailed logging information
2. **Verbose mode**: Use `--verbose` flag for detailed cycle information  
3. **Individual testing**: Test components separately to isolate issues
4. **Baseline comparison**: Always compare against known-good baseline

## Files Overview

- `memory_leak_profiler.py` - Core profiling engine
- `run_baseline_memory_profile.py` - Quick baseline measurements
- `scripts/run_memory_leak_tests.py` - Comprehensive test suite
- `scripts/profile_dialog_leaks.py` - Individual dialog testing
- `scripts/install_memory_profiling_deps.py` - Dependency installer

## Expected Results

Based on initial analysis, expect to find:
- **Minor leaks** in dialog open/close cycles (1-20 KB per cycle)
- **Signal connection issues** where connections aren't cleaned up
- **Qt object orphaning** from improper parent-child relationships
- **Worker thread cleanup issues** where threads aren't properly terminated

The goal is to reduce per-cycle leaks to < 1 KB and eliminate severe leaks entirely.