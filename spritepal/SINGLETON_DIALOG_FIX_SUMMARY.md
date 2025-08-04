# Manual Offset Dialog Singleton Fix

## Problem
The user was experiencing duplicate sliders in the manual offset dialog, suggesting multiple dialog instances were being created instead of reusing a single instance.

## Root Cause Analysis
The original implementation used a per-panel singleton pattern where each `ROMExtractionPanel` stored its own `_manual_offset_dialog` reference. This could lead to:
1. Multiple panels creating separate dialog instances
2. Dialog instances not being properly cleaned up when closed
3. Memory leaks from uncollected dialog objects
4. UI inconsistencies with multiple dialogs showing

## Solution Implementation

### 1. Application-Wide Singleton Pattern
Created `ManualOffsetDialogSingleton` class that ensures only ONE dialog instance exists across the entire application:

```python
class ManualOffsetDialogSingleton:
    """
    Application-wide singleton for manual offset dialog.
    Ensures only one dialog instance exists across the entire application.
    """
    _instance: 'UnifiedManualOffsetDialog | None' = None
    _creator_panel: 'ROMExtractionPanel | None' = None
```

### 2. Proper Lifecycle Management
- **Creation**: Dialog is created only when needed
- **Reuse**: Existing dialog is reused when requested again
- **Cleanup**: Dialog is properly destroyed when closed
- **Signal Management**: Signals are connected only once and reused

### 3. Enhanced Logging
Added comprehensive debug logging to track:
- Dialog creation with unique debug IDs
- Dialog show/hide events
- Dialog destruction
- Singleton state changes

### 4. Thread-Safe Access
- Uses Qt's `deleteLater()` for proper cleanup
- Proper signal connections that prevent duplicates
- Mutex protection for manager references in dialog

## Key Changes

### In `ui/rom_extraction_panel.py`:

1. **Added singleton manager class**:
   ```python
   class ManualOffsetDialogSingleton:
       @classmethod
       def get_dialog(cls, creator_panel) -> 'UnifiedManualOffsetDialog':
           # Returns existing instance or creates new one
   ```

2. **Updated dialog opening method**:
   ```python
   def _open_manual_offset_dialog(self):
       # Get or create singleton dialog instance
       dialog = ManualOffsetDialogSingleton.get_dialog(self)
       # Connect signals only once
       # Show or bring to front
   ```

3. **Updated all dialog references** to use singleton methods

### In `ui/dialogs/manual_offset_unified_integrated.py`:

1. **Added debug tracking**:
   ```python
   def __init__(self, parent: QWidget | None = None) -> None:
       logger.info(f"Creating UnifiedManualOffsetDialog instance")
       self._debug_id = f"dialog_{int(time.time()*1000)}"
   ```

2. **Enhanced event logging**:
   - Show/hide events logged with debug ID
   - Close events logged
   - Destructor logs when dialog is destroyed

## Benefits

1. **Single Instance**: Only one dialog can exist at a time
2. **Memory Efficient**: Proper cleanup prevents memory leaks
3. **Consistent UI**: Users can't accidentally open multiple dialogs
4. **Better Resource Management**: Dialog reuse reduces creation overhead
5. **Debug Visibility**: Comprehensive logging helps identify issues

## Testing

Created `test_singleton_dialog.py` to verify:
- Only one dialog instance is created
- Dialog is reused when opened from different panels
- Proper cleanup when dialog is closed
- Signal connections work correctly

## Usage

The fix is transparent to users. The dialog behavior remains the same:
- Click "Open Manual Offset Control" button
- Dialog opens (or brings existing one to front)
- Close dialog normally
- Next open reuses same instance if still in memory, or creates new one

## Verification Commands

To test the fix:

```bash
# Run the singleton test
python3 test_singleton_dialog.py

# Run SpritePal normally and verify no duplicate sliders
python3 launch_spritepal.py

# Check logs for singleton behavior
grep -E "(Creating|showing|hiding|destroying)" spritepal.log
```

## Monitoring

The fix includes extensive logging. Look for these log messages:
- `Creating UnifiedManualOffsetDialog instance` - New dialog created
- `Reusing existing ManualOffsetDialog singleton instance` - Singleton reused
- `Dialog {id} showing/hiding` - Dialog visibility changes  
- `Dialog {id} being destroyed` - Dialog cleanup

This ensures the duplicate slider issue is resolved while maintaining proper resource management and providing clear debugging information.