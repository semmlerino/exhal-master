# Test Infrastructure Reliability Fix Plan

## Overview

This plan addresses critical reliability issues in the SpritePal test suite identified through comprehensive review. The issues fall into three priority tiers based on impact on test reliability.

---

## Phase 1: Critical Fixture Isolation Fixes (Highest Priority)

**Goal**: Ensure tests don't leak state to each other.

### 1.1 Fix `main_window` Mutable State Leakage

**File**: `tests/conftest.py:1440-1444`

**Problem**: The `main_window` fixture has mutable attributes that persist between tests:
```python
window._output_path = ""
window._extracted_files = []  # Mutable list - accumulates across tests
```

**Fix**: Add explicit reset in `reset_class_scoped_fixtures` (line 1537+):
```python
# Add to fixtures_to_reset list or handle explicitly:
if 'main_window' in fixture_names:
    try:
        main_window = request.getfixturevalue('main_window')
        main_window._output_path = ""
        main_window._extracted_files = []  # New list each test
    except pytest.FixtureLookupError:
        pass
```

**Success Criteria**: Running `test_A` that modifies `_extracted_files`, followed by `test_B` that reads it, should show `test_B` sees empty list.

---

### 1.2 Fix Class-Scoped Real Component Reset

**File**: `tests/conftest.py:777-804, 1578-1584`

**Problem**: `mock_extraction_manager` and `mock_session_manager` are real components from `RealComponentFactory`. The reset logic (line 1578-1580) calls `reset_state()` if available, but:
- These real components may not implement `reset_state()`
- Exceptions are suppressed, hiding failures

**Fix A - Add reset_state() to real components** (preferred):

In `core/managers/extraction_manager.py`:
```python
def reset_state(self) -> None:
    """Reset internal state for test isolation."""
    self._cached_results = {}
    self._current_operation = None
    # Reset any other mutable state
```

In `core/managers/session_manager.py`:
```python
def reset_state(self) -> None:
    """Reset internal state for test isolation."""
    self._session_data = {}
    self._current_session = None
```

**Fix B - Alternative: Use function scope** (simpler but slower):

Change fixture scopes from `class` to `function`:
```python
@pytest.fixture(scope="function")  # Was "class"
def mock_extraction_manager() -> MockExtractionManagerProtocol:
    factory = RealComponentFactory()
    return factory.create_extraction_manager()
```

**Success Criteria**: Tests modifying manager state should not affect subsequent tests.

---

### 1.3 Add Module-Scoped Fixture Reset

**File**: `tests/conftest.py:1471-1493`

**Problem**: `mock_manager_registry` is module-scoped but has no reset mechanism. Tests can configure `get_manager.return_value` and it persists across the module.

**Fix**: Add module-level reset hook:
```python
@pytest.fixture(scope="module", autouse=True)
def reset_module_scoped_fixtures(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Reset module-scoped fixtures at end of each module."""
    yield
    # Reset after all tests in module complete
    if hasattr(request.module, '_mock_manager_registry'):
        request.module._mock_manager_registry.reset_mock()
```

Or simpler - track and reset in the fixture itself:
```python
@pytest.fixture(scope="module")
def mock_manager_registry(request: pytest.FixtureRequest) -> Generator[Mock, None, None]:
    registry = Mock()
    # ... setup ...
    yield registry
    registry.reset_mock()  # Reset at module end
```

---

## Phase 2: Worker Cleanup Reliability

**Goal**: Fix thread cleanup to use Qt-safe mechanisms.

### 2.1 Replace time.sleep() with Qt-safe Waiting

**File**: `tests/conftest.py:1688`

**Problem**: `time.sleep()` blocks the Qt event loop, preventing threads from cleaning up properly.

**Current Code**:
```python
while elapsed < max_wait_ms:
    active_threads = threading.active_count()
    if active_threads <= baseline_thread_count:
        break
    time.sleep(poll_interval_ms / 1000.0)  # BLOCKS Qt event loop
    elapsed += poll_interval_ms
```

**Fix**:
```python
from PySide6.QtCore import QCoreApplication, QThread

while elapsed < max_wait_ms:
    active_threads = threading.active_count()
    if active_threads <= baseline_thread_count:
        break

    # Process Qt events to allow threads to clean up
    app = QCoreApplication.instance()
    if app:
        app.processEvents()

    # Use Qt-safe sleep
    current_thread = QThread.currentThread()
    if current_thread:
        current_thread.msleep(poll_interval_ms)
    else:
        import time
        time.sleep(poll_interval_ms / 1000.0)  # Fallback only

    elapsed += poll_interval_ms
```

**Success Criteria**: No more "QThread: Destroyed while thread is still running" warnings.

---

## Phase 3: Add Assertions to Empty Tests

**Goal**: Tests should verify behavior, not just run without crashing.

### 3.1 Fix test_division_by_zero_comprehensive.py

**File**: `tests/test_division_by_zero_comprehensive.py`

**Problem**: All 10 tests call `worker.run()` without any assertions.

**Fix Pattern** (apply to each test):
```python
def test_scan_worker_zero_range(self):
    """Test SpriteScanWorker with zero scan range."""
    # ... existing setup ...

    worker.run()

    # ADD ASSERTIONS:
    # 1. Verify no exception was raised (implicit by reaching here)
    # 2. Verify result is valid (empty for zero range)
    assert hasattr(worker, '_parallel_finder'), "Worker should have finder"
    # 3. If worker has result attribute, verify it
    if hasattr(worker, 'result'):
        assert worker.result is not None, "Result should not be None"
    # 4. If worker has error attribute, verify no error
    if hasattr(worker, 'error'):
        assert worker.error is None, f"Unexpected error: {worker.error}"
```

**Tests to fix**:
- `test_scan_worker_zero_range` (line 22)
- `test_scan_worker_progress_callback_zero_range` (line 47)
- `test_range_scan_worker_zero_range` (line 85)
- `test_similarity_indexing_no_sprites` (line 105)
- `test_preview_worker_zero_expected_size` (line 124)
- `test_sprite_search_worker_zero_tile_count` (line 150)
- `test_search_worker_zero_step` (line 176)
- `test_scan_worker_zero_rom_size` (line 200)
- `test_all_workers_with_realistic_edge_cases` (line 223)
- `test_progress_calculations_boundary_conditions` (line 265)

---

### 3.2 Fix test_base_manager.py Validation Tests

**File**: `tests/test_base_manager.py:78-137`

**Problem**: Validation tests call methods but don't verify they work.

**Fix**: Add proper assertions:
```python
def test_validation_required(self):
    """Test that required field validation raises on missing keys."""
    with pytest.raises(ValueError) as exc_info:
        manager._validate_required({"a": 1}, ["a", "b"])
    assert "b" in str(exc_info.value), "Should mention missing field"
```

---

### 3.3 Remove or Fix test_black_boxes.py

**File**: `tests/test_black_boxes.py`

**Problem**: This is a debug script, not a test:
- Line 36: `test_preview_widget()` has no assertions
- Lines 80-128: `check_preview()` only prints debug output
- Lines 130-141: Contains `if __name__ == "__main__"` block

**Fix Options**:
1. **Move to scripts/**: Rename to `scripts/debug_preview_widget.py`
2. **Convert to real test**: Add assertions and remove debug prints
3. **Delete**: If no longer needed

---

## Phase 4: Performance Optimizations

**Goal**: Reduce unnecessary waiting in tests.

### 4.1 Replace Critical time.sleep() Calls

**Priority files** (sleeps > 0.3s):

| File | Line | Duration | Replace With |
|------|------|----------|--------------|
| `test_concurrent_operations.py` | 627 | 0.5s | `qtbot.waitSignal()` |
| `test_worker_owned_injection.py` | 152 | 0.5s | `qtbot.waitSignal()` |
| `test_worker_owned_injection.py` | 223 | 0.3s | `qtbot.waitSignal()` |
| `run_test_analysis.py` | 145 | 0.5s | Signal-based wait |

**Pattern**:
```python
# Before:
time.sleep(0.5)

# After:
with qtbot.waitSignal(worker.finished, timeout=500):
    pass  # Continues immediately when signal fires
```

---

## Phase 5: Documentation Cleanup

### 5.1 Delete Outdated pytest.ini

**File**: Project root `pytest.ini`

**Problem**: References non-existent directories (`sprite_editor/tests`, `pixel_editor/tests`).

**Action**: Delete file. `pyproject.toml` is the source of truth.

---

### 5.2 Document Segfault-Prone Tests

**File**: `tests/constants_segfault.py`

**Current**: 32 test patterns skipped by default.

**Action**:
1. Add docstrings explaining root cause for each pattern
2. Create issue tickets for fixing the underlying Qt threading issues
3. Consider marking with `@pytest.mark.segfault_prone` directly on tests instead of pattern matching

---

## Implementation Order

1. **Phase 1.1**: Fix main_window mutable state (15 min)
2. **Phase 1.2**: Fix class-scoped real component reset (30 min)
3. **Phase 2.1**: Fix worker cleanup time.sleep (20 min)
4. **Phase 3.1**: Add assertions to division_by_zero tests (30 min)
5. **Phase 1.3**: Add module-scoped fixture reset (15 min)
6. **Phase 3.2-3.3**: Fix remaining empty tests (20 min)
7. **Phase 4.1**: Replace critical sleep calls (30 min)
8. **Phase 5**: Documentation cleanup (10 min)

**Total estimated time**: 2.5-3 hours

---

## Verification

After each phase, run:
```bash
# Quick smoke test
uv run pytest spritepal/tests -x -q --tb=short -k "not segfault" 2>&1 | head -50

# Full test with timing
uv run pytest spritepal/tests --durations=20 -q 2>&1 | tail -30
```

---

## Success Metrics

| Metric | Before | After Target |
|--------|--------|--------------|
| Tests without assertions | 62 | 0 |
| Flaky test failures | Unknown | <1% |
| time.sleep() calls >0.3s | 5+ | 0 |
| Mutable fixture state leaks | 3+ | 0 |
