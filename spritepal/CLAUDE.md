# SpritePal Development Guidelines

## Qt Testing Best Practices Learned

### Layered Testing Strategy

We use a **hybrid approach** combining the best of both mock and real Qt testing:

1. **Unit Tests**: Fast mocks for business logic
2. **Integration Tests**: Real Qt with `qtbot` for UI behavior
3. **Environment Detection**: Automatic fallback strategies

### Critical Crash Prevention Patterns

Through systematic fixes, we've established patterns that prevent "Fatal Python error: Aborted" crashes:

#### MockQDialog Pattern (Critical Success Factor)

**Never inherit from QDialog in mocks** - causes metaclass conflicts
```python
# CORRECT - Safe for all environments
class MockDialog(QObject):
    accepted = pyqtSignal()
    rejected = pyqtSignal()
    
# INCORRECT - Causes fatal crashes  
class MockDialog(QDialog):  # Don't do this!
    pass
```

#### Mock at Import Location Pattern

```python
# Mock where imported/used, not where defined
@patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog')  # ✓ Correct
@patch('ui.dialogs.manual_offset_unified_integrated.UnifiedManualOffsetDialog')  # ✗ Wrong
```

#### Robust Environment Detection

```python
def is_headless_environment() -> bool:
    if os.environ.get("CI"): return True
    if not os.environ.get("DISPLAY"): return True
    try:
        app = QApplication.instance() or QApplication([])
        return not app.primaryScreen()
    except: return True
```

### pytest-qt Integration Patterns

#### Signal Testing
```python
def test_async_operation(qtbot):
    with qtbot.waitSignal(worker.finished, timeout=5000) as blocker:
        blocker.connect(worker.failed)  # Multiple signals
        worker.start()
    assert blocker.args[0] == "success"  # Access signal args

# For callbacks
def test_callback(qtbot):
    with qtbot.waitCallback() as cb:
        page.runJavaScript("1 + 1", cb)
    cb.assert_called_with(2)
```

#### Qt Logging Control
```ini
# pytest.ini
[pytest]
qt_log_level_fail = CRITICAL
qt_log_ignore = 
    WM_DESTROY.*sent
    WM_PAINT failed
```

```python
def test_with_qt_logs(qtlog):
    do_something_that_warns()
    records = [(r.type, r.message.strip()) for r in qtlog.records]
    assert (QtWarningMsg, 'expected warning') in records
```

#### Model Testing
```python
def test_model_behavior(qtmodeltester):
    model = QStandardItemModel()
    # ... populate model ...
    qtmodeltester.check(model)  # Comprehensive validation
```

#### Visual Debugging
```python
def test_widget_appearance(qtbot):
    widget = MyWidget()
    qtbot.addWidget(widget)
    # On failure, save screenshot for inspection
    if assertion_fails:
        path = qtbot.screenshot(widget)
        assert False, f"Widget incorrect: {path}"
```

### Test Classification and Markers

- `@pytest.mark.gui` - Real Qt tests (requires display/xvfb)
- `@pytest.mark.headless` - Mock/unit tests (fast, always work)
- `@pytest.mark.serial` - No parallel execution
- `@pytest.mark.qt_no_exception_capture` - Disable crash protection

### CI/CD Environment Setup

#### GitHub Actions
```yaml
env:
  DISPLAY: ':99.0'
steps:
  - run: |
      sudo apt install libxkbcommon-x11-0 libxcb-icccm4 x11-utils
      /sbin/start-stop-daemon --start --quiet --pidfile /tmp/custom_xvfb_99.pid \
        --make-pidfile --background --exec /usr/bin/Xvfb -- :99 -screen 0 1920x1200x24 -ac +extension GLX
```

#### Alternative: pytest-xvfb Plugin
```bash
pip install pytest-xvfb
pytest --xvfb-width=1920 --xvfb-height=1200
```

### Results Achieved

- **Manual Offset Tests**: 87% pass rate (was 0% - complete failure)
- **Fatal Crashes**: 100% elimination through mock patterns  
- **CI Compatibility**: Full headless + xvfb support
- **Test Coverage**: Unit (fast) + Integration (comprehensive)

### Development Workflows

**Fast Unit Testing** (Mock-based):
```bash
pytest -m "headless and not slow"  # Quick iteration
```

**Integration Testing** (Real Qt):
```bash  
pytest -m "gui" --xvfb-width=1920 --xvfb-height=1200
```

**Complete Test Suite**:
```bash
pytest -m "headless" && pytest -m "gui"  # Both layers
```

## Architecture Guidelines

### Thread Safety Patterns
- Use `qtbot.waitSignal()` for async testing
- Clean up workers with proper signal connections
- Test signal/slot behavior explicitly

### Manager/Worker Separation  
- Business logic in managers (unit test with mocks)
- Qt threading in workers (integration test with qtbot)
- Signal interfaces between layers

### Error Handling
```python
# Test exception capture in Qt virtual methods
@pytest.mark.qt_no_exception_capture
def test_exception_in_virtual_method(qtbot):
    # When you need to test exception handling
```

## Development Tools

### Type Safety
- basedpyright with Qt stubs
- Protocol definitions for testable interfaces
- TYPE_CHECKING imports for dependencies

### Testing Infrastructure
- `qtbot` fixture for real Qt interaction
- `qtmodeltester` for QAbstractItemModel validation  
- `qtlog` fixture for message inspection
- `qtbot.screenshot()` for visual debugging

### Code Quality
- Ruff with Qt-aware rules
- Exception capture in virtual methods
- Systematic test markers

## Project Structure

```
spritepal/
├── core/           # Business logic (unit test with mocks)
├── ui/             # Qt UI components (integration test with qtbot)  
├── tests/
│   ├── unit/       # Fast mock-based tests
│   ├── integration/# Real Qt tests with qtbot
│   ├── infrastructure/  # Mock patterns and qtbot helpers
│   └── fixtures/        # Test data and configurations
├── utils/          # Shared utilities
└── docs/           # Test documentation and examples
```

## Critical Success Factors

1. **Layered Testing**: Unit (mocks) + Integration (real Qt)
2. **MockQDialog Pattern**: Never inherit from QDialog in mocks  
3. **Signal Testing**: Use `qtbot.waitSignal()` for async behavior
4. **Environment Setup**: xvfb for CI, fallback detection for robustness
5. **Visual Debugging**: `qtbot.screenshot()` for failure analysis

---

*These patterns were established through systematic resolution of Qt testing issues and provide a reliable foundation for continued SpritePal development.*