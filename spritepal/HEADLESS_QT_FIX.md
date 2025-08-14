# Headless Qt Widget Safety Fix

## Problem
Qt widgets were experiencing segmentation faults in headless environments (WSL2, CI/CD, Docker) when:
1. Creating `QPropertyAnimation` objects without display resources
2. Running with `QT_QPA_PLATFORM=offscreen`
3. Missing DISPLAY environment variable

### Affected Components
- `CollapsibleGroupBox._setup_animation()` - QPropertyAnimation creation
- `SimpleBrowseTab._setup_ui()` - Widget initialization  
- Manual offset dialog initialization
- Any widget using QPropertyAnimation

## Solution

### 1. Safe Animation Wrapper (`ui/utils/safe_animation.py`)
Created a `SafeAnimation` class that:
- Detects headless environments automatically
- Falls back to instant property changes when animation isn't available
- Provides the same interface as QPropertyAnimation
- Handles signal/slot connections safely

### 2. Enhanced Headless Detection
Comprehensive environment checking for:
- CI environment variables
- QT_QPA_PLATFORM=offscreen
- Missing DISPLAY on Linux/WSL
- Qt screen availability
- Screen geometry validation

### 3. Updated Components
- `CollapsibleGroupBox` now uses `SafeAnimation` instead of `QPropertyAnimation`
- Graceful fallback to non-animated behavior in headless mode
- All functionality preserved when display is available

## Testing

Run the headless safety test:
```bash
source venv/bin/activate
python test_headless_safety.py
```

Expected output:
```
All tests PASSED - widgets are safe for headless mode!
Key Achievement: No segmentation faults when creating Qt widgets
with QPropertyAnimation in headless WSL2 environment.
```

## Implementation Details

### SafeAnimation Class
```python
class SafeAnimation:
    """
    Safe wrapper for QPropertyAnimation that falls back to instant 
    changes in headless mode.
    """
    def __init__(self, target, property_name):
        # Detect headless and create real animation only if safe
        # Otherwise use instant property updates
```

### Usage Pattern
```python
# Before (crashes in headless):
self._animation = QPropertyAnimation(widget, b"maximumHeight")

# After (safe everywhere):
self._animation = SafeAnimation(widget, b"maximumHeight")
```

## Benefits
1. **No segfaults** - Widgets initialize safely in all environments
2. **Automatic detection** - No manual configuration required
3. **Graceful degradation** - Instant updates instead of animations
4. **Full compatibility** - Same API as QPropertyAnimation
5. **CI/CD ready** - Tests run in Docker, GitHub Actions, etc.

## Files Modified
- `/ui/utils/safe_animation.py` - New safe animation utility
- `/ui/common/collapsible_group_box.py` - Updated to use SafeAnimation
- `/test_headless_safety.py` - Test suite for headless safety

## Key Achievement
Successfully eliminated segmentation faults when creating Qt widgets with animations in headless WSL2 environments, while maintaining full functionality when display is available.
