# SpritePal Test Taxonomy: When to Mock vs Real Implementations

This document establishes clear guidelines for when to use mocks versus real implementations in SpritePal tests, based on lessons learned from the comprehensive testing architecture overhaul.

## Core Principle

**Use real implementations wherever they provide value for catching architectural bugs. Use mocks only where they provide genuine testing benefits without hiding critical issues.**

## Test Categories

### 1. ALWAYS Use Real Implementations

These test scenarios MUST use real implementations because mocks hide critical bugs:

#### Qt Lifecycle & Threading Tests
- **Qt parent/child relationships** - Mocks can't validate Qt object lifecycle
- **Worker thread management** - Real QThread behavior is essential
- **Signal/slot connections across threads** - Thread affinity matters
- **Manager lifecycle in workers** - Worker-owned pattern validation

```python
# ✅ CORRECT: Real Qt testing
def test_worker_owns_manager_real():
    with qt_worker_test(WorkerOwnedVRAMExtractionWorker, params) as worker:
        assert worker.manager.parent() is worker
        assert worker.start_worker_and_wait(5000)

# ❌ INCORRECT: Mocked Qt testing
@patch('PyQt6.QtCore.QThread')
def test_worker_owns_manager_mocked(mock_thread):
    # This test can't validate real Qt lifecycle issues
    pass
```

#### Manager Integration Tests
- **Manager business logic** - Core functionality must be tested with real managers
- **Manager-to-manager communication** - Real dependency patterns
- **Error propagation** - Real exception handling paths
- **State management** - Real state consistency validation

```python
# ✅ CORRECT: Real manager testing
def test_extraction_manager_validation():
    with RealManagerFixtureFactory() as factory:
        manager = factory.create_extraction_manager(isolated=True)
        result = manager.validate_extraction_params(invalid_params)
        assert not result  # Tests real validation logic

# ❌ INCORRECT: Mocked manager testing  
def test_extraction_manager_validation_mocked():
    mock_manager = create_mock_extraction_manager()
    mock_manager.validate_extraction_params.return_value = False
    # This test validates nothing about real validation logic
```

#### Integration Workflows
- **Cross-component workflows** - Real component interaction
- **Dialog-to-dialog communication** - Real UI state management
- **File I/O operations** - Real file system interaction (with test data)
- **Error boundary testing** - Real error propagation paths

### 2. PREFER Real Implementations

These scenarios benefit significantly from real implementations:

#### UI Component Testing
- **Widget initialization** - Real Qt widget lifecycle
- **Dialog state management** - Real modal/non-modal behavior
- **Event handling** - Real Qt event system
- **Layout management** - Real Qt layout behavior

#### Data Processing Testing
- **Image processing** - Real PIL/Qt image operations
- **File format parsing** - Real file format validation
- **Compression operations** - Real compression algorithm testing
- **Cache operations** - Real cache behavior validation

### 3. APPROPRIATE to Mock

These scenarios where mocking provides genuine value:

#### External Dependencies
- **File system operations** (for predictable test environments)
- **Network operations** (when testing network-independent logic)
- **System calls** (for environment independence)
- **External tools** (HAL compression tools, etc.)

```python
# ✅ APPROPRIATE: Mock external dependencies
@patch('subprocess.run')
def test_hal_compression_command_generation(mock_subprocess):
    # Test command generation logic, not actual compression
    generate_hal_command(input_file, output_file)
    mock_subprocess.assert_called_with(['exhal', 'input.bin', 'output.bin'])
```

#### Performance Testing
- **Time-dependent operations** (for predictable timing)
- **Resource-intensive operations** (for fast test execution)
- **Rate limiting** (for controllable test scenarios)

#### Error Injection
- **Specific error scenarios** (when hard to reproduce with real systems)
- **Edge case testing** (when real systems make edge cases difficult)
- **Fault injection** (for testing error handling paths)

### 4. NEVER Mock

These areas where mocking is actively harmful:

#### Architectural Components
- **Qt application lifecycle** - Masks Qt lifecycle bugs
- **Manager-worker relationships** - Hides architectural issues
- **Signal/slot behavior** - Different from real Qt behavior
- **Thread safety** - Mocks can't validate thread safety

#### Core Business Logic
- **Extraction algorithms** - Core functionality must be tested
- **Injection algorithms** - Core functionality must be tested
- **Validation logic** - Real validation must be tested
- **State management** - Real state consistency is critical

## Test Infrastructure Usage

### Use TestApplicationFactory
```python
# ✅ CORRECT: Standardized Qt setup
def test_widget_with_real_qt():
    with qt_test_context() as app:
        widget = MyWidget()
        widget.show()
        # Test real Qt behavior
```

### Use RealManagerFixtureFactory
```python
# ✅ CORRECT: Real managers with proper Qt parents
def test_manager_integration():
    factory = RealManagerFixtureFactory()
    manager = factory.create_extraction_manager(isolated=True)
    # Test real manager behavior
    factory.cleanup()
```

### Use TestDataRepository
```python
# ✅ CORRECT: Real test data instead of mock data
def test_extraction_with_real_data():
    test_data = get_vram_test_data("medium")
    # Use real VRAM/CGRAM files for testing
    result = extract_sprites(test_data)
```

## Migration Patterns

### From Mock Manager to Real Manager
```python
# ❌ OLD: Mocked manager
def test_extraction_old():
    mock_manager = create_mock_extraction_manager()
    mock_manager.extract_sprites.return_value = ["sprite1.png"]
    # Test tells us nothing about real extraction

# ✅ NEW: Real manager with worker-owned pattern
def test_extraction_new():
    factory = RealManagerFixtureFactory()
    manager = factory.create_extraction_manager(isolated=True)
    result = manager.extract_sprites(real_test_params)
    assert len(result) > 0  # Tests real extraction logic
```

### From Mock Qt to Real Qt
```python
# ❌ OLD: Mocked Qt components
@patch('PyQt6.QtWidgets.QWidget')
def test_widget_old(mock_widget):
    mock_widget.return_value.show = Mock()
    # Test validates nothing about real Qt behavior

# ✅ NEW: Real Qt components
def test_widget_new():
    with qt_widget_test(MyWidget) as widget:
        widget.show()
        assert widget.isVisible()  # Tests real Qt behavior
```

## Quality Metrics

### Test Quality Indicators
- **Architectural Bug Detection**: Tests catch Qt lifecycle, threading, and manager issues
- **Real Behavior Validation**: Tests validate actual component behavior
- **Integration Coverage**: Tests validate cross-component interactions
- **Error Path Coverage**: Tests validate real error propagation

### Test Debt Indicators
- **Excessive Manager Mocking**: More than 1-2 manager mocks per test file
- **Qt Component Mocking**: Mocking QWidget, QThread, QApplication, etc.
- **Mock Complexity**: Mock setup longer than actual test logic
- **False Confidence**: Tests pass with mocks but fail with real implementations

## Implementation Guidelines

### Test File Organization
```
tests/
├── unit/           # Pure business logic, minimal mocking
├── integration/    # Real component integration, worker-owned pattern
├── ui/            # Real Qt components, real managers
└── system/        # End-to-end workflows, real everything
```

### Naming Conventions
- `test_*_real.py` - Tests using real implementations
- `test_*_integration.py` - Integration tests with real components
- `test_*_mock.py` - Tests where mocking is appropriate
- `test_*_unit.py` - Pure unit tests

### Review Checklist
- [ ] Does this test use real implementations for architectural components?
- [ ] Are Qt lifecycle, threading, and manager relationships tested with real objects?
- [ ] Is mocking limited to external dependencies and performance scenarios?
- [ ] Does the test catch bugs that mocked versions would miss?
- [ ] Is the test using proper test infrastructure (factories, contexts, etc.)?

## Migration Priority

### High Priority (Critical Bug Risk)
1. Manager lifecycle tests
2. Worker thread tests  
3. Qt parent/child relationship tests
4. Cross-component integration tests

### Medium Priority (Quality Improvement)
1. UI component tests
2. File I/O integration tests
3. Error handling tests
4. Workflow integration tests

### Low Priority (Maintainability)
1. Pure business logic tests (already appropriate)
2. External dependency tests (mocking is appropriate)
3. Performance tests (mocking may be appropriate)

## Success Criteria

A successful test taxonomy implementation will:

1. **Catch More Bugs**: New tests catch architectural issues that mocked tests missed
2. **Increase Confidence**: Developers trust tests because they use real implementations
3. **Improve Maintainability**: Tests are easier to understand and maintain
4. **Enable Safe Refactoring**: Tests provide genuine protection during architectural changes
5. **Reduce Test Debt**: Less complex mock setup, more straightforward test logic

This taxonomy is living documentation that should be updated as we learn more about effective testing patterns in SpritePal.