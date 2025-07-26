# Mock Reduction Plan for SpritePal Test Suite

## Overview
This document outlines a phased approach to reduce unnecessary mocking in the SpritePal test suite while maintaining test reliability and headless compatibility.

## Current State Analysis
- **Total test files using mocks**: 21 active files (217 total @patch/with patch occurrences)
- **Common mock patterns**:
  - Logger mocking (often unnecessary)
  - File system path mocking
  - Qt component mocking (necessary for headless)
  - Internal method mocking (often excessive)

## Phase 0: Baseline Metrics

### Goal
Establish baseline metrics before making changes.

### Metrics to Capture
```bash
# Test execution time
time pytest tests/ -v > baseline_time.txt

# Code coverage
pytest --cov=spritepal tests/ --cov-report=html

# Mock usage count (current baseline: 217 @patch/with patch occurrences)
grep -r "@patch\|with patch" tests/ | grep -v ".bak\|.disabled" | wc -l > baseline_mocks.txt

# Top mocked files
grep -c "@patch" tests/*.py | sort -t: -k2 -nr | head -10 > baseline_top_mocked.txt

# Test count by category
pytest --collect-only -q | head -n -2 | wc -l > baseline_tests.txt
```

### Current Top Mocked Files (by @patch count)
1. `test_controller.py`: 16 @patch decorators
2. `test_rom_injector_comprehensive.py`: 15 @patch decorators
3. `test_integration_mock.py`: 6 @patch decorators
4. `test_cross_dialog_integration.py`: 4+ @patch decorators
5. `test_grid_image_processor.py`: 3 @patch decorators

### Store Results
- Create `metrics/baseline.json` with all metrics
- Use for comparison after each phase

### Note on Disabled Tests
- `test_performance_integration.py.disabled` - Performance testing (17 @patch occurrences)
- `test_session_management_integration.py.disabled` - Session management tests (1 @patch occurrence)
- These files are excluded from the active test count but may need review if re-enabled

## Phase 1: Remove Unnecessary Logger Mocking

### Goal
Eliminate logger mocks that don't specifically test logging behavior.

### Target Files
1. `test_rom_injection_settings.py` (4 instances)
   - Lines with `patch("spritepal.ui.injection_dialog.get_logger")`
   ```python
   # Example pattern to remove:
   @patch("spritepal.ui.injection_dialog.get_logger")
   def test_something(self, mock_logger):
       mock_logger.return_value = Mock()
   ```
   
2. `test_error_boundary_integration.py` (1 instance)
   - Line with `patch("spritepal.core.controller.logger")`
   ```python
   # Remove this decorator and its parameter:
   @patch("spritepal.core.controller.logger")
   ```

### Implementation Steps
1. Remove `@patch` decorators for loggers
2. Remove associated mock_logger setup code
3. Let logging happen naturally during tests
4. Verify no test assertions depend on logger calls

### Test Command
```bash
pytest tests/test_rom_injection_settings.py tests/test_error_boundary_integration.py -v
```

### Expected Outcome
- Tests pass without logger mocking
- Cleaner test code
- Real logging output (can be captured by pytest if needed)

## Phase 2: Replace File System Mocking with Real Files

### Goal
Use pytest's `tmp_path` fixture instead of mocking file operations.

### Target Patterns
- Hardcoded paths like `"/path/to/test.sfc"`
- `@patch("os.path.exists")`
- `mock.path` operations

### Target Files to Update
- `test_controller.py` - uses hardcoded paths like "/test/vram.dmp"
- `test_main_window_state_integration.py` - may have path mocking
- `test_cross_dialog_integration.py` - likely has dialog path mocking

### Implementation Steps
1. Replace hardcoded paths with `tmp_path` fixtures:
   ```python
   # Before
   mock_dialog.input_rom_edit.text.return_value = "/path/to/test.sfc"
   
   # After
   test_rom = tmp_path / "test.sfc"
   test_rom.write_bytes(b"ROM data")
   mock_dialog.input_rom_edit.text.return_value = str(test_rom)
   ```

2. Create actual test files where needed
3. Remove path existence mocks
4. Use real file I/O operations
5. Handle cross-platform paths:
   ```python
   # Use pathlib for cross-platform compatibility
   from pathlib import Path
   test_file = tmp_path / "test.sfc"
   mock_dialog.text.return_value = str(test_file)  # Convert to string for Qt
   ```

### Test Command
```bash
pytest tests/ -k "path" -v
```

### Expected Outcome
- More realistic file handling tests
- Reduced mocking complexity
- Better test coverage of actual file operations

## Phase 3: Consolidate Qt Component Mocking

### Goal
Create reusable Qt mock fixtures to reduce duplication.

### Implementation Steps
1. Extract existing MockSignal from `test_integration_mock.py` to `tests/fixtures/qt_mocks.py`:
   ```python
   # Move this excellent implementation from test_integration_mock.py:
   class MockSignal:
       def __init__(self):
           self.callbacks = []
           self.emit = Mock(side_effect=self._emit)
       
       def connect(self, callback):
           self.callbacks.append(callback)
       
       def _emit(self, *args):
           for callback in self.callbacks:
               callback(*args)
   
   class MockQPixmap:
       def __init__(self):
           self.width = lambda: 100
           self.height = lambda: 100
           self.loadFromData = Mock(return_value=True)
   
   class MockSignal:
       def __init__(self):
           self.callbacks = []
       
       def connect(self, callback):
           self.callbacks.append(callback)
       
       def emit(self, *args):
           for callback in self.callbacks:
               callback(*args)
   ```

2. Update `conftest.py` to provide common fixtures:
   ```python
   @pytest.fixture
   def mock_qt_signals():
       return {
           'progress': MockSignal(),
           'finished': MockSignal(),
           'error': MockSignal()
       }
   ```

3. Replace individual Qt mocks with shared fixtures

### Test Command
```bash
QT_QPA_PLATFORM=offscreen pytest tests/ -v
```

### Expected Outcome
- Consistent Qt mocking patterns
- Reduced code duplication
- Easier maintenance

## Phase 4: Convert Over-Mocked Unit Tests

### Goal
Reduce excessive internal implementation mocking.

### Identification Criteria
- Tests with >5 `@patch` decorators
- Tests mocking internal methods
- Tests mocking trivial operations

### Specific Target Files
Based on initial analysis:
- `test_controller.py` - extensive mocking of internal components
- `test_main_window_state_integration.py` - likely over-mocked UI state
- `test_grid_arrangement_dialog_mock.py` - candidate for integration approach

### Implementation Steps
1. Identify candidates:
   ```bash
   grep -c "@patch" tests/*.py | sort -t: -k2 -nr | head -10
   ```

2. Convert to mini-integration tests:
   - Use real components where possible
   - Mock only external dependencies
   - Test behavior, not implementation

3. Example transformation:
   ```python
   # Before: Excessive mocking
   @patch('module.internal_method1')
   @patch('module.internal_method2')
   @patch('module.internal_method3')
   def test_feature(mock1, mock2, mock3):
       # Complex mock setup
   
   # After: Integration approach
   def test_feature(tmp_path):
       # Use real components with test data
       component = RealComponent(tmp_path)
       result = component.process()
       assert result == expected
   ```

### Test Command
```bash
pytest tests/ --tb=short -v
```

### Expected Outcome
- More robust tests
- Better coverage of real interactions
- Easier to understand test intent

## Phase 5: Document Testing Strategy

### Goal
Create comprehensive guidelines for future test development.

### Deliverables
1. Create `TESTING_GUIDELINES.md` with sections:
   - When to Mock vs Use Real Components
   - Qt Component Mocking Patterns
   - File System Testing Best Practices
   - Examples of Good vs Excessive Mocking

2. Update test docstrings with rationale for mocking

3. Add comments explaining non-obvious mocks

### Example Guidelines
```markdown
## When to Mock

### Always Mock
- Qt components in headless environments
- External network calls
- System-specific operations
- HAL compression tools (exhal/inhal binaries)
- Pixel editor subprocess launches

### Prefer Real Components
- File I/O (use tmp_path)
- Pure business logic
- Data transformations
- VRAM/CGRAM/OAM data processing
- PNG/palette file generation

### Never Mock
- The system under test
- Simple data structures
- Standard library functions (unless necessary)
- SpriteExtractor core logic
- PaletteManager operations

### SpritePal-Specific Examples

#### Good: Using real test data
```python
def test_extraction(tmp_path):
    # Create real VRAM data
    vram_data = bytearray(0x10000)
    vram_data[0xC000:0xC020] = SAMPLE_TILE_DATA
    vram_file = tmp_path / "test.vram"
    vram_file.write_bytes(vram_data)
    
    # Test with real extractor
    extractor = SpriteExtractor()
    img, tiles = extractor.extract_sprites_grayscale(str(vram_file), str(tmp_path / "out.png"))
    assert tiles > 0
```

#### Bad: Over-mocking internals
```python
@patch('spritepal.core.extractor.SpriteExtractor._decode_4bpp_tile')
@patch('spritepal.core.extractor.SpriteExtractor._load_vram')
def test_extraction(mock_load, mock_decode):
    # Too much mocking!
```
```

## Execution Timeline

### Week 1
- Phase 1: Remove logger mocking
- Run full test suite
- Address any failures

### Week 2
- Phase 2: File system mock reduction
- Update affected tests
- Verify headless compatibility

### Week 3
- Phase 3: Qt mock consolidation
- Create shared fixtures
- Refactor existing tests

### Week 4
- Phase 4: Reduce over-mocking
- Convert selected tests
- Performance comparison

### Week 5
- Phase 5: Documentation
- Review and finalize guidelines
- Team training

## Success Metrics

1. **Test Suite Health**
   - All tests pass after each phase
   - No increase in test execution time
   - Maintained code coverage

2. **Code Quality**
   - Reduced lines of mock setup code
   - Improved test readability
   - Clear test intent

3. **Maintainability**
   - Easier to add new tests
   - Consistent patterns
   - Well-documented approach

## Test Data Management

### Approach
1. Create `tests/fixtures/test_data/` directory
2. Generate minimal test files programmatically:
   ```python
   # tests/fixtures/test_data_generator.py
   def create_minimal_vram(size=0x10000):
       """Generate minimal valid VRAM data"""
       data = bytearray(size)
       # Add valid sprite tile at standard offset
       data[0xC000:0xC020] = VALID_4BPP_TILE
       return bytes(data)
   ```
3. DO NOT commit large binary test files
4. Use pytest fixtures to generate test data on-demand

## Risk Mitigation

1. **Test Failures**
   - Create a new git branch for each phase: `git checkout -b mock-reduction-phase-N`
   - Run tests after each file change
   - Keep original code in version control
   - Document any behavior changes

2. **Platform Compatibility**
   - Test on multiple platforms
   - Verify headless mode works
   - Maintain CI/CD compatibility

3. **Performance Impact**
   - Monitor test execution time
   - Profile if significant slowdown
   - Balance realism vs speed
   - Consider pytest-xdist for parallel execution:
     ```bash
     # May help offset I/O overhead from real files
     pytest -n auto tests/
     ```

## Rollback Plan
If any phase causes significant issues:
1. Revert using git: `git checkout main`
2. Cherry-pick successful changes: `git cherry-pick <commit>`
3. Analyze root cause using pytest verbose output
4. Adjust approach based on specific failures
5. Re-attempt with modifications
6. Consider partial implementation if full phase is problematic

## Examples of Mocks to Keep

### Essential Mocks (DO NOT REMOVE)
```python
# 1. HAL tool subprocess calls
@patch('subprocess.run')
def test_rom_injection(mock_run):
    # Keep this - we don't want to run actual compression
    
# 2. Pixel editor launches  
@patch('subprocess.Popen')
def test_open_in_editor(mock_popen):
    # Keep this - no need to launch external editor

# 3. Qt components in headless tests
@patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName')
def test_file_dialog(mock_dialog):
    # Keep this - can't show real dialogs in CI
```

## Conclusion
This phased approach will systematically reduce unnecessary mocking while maintaining test reliability. Each phase builds on the previous one, allowing for continuous validation and adjustment.