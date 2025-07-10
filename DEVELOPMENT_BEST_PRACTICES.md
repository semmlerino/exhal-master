# Development Best Practices to Avoid File Management Errors

## The Problem We Encountered
- `pixel_editor_workers.py` was accidentally archived when it was still needed
- This broke imports and caused confusion
- Easy mistake when managing many files during refactoring

## Prevention Strategies

### 1. **Test Before Archiving**
```bash
# ALWAYS run this before archiving
python3 -c "import module1, module2, module3; print('All imports OK')"

# Or create a simple import test
python3 -c "
try:
    from indexed_pixel_editor import *
    from pixel_editor_widgets import *
    from pixel_editor_workers import *
    print('✅ All imports successful')
except ImportError as e:
    print(f'❌ Import failed: {e}')
"
```

### 2. **Use Git Status as Safety Check**
```bash
# Before archiving, check what's new vs old
git status --porcelain | grep "^??" # Shows untracked (new) files
git ls-files | grep pixel_editor  # Shows tracked files

# New files shouldn't be archived immediately
```

### 3. **Create Archive Manifest**
```python
# archive_manifest.py
TO_ARCHIVE = [
    "test_*.py",  # Old test files
    "debug_*.py", # Debug utilities
    "*_old.py",   # Explicitly marked old files
]

KEEP_ACTIVE = [
    "pixel_editor_workers.py",  # New Phase 1
    "pixel_editor_commands.py", # New Phase 1
    "pixel_editor_utils.py",    # New Phase 1
]
```

### 4. **Use Staging Directory**
```bash
# Don't archive directly, stage first
mkdir archive_staging/
mv old_files archive_staging/

# Test everything still works
python3 main_app.py

# Only then move to archive
mv archive_staging/* archive/
```

### 5. **Add Import Checks to Main Files**
```python
# At top of indexed_pixel_editor.py
try:
    import pixel_editor_workers
    import pixel_editor_commands
    import pixel_editor_utils
except ImportError as e:
    print(f"Missing required module: {e}")
    print("Check if files were accidentally moved/archived")
    sys.exit(1)
```

### 6. **Use Automated Tests**
```python
# test_imports.py - Run after any file moves
import unittest
import importlib

class TestImports(unittest.TestCase):
    def test_all_modules_import(self):
        modules = [
            'indexed_pixel_editor',
            'pixel_editor_widgets', 
            'pixel_editor_workers',
            'pixel_editor_commands',
            'pixel_editor_utils',
            'pixel_editor_constants'
        ]
        
        for module in modules:
            with self.subTest(module=module):
                try:
                    importlib.import_module(module)
                except ImportError:
                    self.fail(f"Failed to import {module}")
```

### 7. **Document Active vs Archive**
```markdown
# PROJECT_STRUCTURE.md

## Active Pixel Editor Files
- indexed_pixel_editor.py - Main application
- pixel_editor_widgets.py - UI components
- pixel_editor_workers.py - Async operations (Phase 1)
- pixel_editor_commands.py - Undo system (Phase 1)
- pixel_editor_utils.py - Shared utilities (Phase 1)
- pixel_editor_constants.py - Constants (Phase 1)

## Can Be Archived
- test_*_old.py files
- debug utilities not in active use
- superseded documentation
```

### 8. **Use File Headers**
```python
"""
pixel_editor_workers.py - ACTIVE (Phase 1)
DO NOT ARCHIVE - Required for async file operations

Created: 2024-07-09
Status: Active
Dependencies: Used by indexed_pixel_editor.py
"""
```

### 9. **Pre-Archive Checklist**
```markdown
## Before Archiving Any File:
- [ ] File hasn't been modified in current phase
- [ ] No active imports of this file
- [ ] Not mentioned in current plans
- [ ] Ran import tests successfully
- [ ] Checked git status
- [ ] Tested main application
```

### 10. **Use `.archiveignore`**
```bash
# .archiveignore - Files that should NEVER be archived
pixel_editor_workers.py
pixel_editor_commands.py
pixel_editor_utils.py
pixel_editor_constants.py
**/models/*.py
**/views/*.py
**/controllers/*.py
```

## Recommended Workflow

1. **Plan** what to archive (list files)
2. **Check** dependencies and imports
3. **Stage** files in temporary directory
4. **Test** everything still works
5. **Archive** only after confirming
6. **Document** what was archived and why

## Quick Recovery

If you accidentally archive something:
```bash
# Find recently archived files
find archive/ -type f -mtime -1 -name "*.py"

# Restore if needed
cp archive/path/to/file.py ./
```

## Summary

The key is to **test before moving** and maintain clear documentation about what's active vs archived. Automated import tests catch these issues immediately.