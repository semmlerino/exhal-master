# SpritePal Priority Action Plan

## 🔴 Phase 1: Critical Issues (Week 1)
*Focus: Prevent runtime failures and crashes*

### 1.1 Fix Critical Type Errors (578 remaining)
**Timeline**: 2-3 days  
**Impact**: Prevents runtime crashes and improves type safety

#### Immediate Actions:
```bash
# Identify critical type errors
../venv/bin/basedpyright --project . | grep "error" | head -20

# Focus on:
- Undefined attributes/methods
- Incompatible type assignments
- Missing type annotations for public APIs
```

#### Priority Fixes:
1. **Worker type errors** - Thread safety critical
2. **Manager protocol violations** - Core functionality
3. **Signal/slot type mismatches** - Qt integration
4. **File I/O type issues** - Data integrity

### 1.2 Fix Critical Undefined Names (F821)
**Timeline**: 1 day  
**Impact**: Prevents NameError at runtime

```python
# Auto-fix script
def fix_undefined_names():
    # Add missing imports
    # Fix typos in variable names
    # Resolve circular imports
```

---

## 🟠 Phase 2: High-Impact Improvements (Week 2)
*Focus: Test reliability and code quality*

### 2.1 Replace Qt Widget Mocks with Real Components
**Timeline**: 3-4 days  
**Impact**: 30% better test coverage, catches real UI bugs

#### Migration Pattern:
```python
# BEFORE: Mock-based test
def test_dialog():
    dialog = MagicMock()
    dialog.exec.return_value = QDialog.Accepted
    
# AFTER: Real Qt with qtbot
def test_dialog(qtbot):
    dialog = RealDialog()
    qtbot.addWidget(dialog)
    qtbot.mouseClick(dialog.ok_button, Qt.LeftButton)
    assert dialog.result() == QDialog.Accepted
```

#### Target Files (High Priority):
1. `test_manual_offset_*` (15 files) - Core UI functionality
2. `test_grid_arrangement_*` (8 files) - Layout critical
3. `test_*_dialog_*.py` (12 files) - User interaction

### 2.2 Fix Code Complexity Issues
**Timeline**: 2 days  
**Impact**: Better maintainability, easier debugging

#### Targets:
- **PLR0915**: Functions with >50 statements (92 occurrences)
- **PLR0912**: Functions with >12 branches (74 occurrences)

#### Refactoring Strategy:
```python
# Extract method pattern
def complex_function():  # Before: 80 lines
    # ... lots of code ...
    
def complex_function():  # After: 20 lines
    result1 = _process_part1()
    result2 = _process_part2(result1)
    return _finalize(result2)
```

---

## 🟡 Phase 3: Medium Priority (Week 3)
*Focus: Testing infrastructure and consistency*

### 3.1 Implement File I/O Testing with Temp Files
**Timeline**: 2 days  
**Impact**: Real I/O testing, catches permission issues

#### Create Test Fixtures:
```python
@pytest.fixture
def temp_rom_file():
    """Provide temp ROM file with test data"""
    with tempfile.NamedTemporaryFile(suffix='.sfc') as f:
        f.write(TEST_ROM_HEADER + TEST_SPRITE_DATA)
        f.flush()
        yield f.name

@pytest.fixture
def temp_output_dir():
    """Provide temp directory for output files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
```

### 3.2 HAL Compression Test Mode
**Timeline**: 2 days  
**Impact**: Test real compression without full overhead

#### Implementation:
```python
class HALCompressor:
    def __init__(self, test_mode=False):
        if test_mode:
            self.max_size = 0x1000  # 4KB limit for tests
            self.timeout = 1.0      # 1 second timeout
```

### 3.3 Fix Import Organization
**Timeline**: 1 day  
**Impact**: Faster imports, cleaner code

```bash
# Auto-organize imports
../venv/bin/ruff check --select I --fix .
```

---

## 🟢 Phase 4: Low Priority (Week 4)
*Focus: Polish and documentation*

### 4.1 Replace Worker Thread Mocks
**Timeline**: 2 days  
**Impact**: Better async testing

#### Migration:
```python
# Use real workers with proper signal testing
def test_worker_lifecycle(qtbot):
    worker = RealWorker()
    controller = WorkerController(worker)
    
    with qtbot.waitSignal(worker.finished, timeout=5000):
        controller.start()
    
    assert worker.result is not None
```

### 4.2 Clean Remaining Linting Issues
**Timeline**: 2 days  
**Impact**: Consistent code style

```bash
# Batch fix safe issues
../venv/bin/ruff check --fix --unsafe-fixes \
    --select E,W,F,UP,B,SIM,RET
```

### 4.3 Update Documentation
**Timeline**: 1 day  
**Impact**: Easier onboarding, better maintenance

#### Documents to Update:
1. `TESTING_STRATEGY.md` - Add real component patterns
2. `CLAUDE.md` - Update with new testing approaches
3. `README.md` - Add testing prerequisites

---

## 📊 Success Metrics

### Week 1 Targets:
- ✅ Type errors: 578 → <100
- ✅ Critical errors (F821): 0
- ✅ No runtime crashes in test suite

### Week 2 Targets:
- ✅ Qt mock usage: -30%
- ✅ Code complexity: -50% of violations
- ✅ Test execution time: <5 minutes

### Week 3 Targets:
- ✅ File I/O mocks: -80%
- ✅ HAL test coverage: >90%
- ✅ Import time: -20%

### Week 4 Targets:
- ✅ All linting issues: <100
- ✅ Documentation: 100% updated
- ✅ Test reliability: >99%

---

## 🚀 Quick Wins (Can do immediately)

### 1. Auto-fix Safe Linting Issues
```bash
# Run now - fixes ~200 issues automatically
../venv/bin/ruff check --fix --select UP,SIM,RET .
```

### 2. Add Missing Type Hints
```python
# Generate type stubs for untyped functions
../venv/bin/basedpyright --createstub ui
```

### 3. Create Test Helper Module
```python
# tests/helpers/qt_testing.py
def create_widget_with_cleanup(qtbot, widget_class, **kwargs):
    """Create widget with automatic cleanup"""
    widget = widget_class(**kwargs)
    qtbot.addWidget(widget)
    return widget

def wait_for_signal_with_timeout(qtbot, signal, timeout=1000):
    """Simplified signal waiting"""
    with qtbot.waitSignal(signal, timeout=timeout) as blocker:
        yield blocker
```

---

## 🔄 Continuous Improvements

### Daily:
- Run type checker before commits
- Fix new linting issues immediately
- Replace mocks when touching test files

### Weekly:
- Review test execution times
- Identify flaky tests
- Update migration progress

### Monthly:
- Audit mock usage trends
- Review test coverage
- Update documentation

---

## 🎯 Next Immediate Step

**Start with**: Fix critical type errors in worker classes

```bash
# Run this now:
../venv/bin/basedpyright ui/workers/*.py | grep error

# Then fix each error systematically
```

This prevents the most likely runtime failures and improves stability immediately.

---

*Timeline: 4 weeks total for all phases*  
*Effort: ~2-3 hours/day focused work*  
*Risk: Low - all changes are in test code*