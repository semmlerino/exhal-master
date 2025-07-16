# SpritePal Test Suite

This directory contains the pytest test suite for SpritePal.

## Test Coverage

- **test_extractor.py** - Tests for SpriteExtractor class (10 tests)
  - VRAM loading
  - 4bpp tile decoding
  - Tile extraction with various offsets
  - Grayscale image generation
  - Main extraction workflow

- **test_palette_manager.py** - Tests for PaletteManager class (11 tests)
  - CGRAM loading
  - BGR555 to RGB888 color conversion
  - Palette extraction
  - JSON palette file generation
  - Sprite palette filtering

- **test_constants.py** - Tests for constants module (6 tests)
  - SNES memory offsets
  - Sprite format constants
  - File extensions
  - Palette information

## Running Tests

From the spritepal directory:
```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_extractor.py -v

# Run with coverage
python3 -m pytest tests/ --cov=spritepal --cov-report=html
```

## Test Guidelines

- Tests are adapted to the actual implementation
- Minimal mocking - tests use real functionality
- Each test class tests one component
- Tests include edge cases and boundary conditions
- All tests must pass before considering a task complete