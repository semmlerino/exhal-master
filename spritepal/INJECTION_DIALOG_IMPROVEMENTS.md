# Injection Dialog Improvements

## Summary
Fixed critical layout issues in the injection dialog to match the improved patterns from other dialogs, providing better usability and a more modern interface.

## Changes Implemented

### 1. Dialog Size Improvements
- **Increased default size**: From 900x600 to **1400x900** pixels
- **Increased minimum size**: From 900x600 to **1200x800** pixels
- **Removed fixed size constraint**: Dialog is now resizable by the user

### 2. Layout Optimizations
- **Fixed splitter ratio**: Changed from 50/50 to **30/70** (controls/preview)
  - Controls panel: 30% width (400px)
  - Preview panel: 70% width (1000px)
- **Moved sprite file selector**: Relocated from duplicated instances in each tab to a single shared instance at dialog level
- **Improved tab structure**: Sprite selector now appears above the tab content, eliminating duplication

### 3. Keyboard Shortcuts
- **Ctrl+S**: Apply/Accept changes
- **Escape**: Cancel dialog
- **Ctrl+Tab**: Next tab
- **Ctrl+Shift+Tab**: Previous tab

### 4. Tooltips Added
All interactive widgets now have informative tooltips:
- **File selectors**: Explain what each file is used for
- **Input fields**: Describe expected format and purpose
- **Buttons**: Show keyboard shortcuts
- **Combo boxes**: Explain selection options
- **Checkboxes**: Clarify effects of options

### 5. Code Quality Improvements
- Added proper imports for keyboard shortcuts (`QKeySequence`, `QShortcut`)
- Added `QDialogButtonBox` import for button text customization
- Implemented helper methods for tab navigation
- Improved widget initialization and layout structure

## User Benefits
1. **Better space utilization**: Larger dialog provides more room for controls and preview
2. **Improved workflow**: Single sprite selector reduces confusion and clicks
3. **Faster operation**: Keyboard shortcuts enable power users to work efficiently
4. **Better discoverability**: Tooltips help new users understand functionality
5. **Responsive design**: Resizable dialog adapts to different screen sizes and user preferences

## Technical Details

### File Modified
- `/ui/injection_dialog.py`

### Key Methods Added
- `_setup_keyboard_shortcuts()`: Configures all keyboard shortcuts
- `_next_tab()`: Navigate to next tab
- `_prev_tab()`: Navigate to previous tab

### Layout Structure
```
Dialog
├── Sprite File Selector (shared)
└── Tab Widget
    ├── VRAM Injection Tab
    │   └── Splitter (30/70)
    │       ├── Controls Panel
    │       └── Preview Widget
    └── ROM Injection Tab
        └── Splitter (30/70)
            ├── Controls Panel
            └── Preview Widget
```

## Testing
All changes have been tested and verified:
- Dialog opens at correct size
- Minimum size constraints work properly
- Keyboard shortcuts function as expected
- Tooltips display correctly
- Sprite file selector is properly shared between tabs
- Splitter ratios are maintained

## Future Enhancements (Optional)
- Remember dialog size and position between sessions
- Add more keyboard shortcuts for common actions
- Implement drag-and-drop for file selection
- Add validation feedback with visual indicators
- Consider adding a status bar for operation feedback