# ManualOffsetDialog Architecture Analysis

## Current Over-Engineered MVP Architecture

### Services Layer (The Problem)
The dialog currently uses 4 separate services in an over-engineered MVP pattern:

1. **ManualOffsetController** (230 lines)
   - Coordinates between 3 other services  
   - Emits 13+ signals for coordination
   - Creates complex signal chain prone to Qt lifecycle issues

2. **ROMDataSession** (158 lines)
   - Manages ROM data, manager references with mutex
   - Tracks current offset and found sprites
   - Forwards cache signals from extraction manager

3. **OffsetExplorationService** (235 lines)
   - Manages sprite preview/search workers
   - Handles worker lifecycle and cleanup
   - ROM operation coordination

4. **ViewStateManager** (279 lines) 
   - Window positioning, fullscreen, titles
   - **NOTE**: Positioning was already fixed, this service works well

### UI Components (These work fine)
- ManualOffsetWidget - offset controls (slider, spinbox, navigation)
- ROMMapWidget - visual ROM overview  
- ScanControlsPanel - scanning operations
- ImportExportPanel - import/export sprite data
- StatusPanel - status and progress display
- SpritePreviewWidget - live preview

## Root Causes of "Buggy and Janky" Issues

### 1. Over-Engineering Problem
- 4 services to coordinate what could be done directly in the dialog
- 13+ signals create complex chains prone to Qt lifecycle issues
- Multiple indirections make debugging difficult
- Worker management spread across services

### 2. Qt Lifecycle Issues
- Complex parent-child relationships across services
- Dialog recreation pattern using `deleteLater()` 
- "wrapped C/C++ object has been deleted" errors
- Signal connections can persist after object deletion

### 3. Dialog Recreation Pattern
```python
# Current problematic pattern in ROM extraction panel:
if self._manual_offset_dialog is not None:
    self._manual_offset_dialog.deleteLater()  # Problematic
self._manual_offset_dialog = ManualOffsetDialog(self)
```

## Key Functionality That Must Be Preserved

### Core Features
1. **ROM Data Management**: ROM path, size, manager references
2. **Offset Control**: Current offset tracking with live preview  
3. **Sprite Search**: Next/previous sprite finding with workers
4. **Preview Generation**: Live preview with workers
5. **Found Sprites**: Collection management and visualization
6. **Scanning**: Full ROM scanning capabilities
7. **Import/Export**: Sprite data persistence
8. **Window Management**: Positioning, fullscreen (already working)

### Signal Interface (for ROM extraction panel)
- `offset_changed(int)` - when offset changes
- `sprite_found(int, str)` - when sprite is applied

## Simplified Architecture Design

### Single Dialog Class Approach
Create `ManualOffsetDialogSimplified` that:

1. **Direct Business Logic**: No service layer, logic directly in dialog
2. **Consolidated Worker Management**: Direct worker creation/cleanup
3. **Simplified Signal Chains**: Direct connections instead of service coordination  
4. **Singleton Pattern**: Proper show/hide lifecycle instead of recreation
5. **Keep ViewStateManager**: Only service that works well (positioning)

### Benefits
- Eliminates 3 of 4 services (750+ lines of coordination code)
- Removes complex signal chains prone to Qt lifecycle issues
- Makes debugging straightforward with direct logic flow
- Fixes recreation pattern with singleton approach
- Maintains all existing functionality

### Migration Strategy
1. Create simplified dialog alongside existing one
2. Migrate ROM extraction panel to use singleton pattern
3. Validate all functionality preserved
4. Remove old services and unused imports
5. Update tests to use new architecture

## Implementation Plan
1. **Phase 1**: Create ManualOffsetDialogSimplified with direct logic
2. **Phase 2**: Implement singleton pattern in ROM extraction panel
3. **Phase 3**: Migrate all functionality and validate
4. **Phase 4**: Clean up old services and update imports