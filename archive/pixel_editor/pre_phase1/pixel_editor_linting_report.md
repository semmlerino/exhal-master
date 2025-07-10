# Pixel Editor Linting Report

## Summary

Ran multiple linting tools (Ruff, Black, isort) on all pixel editor related files.
Found several issues that need to be addressed for code quality and consistency.

## Files Analyzed

1. `indexed_pixel_editor.py` - Main pixel editor implementation
2. `pixel_editor_widgets.py` - Custom widget implementations
3. `debug_pixel_editor.py` - Debug utilities
4. `extract_for_pixel_editor.py` - Extraction utilities
5. `test_indexed_pixel_editor.py` - Test file
6. `test_pixel_editor_core.py` - Core tests
7. `launch_sprite_pixel_editor.py` - Launcher script
8. `run_pixel_editor_tests.py` - Test runner
9. `test_indexed_pixel_editor_enhanced.py` - Enhanced tests

## Issues Found

### 1. **Ruff Linting Issues** (39 total errors)

#### Common Issues:
- **N802** (11 instances): Function names should be lowercase
  - `keyPressEvent`, `wheelEvent`, `setWidget`, etc. (PyQt requires these names)
- **TRY300** (8 instances): Consider moving return statements to else blocks
- **DTZ005** (2 instances): `datetime.now()` called without timezone
- **N815** (2 instances): Class-level variables should not be mixedCase
- **F401** (3 instances): Unused imports in launcher
- **E722** (1 instance): Bare except clause
- **ERA001** (2 instances): Commented out code
- **SIM117** (4 instances): Multiple with statements can be combined
- **NPY002** (2 instances): Legacy numpy random calls
- **SIM105** (1 instance): Use contextlib.suppress

### 2. **Black Formatting Issues**
All 4 main pixel editor files need reformatting:
- `indexed_pixel_editor.py`
- `pixel_editor_widgets.py`
- `debug_pixel_editor.py`
- `extract_for_pixel_editor.py`

### 3. **isort Import Ordering Issues**
All 4 main files have incorrectly sorted imports.

## Priority Fixes

### High Priority (Functional Issues):
1. **Bare except clause** - Can hide real errors
2. **Unused imports** - Clean up code
3. **Datetime without timezone** - Can cause issues in different timezones

### Medium Priority (Code Quality):
1. **Import ordering** - Consistency across project
2. **Black formatting** - Code style consistency
3. **Try/except/else patterns** - Better error handling

### Low Priority (Convention/Style):
1. **PyQt method names** - These are required by Qt framework
2. **Variable naming** - Some are Qt signals that need specific names

## Recommendations

1. **Fix functional issues first** - bare except, imports, datetime
2. **Run auto-formatters** - `black` and `isort` can fix most formatting
3. **Configure Ruff** - Add PyQt method name exceptions to config
4. **Update try/except blocks** - Use else blocks where suggested
5. **Modernize numpy usage** - Use new random generator API

## Next Steps

1. Fix high priority issues manually
2. Run `black .` to auto-format
3. Run `isort .` to fix imports
4. Re-run `ruff` to verify fixes
5. Update pyproject.toml to ignore PyQt-required naming conventions