# Safe Fixtures Guide

## Overview

Safe fixtures provide a comprehensive solution for preventing Qt initialization crashes in headless environments while maintaining full test compatibility. They automatically detect the environment and provide appropriate implementations (real Qt or mock) without requiring test code changes.

## Key Features

- **Environment Auto-Detection**: Automatically detects headless vs GUI environments
- **Crash Prevention**: Prevents segfaults during Qt initialization in headless mode
- **API Compatibility**: Maintains same API as pytest-qt fixtures
- **Fallback Mechanisms**: Graceful fallbacks when Qt components fail
- **Resource Management**: Automatic cleanup and resource management
- **Performance Optimization**: Session-scoped fixtures and caching
- **Type Safety**: Full type hints and protocol-based interfaces

## Quick Start

### Basic Usage

```python
def test_my_component(enhanced_safe_qtbot, enhanced_safe_qapp):
    """Test using safe fixtures - works in any environment."""
    # qtbot works the same as pytest-qt qtbot
    enhanced_safe_qtbot.wait(100)
    
    # QApplication works normally
    enhanced_safe_qapp.processEvents()
    
    # Create widgets safely
    widget = MyWidget()
    enhanced_safe_qtbot.addWidget(widget)
```

### Widget and Dialog Creation

```python
def test_widget_creation(safe_widget_factory_fixture, safe_dialog_factory_fixture):
    """Test safe widget and dialog creation."""
    # Create widgets - real or mock based on environment
    widget = safe_widget_factory_fixture.create_widget('QWidget')
    widget.show()
    
    # Create dialogs - crash-safe in all environments
    dialog = safe_dialog_factory_fixture.create_dialog('QDialog')
    result = dialog.exec()  # Returns mock result in headless mode
```

### Complete Qt Environment

```python
def test_complete_environment(safe_qt_environment):
    """Test with complete Qt environment."""
    qt_env = safe_qt_environment
    
    # Access all components
    qtbot = qt_env['qtbot']
    qapp = qt_env['qapp'] 
    widget_factory = qt_env['widget_factory']
    dialog_factory = qt_env['dialog_factory']
    env_info = qt_env['env_info']
    
    # Use as needed
    if not env_info.is_headless:
        # Real Qt operations
        pass
    else:
        # Mock operations
        pass
```

## Fixture Types

### Core Fixtures

#### `enhanced_safe_qtbot`
- **Scope**: Function
- **Type**: `SafeQtBotProtocol`
- **Description**: Safe qtbot that works in both headless and GUI environments
- **API**: Compatible with pytest-qt qtbot

```python
def test_qtbot_usage(enhanced_safe_qtbot):
    # All standard qtbot operations work
    enhanced_safe_qtbot.wait(timeout=1000)
    blocker = enhanced_safe_qtbot.waitSignal(signal, timeout=5000)
    enhanced_safe_qtbot.addWidget(widget)
    enhanced_safe_qtbot.keyPress(widget, Qt.Key_Return)
    enhanced_safe_qtbot.mouseClick(widget, Qt.LeftButton)
```

#### `enhanced_safe_qapp`
- **Scope**: Session
- **Type**: `SafeQApplicationProtocol`  
- **Description**: Safe QApplication with singleton handling
- **API**: Compatible with QApplication

```python
def test_qapp_usage(enhanced_safe_qapp):
    # Standard QApplication operations
    enhanced_safe_qapp.processEvents()
    enhanced_safe_qapp.quit()
    screen = enhanced_safe_qapp.primaryScreen()
```

### Factory Fixtures

#### `safe_widget_factory_fixture`
- **Scope**: Function
- **Type**: `SafeWidgetFactory`
- **Description**: Factory for creating Qt widgets safely

```python
def test_widget_factory(safe_widget_factory_fixture):
    factory = safe_widget_factory_fixture
    
    # Create various widgets
    widget = factory.create_widget('QWidget')
    dialog = factory.create_widget('QDialog')
    
    # Custom widgets (if available)
    try:
        custom_widget = factory.create_widget(MyCustomWidget)
    except WidgetCreationError:
        # Handle creation failure
        pass
```

#### `safe_dialog_factory_fixture`
- **Scope**: Function
- **Type**: `SafeDialogFactory`
- **Description**: Factory for creating Qt dialogs safely

```python
def test_dialog_factory(safe_dialog_factory_fixture):
    factory = safe_dialog_factory_fixture
    
    # Create dialogs with crash prevention
    dialog = factory.create_dialog('QDialog')
    message_box = factory.create_dialog('QMessageBox')
    file_dialog = factory.create_dialog('QFileDialog')
```

### Environment-Specific Fixtures

#### `real_qtbot`
- **Description**: Forces real pytest-qt qtbot (skips in headless)
- **Use Case**: Integration tests requiring real Qt behavior

```python
@pytest.mark.qt_real
def test_real_qt_required(real_qtbot):
    # This test requires real Qt and will be skipped in headless environments
    real_qtbot.waitSignal(real_signal)
```

#### `mock_qtbot`
- **Description**: Forces mock qtbot implementation
- **Use Case**: Unit tests that should always use mocks

```python
@pytest.mark.qt_mock
def test_always_mock(mock_qtbot):
    # This test always uses mocks regardless of environment
    mock_qtbot.wait(1000)  # Returns immediately
```

#### `adaptive_qtbot`
- **Description**: Chooses implementation based on test markers
- **Use Case**: Tests that can work with either real or mock Qt

```python
def test_adaptive(adaptive_qtbot):
    # Uses real qtbot if marked @pytest.mark.qt_real
    # Uses mock qtbot if marked @pytest.mark.qt_mock  
    # Uses safe qtbot (auto-detect) if unmarked
    adaptive_qtbot.wait(100)
```

## Environment Detection

### Automatic Detection

The safe fixtures automatically detect:
- **Headless environments** (CI, Docker, no DISPLAY)
- **GUI environments** (desktop with display) 
- **xvfb availability** (virtual display for testing)
- **Qt availability** (PySide6 installation)

### Manual Override

```python
# Force headless mode
def test_force_headless(fixture_validation_report):
    if not fixture_validation_report['environment']['headless']:
        pytest.skip("This test requires headless mode")

# Require GUI mode
@pytest.mark.skipif(is_headless_environment(), reason="Requires GUI")
def test_requires_gui(enhanced_safe_qtbot):
    pass
```

## Error Handling and Fallbacks

### Automatic Fallbacks

Safe fixtures provide multiple levels of fallback:

1. **Qt Available + GUI Environment**: Real Qt components
2. **Qt Available + Headless Environment**: Offscreen Qt or mocks
3. **Qt Unavailable**: Mock components with compatible API
4. **Component Creation Failure**: Mock fallbacks

### Error Recovery

```python
def test_with_error_recovery(safe_qt_environment):
    qt_env = safe_qt_environment
    
    # Check if components are available
    if qt_env['qtbot'] is None:
        pytest.skip("QtBot not available in this environment")
    
    # Environment info always available
    env_info = qt_env['env_info']
    if env_info.is_headless:
        # Adjust test behavior for headless mode
        pass
```

### Custom Error Handling

```python
from tests.infrastructure.safe_fixtures import report_fixture_error

def test_custom_error_handling():
    try:
        qtbot = create_safe_qtbot()
    except Exception as e:
        report_fixture_error('custom_qtbot', e)
        pytest.skip(f"QtBot creation failed: {e}")
```

## Advanced Usage

### Fixture Factory Pattern

```python
from tests.infrastructure.fixture_factory import QtFixtureFactory, FixtureConfiguration

def test_custom_factory():
    # Create custom configuration
    config = FixtureConfiguration(
        headless_override=True,
        strict_mode=False,
        enable_debug_logging=True
    )
    
    # Create factory
    factory = QtFixtureFactory(config)
    
    # Create fixtures
    qtbot = factory.create_qtbot()
    qapp = factory.create_qapp()
    
    # Use context manager
    with factory.qt_context() as qt_env:
        # Complete Qt environment available
        pass
    
    # Cleanup
    factory.cleanup_all()
```

### Performance Optimization

```python
from tests.infrastructure.fixture_factory import create_performance_qt_factory

@pytest.fixture(scope="session")
def performance_qt():
    """Session-scoped Qt environment for performance."""
    factory = create_performance_qt_factory()
    yield factory
    factory.cleanup_all()

def test_with_performance_qt(performance_qt):
    qtbot = performance_qt.create_qtbot()
    # Uses cached/session-scoped components for speed
```

### Development and Debugging

```python
from tests.infrastructure.fixture_factory import create_development_qt_factory

def test_with_debugging():
    factory = create_development_qt_factory()
    
    # Get detailed statistics
    stats = factory.get_statistics()
    print(f"Environment: {stats['environment']}")
    print(f"Fixtures: {stats['fixtures_created']}")
    
    # Enable debug logging
    import os
    os.environ['PYTEST_DEBUG_FIXTURES'] = '1'
    
    qtbot = factory.create_qtbot()
    factory.cleanup_all()
```

## Integration with Existing Tests

### Migration from pytest-qt

Safe fixtures are designed to be drop-in replacements:

```python
# OLD - using pytest-qt directly
def test_old_way(qtbot, qapp):
    qtbot.wait(1000)
    qapp.processEvents()

# NEW - using safe fixtures (same API)
def test_new_way(enhanced_safe_qtbot, enhanced_safe_qapp):
    enhanced_safe_qtbot.wait(1000)
    enhanced_safe_qapp.processEvents()
```

### Gradual Migration

```python
# Use adaptive fixtures during migration
def test_gradual_migration(adaptive_qtbot):
    # Works with both old and new fixture systems
    adaptive_qtbot.wait(100)
    
# Mark tests explicitly during migration
@pytest.mark.qt_mock  # Force mock during migration
def test_mock_during_migration(adaptive_qtbot):
    pass

@pytest.mark.qt_real  # Force real Qt when ready
def test_real_when_ready(adaptive_qtbot):
    pass
```

## Test Markers

Safe fixtures work with pytest markers for fine-grained control:

- `@pytest.mark.qt_real`: Force real Qt components
- `@pytest.mark.qt_mock`: Force mock components  
- `@pytest.mark.headless`: Test is headless-safe
- `@pytest.mark.gui`: Test requires GUI environment
- `@pytest.mark.no_qt`: Test has no Qt dependencies

## Configuration

### Environment Variables

- `PYTEST_DEBUG_FIXTURES=1`: Enable debug logging
- `HEADLESS=1`: Force headless mode
- `QT_QPA_PLATFORM=offscreen`: Use offscreen Qt platform

### pytest.ini Configuration

```ini
[tool:pytest]
markers =
    qt_real: Tests requiring real Qt components
    qt_mock: Tests using mock Qt components  
    headless: Tests safe for headless environments
    gui: Tests requiring GUI environment

# Safe fixture debugging
addopts = --tb=short
log_cli_level = INFO
```

## Troubleshooting

### Common Issues

1. **"Fatal Python error: Aborted"**
   - Cause: Real Qt widgets in headless environment
   - Solution: Use safe fixtures which auto-detect environment

2. **"QApplication not found"**
   - Cause: Missing PySide6 installation
   - Solution: Safe fixtures automatically fall back to mocks

3. **"Segmentation fault"**
   - Cause: Qt initialization in incompatible environment
   - Solution: Environment detection prevents this

### Debug Mode

```python
import os
os.environ['PYTEST_DEBUG_FIXTURES'] = '1'

def test_debug_mode(fixture_validation_report):
    # Get detailed environment report
    print("Environment:", fixture_validation_report['environment'])
    print("Fixtures:", fixture_validation_report['fixtures']) 
    print("Errors:", fixture_validation_report['errors'])
```

### Validation

```python
def test_fixture_validation(fixture_validation_report):
    """Validate fixture environment before testing."""
    report = fixture_validation_report
    
    # Check for critical errors
    if report['errors']:
        pytest.skip(f"Fixture validation failed: {report['errors']}")
    
    # Verify required fixtures work
    assert report['fixtures']['qtbot_created']
    assert report['fixtures']['qapp_created']
```

## Best Practices

### 1. Use Appropriate Fixture Scope

```python
# Session scope for expensive setup
@pytest.fixture(scope="session")
def session_qt_factory():
    factory = QtFixtureFactory()
    yield factory
    factory.cleanup_all()

# Function scope for isolation
def test_isolated(enhanced_safe_qtbot):
    # Fresh qtbot for each test
    pass
```

### 2. Handle Environment Differences

```python
def test_environment_aware(safe_qt_environment):
    qt_env = safe_qt_environment
    env_info = qt_env['env_info']
    
    if env_info.is_headless:
        # Adjust expectations for headless mode
        timeout = 10000  # Longer timeout in headless
    else:
        timeout = 1000   # Normal timeout in GUI
        
    qt_env['qtbot'].wait(timeout)
```

### 3. Clean Error Handling

```python
def test_with_fallback(enhanced_safe_qtbot):
    try:
        # Attempt operation that might fail
        enhanced_safe_qtbot.waitSignal(complex_signal, timeout=5000)
    except Exception:
        # Graceful degradation
        pytest.skip("Signal testing not available in this environment")
```

### 4. Performance Considerations

```python
# Use session-scoped fixtures for expensive operations
@pytest.fixture(scope="session")
def expensive_qt_setup(enhanced_safe_qapp):
    # Expensive setup once per session
    setup_expensive_qt_components()
    yield
    cleanup_expensive_qt_components()

def test_performance(expensive_qt_setup, enhanced_safe_qtbot):
    # Fast test using pre-setup environment
    pass
```

## Examples

### Complete Test Example

```python
import pytest
from tests.infrastructure.safe_fixtures import create_safe_qtbot

class TestMyWidget:
    """Example test class using safe fixtures."""
    
    def test_widget_creation(self, safe_widget_factory_fixture):
        """Test widget creation in any environment."""
        factory = safe_widget_factory_fixture
        widget = factory.create_widget('QWidget')
        assert widget is not None
        widget.show()
    
    def test_signal_handling(self, enhanced_safe_qtbot):
        """Test Qt signals with safe qtbot."""
        qtbot = enhanced_safe_qtbot
        
        # Create mock signal
        from unittest.mock import Mock
        signal = Mock()
        
        # Wait for signal (mock or real)
        with qtbot.waitSignal(signal, timeout=1000) as blocker:
            signal.emit()  # Trigger signal
            
        # Verify signal was handled
        assert blocker is not None
    
    def test_environment_specific(self, safe_qt_environment):
        """Test that adapts to environment."""
        qt_env = safe_qt_environment
        
        if qt_env['env_info'].is_headless:
            # Headless-specific testing
            assert qt_env['qtbot'] is not None  # Mock qtbot
        else:
            # GUI-specific testing  
            qt_env['qapp'].processEvents()  # Real processing
    
    @pytest.mark.qt_real
    def test_real_qt_only(self, real_qtbot):
        """Test that requires real Qt (skipped in headless)."""
        # This test will be skipped in headless environments
        real_qtbot.wait(100)
        
    @pytest.mark.qt_mock
    def test_mock_qt_only(self, mock_qtbot):
        """Test that always uses mocks."""
        # This test always uses mocks regardless of environment
        mock_qtbot.wait(1000)  # Returns immediately
```

## Migration Guide

### From pytest-qt to Safe Fixtures

1. **Replace fixture names**:
   - `qtbot` → `enhanced_safe_qtbot`
   - `qapp` → `enhanced_safe_qapp`

2. **Add factory fixtures for widget creation**:
   - Add `safe_widget_factory_fixture` parameter
   - Use `factory.create_widget()` instead of direct instantiation

3. **Update imports**:
   ```python
   # Add to test files
   from tests.infrastructure.safe_fixtures import create_safe_qtbot
   ```

4. **Add environment awareness**:
   ```python
   # Check environment when needed
   def test_with_env_check(safe_qt_environment):
       if safe_qt_environment['env_info'].is_headless:
           pytest.skip("Requires GUI environment")
   ```

5. **Test migration**:
   ```bash
   # Test in headless mode
   HEADLESS=1 pytest tests/
   
   # Test with GUI
   pytest tests/
   
   # Test with debug info
   PYTEST_DEBUG_FIXTURES=1 pytest tests/ -v
   ```

This guide provides comprehensive coverage of safe fixtures usage. The fixtures are designed to be robust, performant, and easy to use while preventing Qt-related crashes in any environment.
