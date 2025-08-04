# Found Sprites Registry Refactoring

## Summary

Extracted the found sprites management logic from `ManualOffsetDialogSimplified` into a dedicated `FoundSpritesRegistry` class, following the Single Responsibility Principle and improving code organization.

## Changes Made

### 1. Created `found_sprites_registry.py`
- New centralized registry for managing discovered sprites
- Implements the `FoundSpritesRegistryProtocol` interface
- Provides thread-safe sprite collection management
- Coordinates between offset widget (storage) and ROM map (visualization)

### 2. Updated `ManualOffsetDialogSimplified`
- Added `_found_sprites_registry` instance variable
- Created `_setup_found_sprites_registry()` method to initialize the registry
- Modified `add_found_sprite()` to use the registry instead of direct delegation
- Updated `_on_sprites_imported()` to use the registry's import functionality
- Fixed import paths to use relative imports (avoiding circular dependencies)

### 3. Fixed Import Issues
- Removed `spritepal.` prefix from imports in dialog files
- Fixed circular import in `panel_factory.py` by using local import
- Updated TYPE_CHECKING imports to use relative paths

## Benefits

1. **Separation of Concerns**: Sprite management logic is now isolated in its own class
2. **Testability**: The registry can be unit tested independently
3. **Reusability**: Other components can use the registry without depending on the dialog
4. **Maintainability**: Changes to sprite management don't require modifying the dialog
5. **Thread Safety**: Centralized management ensures consistent state across threads

## Architecture

The registry follows the established pattern in SpritePal:
- Delegates storage to the offset widget (single source of truth)
- Coordinates visualization updates in the ROM map
- Emits signals for sprite collection changes
- Provides a clean API for sprite operations

## Testing

Created comprehensive unit tests in `test_found_sprites_registry.py` covering:
- Sprite addition and duplicate detection
- Sprite retrieval and querying
- Import/export functionality
- Signal emission
- ROM map synchronization

All tests pass successfully, confirming the refactoring maintains functionality while improving code structure.