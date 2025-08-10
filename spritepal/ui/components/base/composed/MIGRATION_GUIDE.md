# DialogBase to Composition Migration Guide

## Overview

The `DialogBaseMigrationAdapter` provides a seamless migration path from the monolithic `DialogBase` class to the new composition-based architecture. This adapter maintains 100% backward compatibility while internally using the new component system.

## Quick Migration

### Step 1: Change Your Import

Replace:
```python
from ui.components.base.dialog_base import DialogBase
```

With:
```python
from ui.components.base.composed.migration_adapter import DialogBaseMigrationAdapter as DialogBase
```

That's it! Your existing dialogs will continue to work exactly as before.

## Benefits of Migration

1. **No Code Changes Required**: The adapter provides the exact same API as DialogBase
2. **Improved Maintainability**: Internal use of composition makes the code more modular
3. **Gradual Migration Path**: You can migrate dialogs one at a time
4. **Better Testing**: Component-based architecture is easier to test in isolation

## How It Works

The migration adapter:
- Inherits from `ComposedDialog` instead of `QDialog`
- Maps all DialogBase methods to appropriate component managers
- Maintains all DialogBase properties (`main_layout`, `content_widget`, `button_box`, etc.)
- Preserves the `_setup_ui()` pattern for subclasses
- Keeps initialization order checking (though simplified)

## Supported Features

All DialogBase features are supported:

### Initialization Parameters
- `parent`: Parent widget
- `title`: Window title
- `modal`: Modal dialog flag
- `min_size`: Minimum size tuple
- `size`: Fixed size tuple
- `with_status_bar`: Enable status bar
- `with_button_box`: Enable button box
- `default_tab`: Default tab index
- `orientation`: Splitter orientation
- `splitter_handle_width`: Splitter handle width

### Methods
- `_setup_ui()`: UI setup method for subclasses
- `add_tab()`: Add tabs to the dialog
- `set_current_tab()`: Switch tabs
- `get_current_tab_index()`: Get current tab
- `add_panel()`: Add panels to splitter
- `add_horizontal_splitter()`: Create splitters
- `add_button()`: Add custom buttons
- `update_status()`: Update status bar
- `show_error()`, `show_info()`, `show_warning()`: Message dialogs
- `confirm_action()`: Confirmation dialogs
- `set_content_layout()`: Set content layout

### Properties
- `main_layout`: Main QVBoxLayout
- `content_widget`: Content area widget
- `button_box`: Dialog button box
- `status_bar`: Status bar widget
- `tab_widget`: Tab widget
- `main_splitter`: Main splitter widget

## Example: Existing Dialog

```python
# This existing dialog works without any changes
class MyDialog(DialogBase):
    def __init__(self, parent=None):
        # Declare instance variables (DialogBase pattern)
        self.my_widget = None
        self.my_data = []
        
        # Initialize dialog
        super().__init__(
            parent=parent,
            title="My Dialog",
            modal=True,
            with_status_bar=True,
            with_button_box=True
        )
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        # Create widgets
        self.my_widget = QWidget()
        
        # Add tabs
        self.add_tab(self.my_widget, "Main Tab")
        self.add_tab(QLabel("Settings"), "Settings")
        
        # Update status
        self.update_status("Ready")
        
        # Add custom button
        self.add_button("Process", self.on_process)
    
    def on_process(self):
        """Handle process action."""
        if self.confirm_action("Confirm", "Process data?"):
            # Process...
            self.show_info("Success", "Processing complete!")
            self.update_status("Processed")
```

## Advanced: Using New Composition Features

While maintaining backward compatibility, you can also access the new composition features:

```python
class ModernDialog(DialogBase):
    def _setup_ui(self):
        # Access component managers directly if needed
        message_manager = self.get_component("message_dialog")
        if message_manager:
            # Connect to signals for tracking
            message_manager.message_shown.connect(self.on_message_shown)
        
        # Use context for advanced features
        self.context.config["custom_setting"] = "value"
    
    def on_message_shown(self, msg_type, message):
        """Track all messages shown."""
        print(f"Message shown: {msg_type} - {message}")
```

## Migration Strategy

### Phase 1: Drop-in Replacement
1. Change imports to use migration adapter
2. Verify dialogs work as expected
3. No functionality changes

### Phase 2: Gradual Modernization (Optional)
1. Access composition features where beneficial
2. Use component managers directly for new features
3. Leverage context for shared state

### Phase 3: Full Composition (Future)
1. Eventually migrate to pure `ComposedDialog`
2. Use components directly without adapter
3. Benefit from full composition architecture

## Testing

The migration adapter is fully tested to ensure compatibility:

```bash
# Run verification script
python3 verify_migration_adapter.py
```

## Troubleshooting

### Initialization Order Warnings
The adapter maintains initialization order checking but is less strict. Warnings are logged instead of raising exceptions.

### Component Access
If you need direct component access:
```python
component = self.get_component("component_name")
```

Available components:
- `"message_dialog"`: Message dialog manager
- `"button_box"`: Button box manager (if with_button_box=True)
- `"status_bar"`: Status bar manager (if with_status_bar=True)

## Summary

The `DialogBaseMigrationAdapter` provides a risk-free migration path from `DialogBase` to the new composition architecture. Simply change your import and your dialogs continue working while benefiting from the improved internal architecture.