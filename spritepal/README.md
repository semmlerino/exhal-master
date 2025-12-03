# SpritePal

A PySide6-based sprite extraction and editing tool for SNES ROM hacking.

## Features

- Extract sprites from SNES ROMs with HAL compression support
- Edit and preview sprites with palette management
- Inject modified sprites back into ROMs
- Multi-threaded thumbnail generation for fast browsing
- WCAG 2.1 compliant keyboard navigation

## Installation

```bash
pip install -e .
```

For development with all tools:

```bash
pip install -e ".[dev]"
```

## Requirements

- Python 3.9+
- PySide6 >= 6.5.0

## Usage

```python
from spritepal.core.controller import SpritePalController
from spritepal.ui.main_window import MainWindow

controller = SpritePalController()
window = MainWindow(controller)
window.show()
```

## License

MIT
