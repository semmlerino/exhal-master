# Biggest Refactoring Priority: Extract Business Logic from UI Components

After analyzing the SpritePal codebase, the **biggest refactoring priority** is to **extract business logic from UI components into dedicated manager classes**. This aligns with the pending "Phase 4: Extract business logic to managers" task.

## Key Findings

### 1. Significant UI/Business Logic Coupling
- `ui/rom_extraction_panel.py` (901 lines) contains extensive ROM handling logic mixed with UI code
- `ui/main_window.py` (758 lines) has extraction logic, file handling, and state management
- `core/controller.py` (751 lines) is doing too much - extraction, injection, preview updates, and file operations

### 2. Missing Business Logic Managers
- No dedicated extraction manager (logic scattered between UI and controller)
- No injection manager (handled directly in controller)
- No session/state manager (mixed into UI components)
- No file operation manager (spread across multiple components)

### 3. Current Issues
- Testing is difficult due to tight coupling
- Business rules are duplicated across UI components
- State management is fragmented
- Error handling is inconsistent

## Recommended Refactoring Approach

### 1. Create Dedicated Manager Classes
- `ExtractionManager` - Handle all extraction workflows (VRAM/ROM)
- `InjectionManager` - Manage injection operations
- `SessionManager` - Centralize session state and persistence
- `FileOperationManager` - Handle all file I/O operations
- `PreviewManager` - Manage preview generation and updates

### 2. Extract Business Logic from UI
- Move ROM sprite scanning logic from `rom_extraction_panel.py` to `ExtractionManager`
- Extract file validation and path resolution from UI to `FileOperationManager`
- Move extraction parameter validation to business layer
- Centralize error handling in managers

### 3. Improve Separation of Concerns
- UI components should only handle presentation and user input
- Business managers handle all logic and state
- Controller becomes a thin coordination layer
- Clear data flow: UI → Controller → Managers → Core

## Why This is the Top Priority

1. **Testing Impact**: Current coupling makes unit testing extremely difficult
2. **Maintenance**: Business logic changes require modifying UI files
3. **Reusability**: Logic trapped in UI can't be reused elsewhere
4. **Type Safety**: Mixed concerns make type annotations harder
5. **Future Features**: Clean architecture needed for planned enhancements

## Implementation Plan

1. Start with `ExtractionManager` to consolidate extraction logic
2. Create `SessionManager` to centralize state management
3. Refactor `rom_extraction_panel.py` to use managers
4. Update controller to coordinate managers instead of implementing logic
5. Add comprehensive type annotations to new managers
6. Write unit tests for extracted business logic

This refactoring will significantly improve code quality, testability, and maintainability while setting a solid foundation for future development.