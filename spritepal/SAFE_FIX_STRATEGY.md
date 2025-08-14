# Safe Fix Strategy - No Breaking Changes

## ⛔ DO NOT Run Automated Fixes Until:

1. **Commit current changes** (200+ files modified!)
   ```bash
   git add -A
   git commit -m "fix: Division by zero and ROM scanning fixes"
   ```

2. **Create a branch for linting fixes**
   ```bash
   git checkout -b fix/safe-linting-cleanup
   ```

3. **Have tests passing**
   ```bash
   pytest tests/ -x --tb=short
   ```

## ✅ Safe Fixes Only (After Committing)

### Phase 1: Whitespace Only (100% Safe)
```bash
# These CANNOT break code
../venv/bin/ruff check --select W291,W292,W293 --fix .
git diff  # Review
pytest tests/ -x  # Verify
git commit -m "style: Fix whitespace issues"
```

### Phase 2: Truly Unused Imports (Review Each)
```bash
# List unused imports first
../venv/bin/ruff check --select F401 . | grep ".py"

# Fix ONE file at a time
../venv/bin/ruff check --select F401 --fix path/to/specific/file.py
# Review the change - some imports are for side effects!
git diff path/to/specific/file.py
```

### Phase 3: Manual Fixes Required

#### Complex Functions (PLR0915 - 49 cases)
**DO NOT AUTO-FIX** - Needs intelligent refactoring:
```python
# BEFORE: 80-line function
def process_all_data():
    # setup code (20 lines)
    # validation (20 lines)  
    # processing (20 lines)
    # cleanup (20 lines)

# AFTER: Extracted methods
def process_all_data():
    data = self._setup_data()
    self._validate_data(data)
    result = self._process_data(data)
    self._cleanup(data)
    return result
```

#### Import Location (PLC0415 - 244 cases)
**DO NOT AUTO-MOVE** - Check each for:
- Circular import prevention
- Conditional imports
- Performance (lazy loading)
- After initialization

## ❌ Never Auto-Fix These

### Import Organization Inside Functions
```python
# This pattern is intentional - DO NOT move to top
def handle_gui_action():
    from PySide6.QtWidgets import QDialog  # Lazy load, only when needed
    
if TYPE_CHECKING:
    from heavy_module import HeavyClass  # Only for type hints

try:
    from optional_module import Feature
except ImportError:
    Feature = None  # Graceful degradation
```

### Simplification Rules (SIM)
These can subtly change behavior:
```python
# SIM102 might combine these incorrectly
if condition1:
    if condition2:  # Has different semantics than 'if condition1 and condition2'
        action()     # (short-circuit evaluation, side effects)
```

## 📊 Current State Analysis

Based on analysis:
- **674 total issues**
- **267 non-top-level imports** (mostly intentional)
- **200+ files with uncommitted changes** (DANGER!)
- **49 complex functions** (need manual refactoring)

## 🎯 Realistic Goal

Don't try to fix everything. Focus on:

1. **Week 1**: Fix actual bugs (type errors)
2. **Week 2**: Refactor complex functions (one at a time)
3. **Week 3**: Clean up safe style issues
4. **Week 4**: Document why certain "issues" are intentional

## 🔧 Helper Scripts

### Check What's Safe to Fix
```bash
# Run the safe analysis script
./safe_linting_approach.py

# This will tell you:
# - What's safe to auto-fix
# - What needs manual review
# - Current git status
```

### Test After Each Fix
```bash
# Quick smoke test
pytest tests/test_manual_offset_unit.py -xvs

# Full test suite (slower)
pytest tests/ --tb=short
```

## 📝 Track Intentional Patterns

Create `.ruff.toml` to ignore intentional patterns:
```toml
[tool.ruff]
ignore = [
    "PLC0415",  # Import outside top-level (we use for circular imports)
    "PLR0915",  # Too many statements (some UI setup needs this)
]

[tool.ruff.per-file-ignores]
"tests/*" = ["PLC0415"]  # Tests use conditional imports
"ui/dialogs/*" = ["PLR0915"]  # Complex UI setup
```

## ⚡ Quick Win (Safe Now)

If you've committed your changes, this is 100% safe:
```bash
# Fix only trailing whitespace
../venv/bin/ruff check --select W291 --fix .
# Cannot break anything, just removes spaces at line ends
```

---

**Remember**: The goal isn't to fix every linting issue. It's to have **working, maintainable code**. Some "issues" are intentional design decisions.