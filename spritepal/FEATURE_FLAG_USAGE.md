# Dialog Implementation Feature Flag

This document explains how to use the dialog implementation feature flag system to switch between the legacy DialogBase and the new composed dialog implementation.

## Overview

The feature flag system allows switching between two dialog implementations:
- **Legacy**: The original `DialogBase` class
- **Composed**: The new `DialogBaseMigrationAdapter` using composition architecture

The system defaults to **legacy** for backward compatibility and safety during migration.

## Environment Variable

The feature flag is controlled by the environment variable:
```bash
SPRITEPAL_USE_COMPOSED_DIALOGS
```

- `"0"` or unset (default): Use legacy DialogBase
- `"1"`: Use composed DialogBaseMigrationAdapter

## Usage Examples

### Command Line

```bash
# Use legacy dialogs (default)
python launch_spritepal.py

# Use composed dialogs
SPRITEPAL_USE_COMPOSED_DIALOGS=1 python launch_spritepal.py
```

### Programmatic Control

```python
from utils.dialog_feature_flags import (
    get_dialog_implementation,
    set_dialog_implementation,
    enable_composed_dialogs,
    enable_legacy_dialogs,
    is_composed_dialogs_enabled
)

# Check current implementation
current = get_dialog_implementation()  # Returns "legacy" or "composed"

# Enable composed dialogs
enable_composed_dialogs()
# Or equivalently:
set_dialog_implementation(True)

# Enable legacy dialogs  
enable_legacy_dialogs()
# Or equivalently:
set_dialog_implementation(False)

# Boolean check
if is_composed_dialogs_enabled():
    print("Using composed dialogs")
else:
    print("Using legacy dialogs")
```

### Import Behavior

The DialogBase import automatically uses the correct implementation:

```python
# This will be either legacy or composed depending on the feature flag
from ui.components.base import DialogBase

# The import remains the same - the feature flag controls which class is imported
class MyDialog(DialogBase):
    # ... your dialog implementation
```

## Testing Different Implementations

### During Development

```python
# Test with legacy dialogs
from utils.dialog_feature_flags import enable_legacy_dialogs
enable_legacy_dialogs()
# ... run tests

# Test with composed dialogs  
from utils.dialog_feature_flags import enable_composed_dialogs
enable_composed_dialogs()
# ... run tests
```

### Automated Testing

```bash
# Test legacy implementation
SPRITEPAL_USE_COMPOSED_DIALOGS=0 python -m pytest tests/

# Test composed implementation
SPRITEPAL_USE_COMPOSED_DIALOGS=1 python -m pytest tests/
```

## Migration Strategy

1. **Phase 1**: All code uses legacy (current state)
   - Feature flag defaults to legacy
   - No code changes required

2. **Phase 2**: Gradual testing of composed implementation
   - Developers can enable composed locally for testing
   - CI tests both implementations

3. **Phase 3**: Switch default to composed
   - Change default in code to composed
   - Legacy still available via flag for rollback

4. **Phase 4**: Remove legacy implementation
   - Remove feature flag system
   - Only composed implementation remains

## Rollback Strategy

If issues are discovered with the composed implementation:

1. **Immediate rollback**: Set environment variable to `"0"`
2. **Application rollback**: Change default in code back to legacy
3. **Emergency rollback**: Revert to commit before feature flag introduction

## Implementation Details

The feature flag system consists of:

- `/ui/components/base/dialog_selector.py`: Core selection logic
- `/ui/components/base/__init__.py`: Exports the selected implementation
- `/utils/dialog_feature_flags.py`: Utility functions for easy access

The system includes:
- Automatic fallback to legacy on import errors
- Logging of which implementation is loaded
- Graceful handling of missing Qt dependencies (for testing)

## Troubleshooting

### "Using legacy dialog implementation" message appears when expecting composed
- Check environment variable: `echo $SPRITEPAL_USE_COMPOSED_DIALOGS`
- Verify composed implementation is available and imports correctly

### Import errors with composed dialogs
- The system automatically falls back to legacy on import errors
- Check the logs for detailed error information
- Ensure all composed dialog dependencies are available

### Changes don't take effect
- Environment variable changes may require restarting the application
- Some module imports are cached and may need application restart