# Singleton Pattern Refactoring Summary

## Overview
Refactored all global state management patterns to eliminate PLW0603 errors (using global statement) by implementing proper singleton patterns without the need for the `global` keyword.

## Approach
Instead of using module-level variables with `global` statements, implemented class-based singleton holders that encapsulate the instance management. This provides:
- No need for `global` keyword
- Better encapsulation
- Maintained thread safety where required
- Easier testing (can reset singleton state)

## Files Refactored

### 1. **core/managers/factory.py**
- Created `_DefaultFactoryHolder` class
- Maintains thread safety with `threading.Lock()`
- Functions `get_default_factory()` and `set_default_factory()` now delegate to the holder

### 2. **ui/common/error_handler.py**
- Created `_ErrorHandlerSingleton` class
- Maintains thread safety for concurrent access
- Preserved parent widget updating logic

### 3. **utils/rom_cache.py**
- Created `_ROMCacheSingleton` class
- Thread-safe with double-checked locking pattern
- Single instance of `ROMCache` across the application

### 4. **utils/settings_manager.py**
- Created `_SettingsManagerSingleton` class
- Simple singleton without thread safety (not needed)

### 5. **utils/preview_generator.py**
- Created `_PreviewGeneratorSingleton` class
- Thread-safe initialization and cleanup
- Preserved all documentation about thread safety

### 6. **utils/unified_error_handler.py**
- Created `_UnifiedErrorHandlerSingleton` class
- Thread-safe singleton pattern
- Maintained reset functionality for testing

### 7. **core/navigation/__init__.py**
- Created `_NavigationManagerSingleton` class
- Proper shutdown method to cleanup resources

### 8. **core/navigation/caching.py**
- Created `_NavigationCacheSingleton` class
- Handles cache directory parameter properly

### 9. **core/navigation/plugins.py**
- Created `_PluginManagerSingleton` class
- Manages plugin directories parameter

### 10. **tests/infrastructure/test_data_repository.py**
- Created `_TestDataRepositorySingleton` class
- Maintains cleanup functionality for tests

### 11. **tests/test_rom_cache_ui_integration_enhanced.py**
- Updated to use new singleton pattern
- Changed from accessing `_rom_cache_instance` to `_ROMCacheSingleton._instance`
- Maintained test isolation

## Pattern Template
```python
class _SingletonHolder:
    """Singleton holder for ClassName."""
    _instance: Optional[ClassName] = None
    _lock = threading.Lock()  # Only if thread safety needed
    
    @classmethod
    def get(cls, *args, **kwargs) -> ClassName:
        """Get the singleton instance."""
        # Thread-safe version:
        if cls._instance is not None:
            return cls._instance
        
        with cls._lock:
            if cls._instance is None:
                cls._instance = ClassName(*args, **kwargs)
            return cls._instance
        
        # Non-thread-safe version:
        # if cls._instance is None:
        #     cls._instance = ClassName(*args, **kwargs)
        # return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (useful for testing)."""
        with cls._lock:  # If thread-safe
            cls._instance = None

def get_instance() -> ClassName:
    """Public API to get the singleton."""
    return _SingletonHolder.get()
```

## Benefits
1. **No PLW0603 errors** - Eliminated all uses of `global` keyword
2. **Better encapsulation** - Singleton logic contained in dedicated class
3. **Maintained compatibility** - Public APIs unchanged
4. **Test-friendly** - Can reset singleton state for test isolation
5. **Thread safety preserved** - Where it was originally implemented

## Verification
All Python files in the codebase have been checked and confirmed to have no `global` statements remaining (except in markdown documentation files which are not Python code).