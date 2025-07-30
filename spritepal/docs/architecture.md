# SpritePal Architecture Guidelines

## Module Boundaries and Import Rules

SpritePal follows a layered architecture to maintain clean dependencies and prevent circular imports.

### Layer Structure

```
┌─────────────────────────────────────┐
│         UI Layer (ui/)              │  ← User Interface
├─────────────────────────────────────┤
│     Manager Layer (core/managers/)  │  ← Business Logic
├─────────────────────────────────────┤
│       Core Layer (core/)            │  ← Domain Logic
├─────────────────────────────────────┤
│       Utils Layer (utils/)          │  ← Shared Utilities
└─────────────────────────────────────┘
```

### Import Rules

1. **UI Layer (`ui/`)**
   - ✅ CAN import from: `core/`, `core/managers/`, `utils/`
   - ❌ CANNOT import from: other UI modules (except submodules)
   - Purpose: Presentation layer only, no business logic

2. **Manager Layer (`core/managers/`)**
   - ✅ CAN import from: `core/`, `utils/`
   - ❌ CANNOT import from: `ui/`
   - Purpose: Business logic, workflow coordination

3. **Core Layer (`core/`)**
   - ✅ CAN import from: `utils/`
   - ❌ CANNOT import from: `ui/`, `core/managers/`
   - Purpose: Domain logic, data structures, algorithms

4. **Utils Layer (`utils/`)**
   - ✅ CAN import from: Python standard library only
   - ❌ CANNOT import from: ANY SpritePal modules
   - Purpose: Shared utilities, constants, helpers

### Common Patterns

#### Avoiding Circular Imports

1. **Use Type Checking Imports**
   ```python
   from typing import TYPE_CHECKING
   
   if TYPE_CHECKING:
       from spritepal.core.controller import Controller
   ```

2. **Dependency Injection**
   Instead of importing managers directly:
   ```python
   # Bad
   from spritepal.core.managers import get_extraction_manager
   
   # Good
   def __init__(self, extraction_manager: ExtractionManager):
       self.extraction_manager = extraction_manager
   ```

3. **Registry Pattern**
   Use the ManagerRegistry for cross-module access:
   ```python
   from spritepal.core.managers import ManagerRegistry
   
   extraction_manager = ManagerRegistry.get_extraction_manager()
   ```

### Special Cases

#### Conditional Imports

Some modules support standalone operation and use conditional imports:

```python
# utils/rom_cache.py - Supports standalone usage
try:
    from spritepal.utils.logging_config import get_logger
except ImportError:
    # Fallback for standalone usage
    import logging
    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)
```

This pattern is acceptable ONLY in `utils/` modules that need to work independently.

### Anti-Patterns to Avoid

1. **Import Inside Functions** (except for circular import resolution)
   ```python
   # Bad
   def my_function():
       from spritepal.utils.settings import get_settings  # Avoid!
   ```

2. **Wildcard Imports**
   ```python
   # Bad
   from spritepal.core import *
   
   # Good
   from spritepal.core import SpriteExtractor, PaletteManager
   ```

3. **Cross-UI Module Imports**
   ```python
   # Bad - ui/dialogs importing from ui/panels
   from spritepal.ui.panels import SomePanel
   
   # Good - use signals or callbacks instead
   ```

### Testing Imports

Test files have more flexibility but should follow these guidelines:

1. Tests can import from any layer
2. Use test fixtures to avoid production dependencies
3. Mock external dependencies at module boundaries

### Enforcement

1. **Static Analysis**: Run `python scripts/analyze_imports.py` to check for violations
2. **Code Review**: Check imports follow these rules
3. **CI/CD**: Automated checks for import violations

### Dialog Initialization Pattern

All dialogs should follow the initialization pattern enforced by `DialogBase`:

```python
from spritepal.ui.components.base import DialogBase

class MyDialog(DialogBase):
    def __init__(self, parent: QWidget | None = None):
        # Step 1: Declare ALL instance variables
        self.my_widget: QWidget | None = None
        self.my_data: list[str] = []
        
        # Step 2: Call super().__init__() 
        super().__init__(parent)  # This calls _setup_ui()
        
    def _setup_ui(self):
        # Step 3: Create widgets (variables already declared)
        self.my_widget = QPushButton("Click me")
```

This prevents the common bug where instance variables declared after `_setup_ui()` overwrite already-created widgets.