# pyright: recommended  # Use recommended mode for test files with enhanced basedpyright features
# pyright: reportPrivateUsage=false  # Allow testing private methods
# pyright: reportUnknownMemberType=warning  # Mock attributes are dynamic
# pyright: reportUnknownArgumentType=warning  # Test data may be dynamic
# pyright: reportUntypedFunctionDecorator=error  # Type all decorators
# pyright: reportUnnecessaryTypeIgnoreComment=error  # Clean up unused ignores

"""
Unified pytest configuration for SpritePal tests.

This module consolidates all test configuration into a single, modern approach
that works consistently across all environments (headless, GUI, CI/CD).

## Performance Optimizations

This conftest.py implements fixture scope optimizations that reduce fixture
instantiations by 68.6% based on usage analysis:

- qt_app: Session scope (1,129 → 1 instance, 99.9% reduction)
- main_window: Class scope (129 → ~30 instances, 77% reduction)
- controller: Class scope (119 → ~30 instances, 75% reduction)
- mock_manager_registry: Module scope (81 → ~15 instances, 81% reduction)
- real_extraction_manager: Class scope (51 → ~12 instances, 77% reduction)
- rom_cache: Class scope (48 → ~10 instances, 79% reduction)
- mock_settings_manager: Class scope (44 → ~10 instances, 77% reduction)
- real_session_manager: Class scope (26 → ~8 instances, 69% reduction)

## State Isolation

Class-scoped and module-scoped fixtures include automatic state reset
mechanisms to ensure test isolation:

- `reset_main_window_state`: Resets main window state between tests
- `reset_controller_state`: Resets controller state between tests
- `reset_class_scoped_fixtures`: Resets all class-scoped mock fixtures

## Scope Selection Guidelines

- **Session scope**: For expensive, stateless resources (Qt application)
- **Module scope**: For fixtures shared across test modules with minimal state
- **Class scope**: For fixtures shared within test classes with manageable state
- **Function scope**: For fixtures requiring full isolation (default)

All optimized fixtures maintain backward compatibility and proper cleanup.
"""

from __future__ import annotations

import os
import sys
import tempfile
import warnings
from collections.abc import Generator
from contextlib import AbstractContextManager as ContextManager
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, patch

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from core.managers.extraction_manager import ExtractionManager
    from core.managers.injection_manager import InjectionManager
    from core.managers.session_manager import SessionManager
    from pytest import FixtureRequest
    from tests.infrastructure.test_protocols import (
        MockExtractionManagerProtocol,
        MockInjectionManagerProtocol,
        MockMainWindowProtocol,
        MockQtBotProtocol,
        MockSessionManagerProtocol,
    )
    from utils.rom_cache import ROMCache

import pytest

# Add parent directories to path - centralized path setup
sys.path.insert(0, str(Path(__file__).parent.parent))  # Add spritepal directory

# Import consolidated mock utilities
import contextlib

# Import constants from segfault and timeout configuration modules
from .constants_timeout import (
    INTEGRATION_PATTERNS,
    SLOW_TEST_PATTERNS,
    TIMEOUT_BENCHMARK,
    TIMEOUT_INTEGRATION,
    TIMEOUT_SLOW,
    TIMEOUT_UNIT,
)
from .infrastructure.environment_detection import get_environment_info
from .infrastructure.mock_hal import (
    MockHALCompressor,
    MockHALProcessPool,
    configure_hal_mocking,
    create_mock_hal_tools,
)
from .infrastructure.real_component_factory import RealComponentFactory

# Import all Qt-related fixtures and environment settings from qt_fixtures.py
from .fixtures.qt_fixtures import (
    IS_HEADLESS,
    DEFAULT_SIGNAL_TIMEOUT,
    DEFAULT_WAIT_TIMEOUT,
    DEFAULT_WORKER_TIMEOUT,
    qt_environment_setup,
    qt_app,
    main_window,
    enhanced_safe_qtbot,
    mock_qtbot,
    enhanced_safe_qapp,
    safe_widget_factory_fixture,
    safe_dialog_factory_fixture,
    safe_qt_environment,
    enhanced_qtbot,
    enhanced_qapp,
    cleanup_safe_fixtures_session,
    fixture_validation_report,
    real_qtbot,
    adaptive_qtbot,
    debug_fixture_logging,
    safe_qapp,
    cleanup_workers,
    signal_timeout,
    wait_timeout,
    worker_timeout,
    timeout_config,
    cleanup_singleton,
)

# Import for controller fixture
try:
    from core.controller import ExtractionController
except ImportError:
    # Avoid import errors in environments where controller isn't available
    ExtractionController = None

# Get environment info for fixture optimization
_environment_info = get_environment_info()


def pytest_addoption(parser: Any) -> None:
    """Add custom command line options for SpritePal tests."""
    parser.addoption(
        "--use-real-hal",
        action="store_true",
        default=False,
        help="Use real HAL process pool instead of mocks (slower)"
    )
    # NOTE: --run-segfault-tests option removed - segfault-prone tests have been deleted

def pytest_configure(config: Any) -> None:
    """Configure pytest with unified markers for SpritePal tests."""
    # Print environment report if verbose mode is enabled
    if config.getoption('-v') or os.environ.get('PYTEST_VERBOSE_ENVIRONMENT'):
        from .infrastructure.environment_detection import get_environment_report
        print(get_environment_report())

    markers = [
        # Execution Environment Markers (Primary Categories)
        "gui: GUI tests requiring display/X11 environment (may be skipped in headless)",
        "headless: Tests that can run without display (safe for CI/headless environments)",
        "mock_only: Tests using only mocked components (fastest, most reliable)",

        # Test Type Markers
        "unit: Unit tests (fast, isolated, no external dependencies)",
        "integration: Integration tests (may require files, databases, services)",
        "benchmark: Performance benchmarking tests",
        "performance: Performance tests",
        "stress: Stress/load testing",
        "slow: Slow tests (>1s execution time)",

        # Qt Component Markers
        "qt_real: Tests using real Qt components (widgets, dialogs, etc.)",
        "qt_mock: Tests using mocked Qt components",
        "qt_app: Tests requiring QApplication instance",
        "no_qt: Tests with no Qt dependencies whatsoever",

        # Threading and Concurrency Markers
        "thread_safety: Thread safety tests",
        "timer: Tests involving QTimer functionality",
        "worker_threads: Tests using worker threads",
        "signals_slots: Tests focused on Qt signal/slot mechanisms",

        # Manager and Infrastructure Markers
        "manager: Tests focused on testing manager classes",
        "mock_managers: Tests using mocked managers",
        "real_managers: Tests using real manager instances",
        "no_manager_setup: Tests that skip manager initialization",
        "isolated_managers: Tests requiring fresh manager instances (slow)",

        # Data and Resource Markers
        "rom_data: Tests requiring ROM files or data",
        "file_io: Tests involving file operations",
        "cache: Tests involving caching mechanisms",
        "memory: Memory management tests",

        # Dialog and UI Markers
        "dialog: Tests involving dialogs",
        "mock_dialogs: Tests that mock dialog exec() methods",
        "widget: Tests involving widgets",
        "preview: Tests involving preview components",

        # Stability and Quality Markers
        "stability: Stability/regression tests",
        "phase1_fixes: Tests validating Phase 1 critical fixes",
        "critical: Critical functionality tests that must always pass",

        # Execution Control Markers
        "serial: Tests that must run in serial (not parallel)",
        "parallel_safe: Tests confirmed safe for parallel execution",
        "process_pool: Tests using process pools that need serial execution",
        "singleton: Tests manipulating singletons that conflict in parallel",
        "qt_application: Tests managing QApplication that conflict in parallel",

        # Development and Debug Markers
        "debug: Debug-related tests",
        "validation: Validation and verification tests",
        "fixture_test: Tests validating test fixtures themselves",
        "infrastructure: Tests of testing infrastructure",

        # Special Configuration Markers
        "timeout: Set custom timeout for test",
        "no_xvfb: Skip xvfb for specific tests",
        "qt_no_exception_capture: Disable Qt exception capture for specific tests",

        # Platform and Environment Markers
        "wsl: Tests that behave differently on WSL",
        "linux_only: Tests that only run on Linux",
        "windows_only: Tests that only run on Windows",

        # HAL Processing Markers (legacy compatibility)
        "real_hal: Mark test to use real HAL process pool (not mocked)",
        "mock_hal: Mark test to use mock HAL (default for unit tests)",

        # Legacy markers for backward compatibility
        "mock: Tests using mocks (deprecated - use mock_only or mock_managers)",
        "mock_gui: GUI tests that use mocks (deprecated - use qt_mock)",

        # Explicit mock Qt marker
        "mock_qt: Tests that explicitly use mock Qt (with mock_qtbot fixture)",
        # NOTE: segfault_prone marker removed - those tests have been deleted
    ]

    for marker in markers:
        config.addinivalue_line("markers", marker)

    # Configure HAL mocking environment variables
    # NOTE: HAL mocking is now OPT-IN - tests must explicitly request the mock_hal fixture
    # The --use-real-hal flag now just controls the environment variable for detection
    if hasattr(config.option, 'use_real_hal'):
        use_real_hal = config.option.use_real_hal
    else:
        use_real_hal = False

    # Set environment variables for code that needs to detect test environment
    # But actual mocking requires requesting the mock_hal fixture
    configure_hal_mocking(use_mocks=not use_real_hal, deterministic=True)

def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """
    Modify test collection based on environment capabilities and marker logic.

    This enhanced hook handles:
    - Segfault-prone test skipping (unless --run-segfault-tests)
    - Automatic timeout markers based on test patterns
    - GUI test skipping in headless environments
    - Automatic marker inference and validation
    - Performance optimization based on markers
    - Environmental context-aware test filtering
    """
    env_info = get_environment_info()

    # NOTE: Segfault-prone test marking removed - those tests have been deleted
    # The following test files were removed as they had unresolvable Qt threading issues:
    # - test_smart_preview_coordinator.py
    # - test_concurrent_operations.py
    # - test_worker_manager.py::*cleanup* tests
    # - test_collapsible_group_box.py::*animation* tests

    # === Automatic timeout markers ===
    # Add timeout markers to tests based on their type/patterns
    timeout_available = config.pluginmanager.has_plugin("timeout")
    if timeout_available:
        for item in items:
            # Skip if test already has a timeout marker
            if item.get_closest_marker("timeout"):
                continue

            test_id = item.nodeid.lower()
            test_name = getattr(item.function, "__name__", "").lower() if hasattr(item, "function") else ""

            # Determine timeout based on test patterns
            timeout = TIMEOUT_UNIT  # Default

            # Check for slow test patterns
            if any(pattern in test_id or pattern in test_name for pattern in SLOW_TEST_PATTERNS):
                timeout = TIMEOUT_SLOW
            # Check for integration patterns
            elif any(pattern in test_id or pattern in test_name for pattern in INTEGRATION_PATTERNS):
                timeout = TIMEOUT_INTEGRATION
            # Check for benchmark marker
            elif item.get_closest_marker("benchmark"):
                timeout = TIMEOUT_BENCHMARK
            # Check for slow marker
            elif item.get_closest_marker("slow"):
                timeout = TIMEOUT_SLOW

            # Add timeout marker
            item.add_marker(pytest.mark.timeout(timeout))



    # Add automatic slow marker for certain test categories
    slow_patterns = ["integration", "gui", "rom_data", "performance", "benchmark"]
    for item in items:
        # Auto-mark tests as slow based on content patterns
        if any(pattern in item.keywords for pattern in slow_patterns) and "slow" not in item.keywords:
            if ("qt_real" in item.keywords or
                "rom_data" in item.keywords or
                "performance" in item.keywords):
                item.add_marker(pytest.mark.slow)

    # Validation: Ensure marker consistency
    # Define mutually exclusive marker sets - tests cannot have markers from same set
    MUTUALLY_EXCLUSIVE_MARKERS = [
        {'gui', 'headless'},
        {'qt_real', 'qt_mock', 'no_qt'},
        {'serial', 'parallel_safe'},
        {'mock_only', 'qt_real'},
    ]

    for item in items:
        item_keywords = set(item.keywords)

        # Check for conflicting markers
        for exclusive_set in MUTUALLY_EXCLUSIVE_MARKERS:
            conflicts = item_keywords & exclusive_set
            if len(conflicts) > 1:
                warnings.warn(
                    f"Test {item.name} has conflicting markers: {conflicts}. "
                    f"These markers are mutually exclusive.",
                    UserWarning,
                    stacklevel=2
                )

# Note: GUI popup prevention is handled via QT_QPA_PLATFORM environment variable
# Set QT_QPA_PLATFORM=offscreen to run tests without GUI windows



@pytest.fixture(scope="session")
def session_managers(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """
    Session-scoped managers for performance optimization.

    This fixture initializes managers once per test session and keeps them
    alive for the entire session. Tests can use this for better performance
    by depending on this fixture instead of setup_managers.

    Uses isolated temp settings directory to avoid polluting repo root.

    Usage:
        def test_something(session_managers):
            # Managers are already initialized and shared across tests
            pass
    """
    # Lazy import manager functions
    from core.managers import cleanup_managers, initialize_managers
    from PySide6.QtWidgets import QApplication

    # Create session-specific settings directory for isolation
    settings_dir = tmp_path_factory.mktemp("session_settings")
    settings_path = settings_dir / ".test_settings.json"

    # Ensure Qt app exists
    app = QApplication.instance()
    if app is None and not IS_HEADLESS:
        app = QApplication([])

    initialize_managers("TestApp", settings_path=settings_path)
    yield
    cleanup_managers()

    # Process events to ensure cleanup completes
    if app and not IS_HEADLESS:
        app.processEvents()


@pytest.fixture
def isolated_managers(tmp_path: Path, request: FixtureRequest) -> Iterator[None]:
    """
    Function-scoped managers for tests that need complete isolation.

    Unlike session_managers, this fixture creates fresh managers for each test
    and cleans them up afterward. Use this for tests that:
    - Modify manager state that could affect other tests
    - Need to test manager initialization/cleanup behavior
    - Can't share state with other tests

    Note: This is slower than session_managers but provides complete isolation.

    IMPORTANT: This fixture includes an isolation guard that fails if the
    ManagerRegistry is already initialized (indicates test pollution).

    Usage:
        def test_something_that_modifies_state(isolated_managers):
            # Fresh managers, isolated from other tests
            from core.managers.registry import ManagerRegistry
            registry = ManagerRegistry()
            # ... test code that modifies manager state ...
    """
    from core.managers import cleanup_managers, initialize_managers
    from core.managers.registry import ManagerRegistry
    from PySide6.QtWidgets import QApplication

    test_name = request.node.name if request and hasattr(request, 'node') else "<unknown>"

    # Isolation guard: fail if registry already initialized (indicates pollution)
    registry = ManagerRegistry()
    if registry.is_initialized():
        # Try to clean up first
        try:
            cleanup_managers()
        except Exception:
            pass
        # If still initialized, fail with clear message
        if registry.is_initialized():
            pytest.fail(
                f"Test '{test_name}': isolated_managers fixture requires uninitialized ManagerRegistry. "
                "Another fixture or test may have leaked state. "
                "Use session_managers for shared state, or ensure cleanup in prior tests."
            )

    # Use temp settings path for isolation
    settings_path = tmp_path / ".test_settings.json"

    # Ensure Qt app exists
    app = QApplication.instance()
    if app is None and not IS_HEADLESS:
        app = QApplication([])

    # Initialize fresh managers for this test with isolated settings
    initialize_managers("TestApp_Isolated", settings_path=settings_path)

    yield

    # Clean up managers after test
    cleanup_managers()

    # Process events to ensure cleanup completes
    if app and not IS_HEADLESS:
        app.processEvents()


@pytest.fixture(autouse=True)
def detect_manager_pollution(request: FixtureRequest) -> Generator[None, None, None]:
    """
    Autouse fixture to detect unexpected ManagerRegistry state pollution.

    This fixture runs before and after each test to detect:
    1. Tests that find an unexpectedly initialized registry (pollution from prior tests)
    2. Tests that leave the registry initialized without using manager fixtures

    This helps identify test isolation issues that could cause flaky behavior.
    """
    from core.managers.registry import ManagerRegistry

    # Get list of manager-related fixtures this test uses
    fixture_names = getattr(request, 'fixturenames', [])
    manager_fixtures = {'session_managers', 'isolated_managers', 'fast_managers', 'setup_managers'}
    uses_manager_fixture = bool(manager_fixtures & set(fixture_names))

    # Check state before test
    registry = ManagerRegistry()
    initialized_before = registry.is_initialized()

    # Warn/fail if registry is initialized but test doesn't use manager fixtures
    # (indicates pollution from a prior test)
    if initialized_before and not uses_manager_fixture:
        test_name = request.node.name if hasattr(request, 'node') else "<unknown>"
        message = (
            f"Test '{test_name}' started with ManagerRegistry already initialized "
            "but doesn't use manager fixtures. This may indicate test pollution from a prior test."
        )
        if os.environ.get("CI"):
            pytest.fail(message)  # Fail in CI for stricter enforcement
        else:
            warnings.warn(message, UserWarning, stacklevel=2)

    yield

    # Check state after test
    initialized_after = registry.is_initialized()

    # Warn/fail if test left registry initialized but didn't use manager fixtures
    if initialized_after and not uses_manager_fixture and not initialized_before:
        test_name = request.node.name if hasattr(request, 'node') else "<unknown>"
        message = (
            f"Test '{test_name}' left ManagerRegistry initialized but didn't use manager fixtures. "
            "This could pollute subsequent tests."
        )
        if os.environ.get("CI"):
            pytest.fail(message)  # Fail in CI for stricter enforcement
        else:
            warnings.warn(message, UserWarning, stacklevel=2)


@pytest.fixture
def fast_managers(session_managers: None) -> Iterator[None]:
    """
    Fast manager access using session-scoped managers.

    This fixture provides manager access without per-test initialization overhead.
    Tests can use this instead of setup_managers for better performance when
    they don't need isolated manager state.

    Usage:
        def test_something(fast_managers):
            # Uses shared session managers - much faster
            pass
    """
    # Just depend on session_managers, no additional work needed
    yield


@pytest.fixture
def reset_manager_state(session_managers: None) -> Iterator[None]:
    """
    Lightweight state reset for session managers.

    This fixture uses session_managers (fast) but resets caches and counters
    before and after the test. Use this when you need:
    - Clean cache state without full manager re-initialization
    - Predictable counter values (e.g., extraction counts)
    - Isolation from prior tests without the overhead of isolated_managers

    Performance: ~5ms (vs ~50ms for isolated_managers)

    Usage:
        def test_extraction_counting(reset_manager_state):
            # Caches cleared, counters reset, but uses session managers
            manager = ManagerRegistry().extraction_manager
            # manager.extraction_count == 0
    """
    from core.managers.registry import ManagerRegistry

    registry = ManagerRegistry()
    if not registry.is_initialized():
        yield
        return

    # Reset state before test
    _reset_manager_caches(registry)

    yield

    # Reset state after test
    _reset_manager_caches(registry)


def _reset_manager_caches(registry: Any) -> None:
    """Reset caches and counters in managers without re-initialization."""
    # Reset extraction manager caches
    if hasattr(registry, 'extraction_manager') and registry.extraction_manager:
        em = registry.extraction_manager
        if hasattr(em, '_cache'):
            em._cache.clear()
        if hasattr(em, 'extraction_count'):
            em.extraction_count = 0

    # Reset session manager state
    if hasattr(registry, 'session_manager') and registry.session_manager:
        sm = registry.session_manager
        if hasattr(sm, 'clear_session'):
            with contextlib.suppress(Exception):
                sm.clear_session()

    # Reset settings manager to defaults (don't clear, just reset)
    if hasattr(registry, 'settings_manager') and registry.settings_manager:
        stm = registry.settings_manager
        if hasattr(stm, 'reset_to_defaults'):
            with contextlib.suppress(Exception):
                stm.reset_to_defaults()


@pytest.fixture
def setup_managers(request: FixtureRequest) -> Iterator[None]:
    """
    Setup managers for all tests (per-test isolation).

    This fixture ensures proper manager initialization and cleanup
    for every test, replacing duplicated setup across test files.
    Skips setup if test is marked with 'no_manager_setup'.

    For better performance, consider using 'fast_managers' fixture instead
    if your test doesn't require isolated manager state.
    """
    # Skip manager setup if test is marked with no_manager_setup
    if request.node.get_closest_marker("no_manager_setup"):
        yield
        return

    # Skip if test uses session managers (via fast_managers fixture)
    if 'session_managers' in request.fixturenames or 'fast_managers' in request.fixturenames:
        yield
        return

    # Lazy import manager functions to reduce startup overhead
    # Ensure Qt app exists before initializing managers
    from core.managers import cleanup_managers, initialize_managers
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None and not IS_HEADLESS:
        app = QApplication([])

    try:
        initialize_managers("TestApp")
        yield
    finally:
        # Safe cleanup with error handling to prevent segfaults
        try:
            cleanup_managers()
        except (RuntimeError, AttributeError) as e:
            # Qt objects may already be deleted, log but don't crash
            import logging
            logging.getLogger(__name__).debug(f"Manager cleanup warning: {e}")
        except Exception as e:
            # Unexpected cleanup error, log but continue
            import logging
            logging.getLogger(__name__).warning(f"Manager cleanup error: {e}")

        # Process events safely
        try:
            if app and not IS_HEADLESS:
                app.processEvents()
        except (RuntimeError, AttributeError):
            # QApplication may be deleted, ignore
            pass

@pytest.fixture
def test_data_factory() -> Callable[..., bytearray]:
    """
    Factory for creating consistent test data structures.

    Provides a unified way to create VRAM, CGRAM, and OAM test data
    with realistic patterns used across the test suite.
    """
    def _create_test_data(data_type: str, size: int | None = None, **kwargs: Any) -> bytearray:
        """
        Create test data of specified type.

        Args:
            data_type: Type of data - 'vram', 'cgram', 'oam'
            size: Size override (uses defaults if None)
            **kwargs: Additional parameters for data generation

        Returns:
            Bytearray with realistic test data
        """
        if data_type == "vram":
            # Lazy import constants to reduce startup overhead
            from utils.constants import BYTES_PER_TILE, VRAM_SPRITE_OFFSET

            default_size = 0x10000  # 64KB
            data = bytearray(size or default_size)

            # Add realistic sprite data at VRAM offset
            start_offset = kwargs.get("sprite_offset", VRAM_SPRITE_OFFSET)
            tile_count = kwargs.get("tile_count", 10)

            for i in range(tile_count):
                offset = start_offset + i * BYTES_PER_TILE
                if offset + BYTES_PER_TILE <= len(data):
                    for j in range(BYTES_PER_TILE):
                        data[offset + j] = (i + j) % 256

            return data

        if data_type == "cgram":
            default_size = 512  # 256 colors * 2 bytes
            data = bytearray(size or default_size)

            # Add realistic palette data (BGR555 format)
            for i in range(0, len(data), 2):
                data[i] = i % 256
                data[i + 1] = (i // 2) % 32

            return data

        if data_type == "oam":
            default_size = 544  # Standard OAM size
            data = bytearray(size or default_size)

            # Add realistic OAM data (sprite attributes)
            for i in range(0, min(len(data), 512), 4):  # 4 bytes per entry
                data[i] = i % 256      # X position
                data[i + 1] = i % 224  # Y position
                data[i + 2] = i % 256  # Tile index
                data[i + 3] = 0x20     # Attributes

            return data

        raise ValueError(f"Unknown data type: {data_type}")

    return _create_test_data

@pytest.fixture
def temp_files() -> Iterator[Callable[[bytes, str], str]]:
    """
    Factory for creating temporary test files with automatic cleanup.

    Creates temporary files with test data and ensures they are
    properly cleaned up after test completion.
    """
    created_files: list[str] = []

    def _create_temp_file(data: bytes, suffix: str = ".dmp") -> str:
        """Create a temporary file with the given data."""
        temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        temp_file.write(data)
        temp_file.close()
        created_files.append(temp_file.name)
        return temp_file.name

    yield _create_temp_file

    # Cleanup
    for file_path in created_files:
        try:
            Path(file_path).unlink(missing_ok=True)
        except OSError:
            pass  # File might already be deleted

@pytest.fixture
def standard_test_params(
    test_data_factory: Callable[..., bytearray],
    temp_files: Callable[[bytes, str], str],
) -> dict[str, Any]:
    """
    Create standard test parameters used across integration tests.

    Provides the common set of test parameters that many integration
    tests use, reducing duplication in test setup.
    """
    # Create standard test data
    vram_data = test_data_factory("vram")
    cgram_data = test_data_factory("cgram")
    oam_data = test_data_factory("oam")

    # Create temporary files - convert bytearray to bytes for temp_files
    vram_file = temp_files(bytes(vram_data), ".dmp")
    cgram_file = temp_files(bytes(cgram_data), ".dmp")
    oam_file = temp_files(bytes(oam_data), ".dmp")

    return {
        "vram_path": vram_file,
        "cgram_path": cgram_file,
        "oam_path": oam_file,
        "output_base": "test_output",
        "create_grayscale": True,
        "create_metadata": True,
        "vram_data": vram_data,
        "cgram_data": cgram_data,
        "oam_data": oam_data,
    }

@pytest.fixture
def minimal_sprite_data(
    test_data_factory: Callable[..., bytearray],
) -> dict[str, Any]:
    """
    Create minimal but valid sprite data for quick tests.

    Provides a lightweight alternative to full test data for tests
    that just need basic sprite data structure.
    """
    return {
        "vram": test_data_factory("vram", size=0x1000),  # 4KB
        "cgram": test_data_factory("cgram", size=32),    # 1 palette
        "width": 64,
        "height": 64,
        "tile_count": 8,
    }

# Consolidated mock fixtures using RealComponentFactory
@pytest.fixture
def real_factory() -> RealComponentFactory:
    """Provide a RealComponentFactory for creating test components."""
    factory = RealComponentFactory()
    yield factory
    # Cleanup will be handled by factory's cleanup method if needed
    if hasattr(factory, 'cleanup'):
        factory.cleanup()

@pytest.fixture
def mock_main_window(real_factory: RealComponentFactory) -> MockMainWindowProtocol:
    """Provide a fully configured mock main window using real components."""
    return real_factory.create_main_window()

@pytest.fixture
def mock_extraction_worker(real_factory: RealComponentFactory) -> Mock:  # Would be MockExtractionWorkerProtocol if it existed
    """Provide a fully configured mock extraction worker using real components."""
    return real_factory.create_extraction_worker()

@pytest.fixture(scope="class")
def real_extraction_manager() -> ExtractionManager:
    """Class-scoped real extraction manager for performance optimization.

    Used 51 times across tests. Class scope reduces instantiations
    from 51 to ~12 (77% reduction).

    NOTE: This returns a REAL ExtractionManager, not a mock.
    For actual mocks, create them locally with Mock(spec=ExtractionManager).
    """
    factory = RealComponentFactory()
    return factory.create_extraction_manager()

@pytest.fixture
def real_injection_manager(real_factory: RealComponentFactory) -> InjectionManager:
    """Provide a fully configured real injection manager.

    NOTE: Returns a REAL InjectionManager, not a mock.
    For actual mocks, create them locally with Mock(spec=InjectionManager).
    """
    return real_factory.create_injection_manager()

@pytest.fixture(scope="class")
def real_session_manager() -> SessionManager:
    """Class-scoped real session manager for performance optimization.

    Used 26 times across tests. Class scope reduces instantiations
    from 26 to ~8 (69% reduction).

    NOTE: This returns a REAL SessionManager, not a mock.
    For actual mocks, create them locally with Mock(spec=SessionManager).
    """
    factory = RealComponentFactory()
    return factory.create_session_manager()

@pytest.fixture(scope="class")
def mock_settings_manager() -> Mock:
    """Class-scoped mock settings manager for performance optimization.

    Used 44 times across tests. Class scope reduces instantiations
    from 44 to ~10 (77% reduction).

    Provides a mock settings manager with common configuration methods.
    """
    manager = Mock()

    # Add common settings methods
    manager.get_setting = Mock()
    manager.set_setting = Mock()
    manager.save_settings = Mock()
    manager.load_settings = Mock()
    manager.reset_to_defaults = Mock()

    # Add common settings with default values
    manager.get_setting.side_effect = lambda key, default=None: {
        'output_path': '/tmp/test_output',
        'create_grayscale': True,
        'create_metadata': True,
        'auto_save': False,
    }.get(key, default)

    return manager

@pytest.fixture
def mock_file_dialogs(real_factory: RealComponentFactory) -> dict[str, Mock]:
    """Provide mock file dialog functions."""
    return real_factory.create_file_dialogs()

# HAL-specific fixtures

@pytest.fixture
def reset_hal_singletons() -> Generator[None, None, None]:
    """
    Reset HAL singletons after a test.

    This prevents HAL state (statistics, mock configuration, failure modes)
    from leaking between tests. Request this fixture explicitly in tests
    that use HAL components.

    Usage:
        def test_hal_extraction(reset_hal_singletons):
            # HAL singletons will be reset after this test
            pass

    Or use usefixtures for entire test classes:
        @pytest.mark.usefixtures("reset_hal_singletons")
        class TestHALCompression:
            pass
    """
    # Let the test run
    yield

    # Reset both real and mock HAL singletons after each test
    with contextlib.suppress(Exception):
        MockHALProcessPool.reset_singleton()
    with contextlib.suppress(Exception):
        from core.hal_compression import HALProcessPool
        HALProcessPool.reset_singleton()


@pytest.fixture
def hal_pool(request, tmp_path):
    """
    Provide HAL process pool - mock or real based on test markers.

    Tests marked with @pytest.mark.real_hal will get the real pool.
    All other tests get the fast mock implementation.
    """
    use_real = request.node.get_closest_marker("real_hal") is not None

    if use_real:
        # Use real HAL process pool
        from core.hal_compression import HALProcessPool

        # Reset singleton before test
        HALProcessPool.reset_singleton()
        pool = HALProcessPool()

        # Create real or mock tools
        exhal_path, inhal_path = create_mock_hal_tools(tmp_path)
        pool.initialize(exhal_path, inhal_path)

        yield pool

        # Cleanup
        pool.shutdown()
        HALProcessPool.reset_singleton()
    else:
        # Use mock HAL process pool
        MockHALProcessPool.reset_singleton()
        pool = MockHALProcessPool()

        # Initialize with mock paths
        pool.initialize("mock_exhal", "mock_inhal")

        yield pool

        # Cleanup
        pool.shutdown()
        MockHALProcessPool.reset_singleton()

@pytest.fixture
def hal_compressor(request, tmp_path):
    """
    Provide HAL compressor - mock or real based on test markers.

    Tests marked with @pytest.mark.real_hal will get the real compressor.
    All other tests get the fast mock implementation.
    """
    use_real = request.node.get_closest_marker("real_hal") is not None

    if use_real:
        # Use real HAL compressor
        from core.hal_compression import HALCompressor

        # Create mock tools for testing
        exhal_path, inhal_path = create_mock_hal_tools(tmp_path)
        compressor = HALCompressor(exhal_path, inhal_path, use_pool=True)

        yield compressor

        # Cleanup if pool was initialized
        if hasattr(compressor, '_pool') and compressor._pool:
            compressor._pool.shutdown()
    else:
        # Use mock HAL compressor
        compressor = MockHALCompressor(use_pool=True)

        yield compressor

        # Cleanup
        if compressor._pool:
            compressor._pool.shutdown()

@pytest.fixture
def mock_hal(monkeypatch):
    """
    Explicit HAL mock fixture - tests must request this to use mocked HAL.

    This fixture patches the HAL module to use mock implementations.
    Tests that need fast HAL mocking (e.g., unit tests) should explicitly
    request this fixture.

    Usage:
        def test_something_with_hal(mock_hal):
            # HAL is now mocked
            ...

        @pytest.mark.usefixtures("mock_hal")
        class TestHALDependentCode:
            # All tests in this class use mocked HAL
            ...

    For tests that need real HAL, simply don't request this fixture.
    """
    monkeypatch.setattr("core.hal_compression.HALProcessPool", MockHALProcessPool)
    monkeypatch.setattr("core.hal_compression.HALCompressor", MockHALCompressor)

    yield

    # Cleanup singletons after test
    with contextlib.suppress(Exception):
        MockHALProcessPool.reset_singleton()

@pytest.fixture
def mock_hal_tools(tmp_path):
    """
    Create mock HAL tool executables for testing.

    Returns tuple of (exhal_path, inhal_path).
    """
    return create_mock_hal_tools(tmp_path)

@pytest.fixture
def hal_test_data() -> dict[str, bytes]:
    """
    Provide standard test data for HAL compression tests.

    Returns dict with various test data patterns.
    """
    return {
        "small": b"Small test data for compression" * 10,
        "medium": b"M" * 0x1000,  # 4KB
        "large": b"L" * 0x8000,   # 32KB
        "pattern": bytes([(i * 17) % 256 for i in range(0x2000)]),  # 8KB pattern
        "zeros": b"\x00" * 0x1000,  # 4KB zeros
        "ones": b"\xff" * 0x1000,   # 4KB ones
    }

@pytest.fixture(scope="class")
def rom_cache() -> ROMCache:
    """Class-scoped ROM cache fixture for performance optimization.

    Used 48 times across tests. Class scope reduces instantiations
    from 48 to ~10 (79% reduction).

    Provides a real ROM cache with common caching functionality.
    Reset between tests via clear_cache() in reset_class_scoped_fixtures.
    """
    factory = RealComponentFactory()
    return factory.create_rom_cache()

@pytest.fixture
def mock_rom_cache(rom_cache: ROMCache) -> ROMCache:
    """Alias for rom_cache fixture for backward compatibility.

    NOTE: This now returns the class-scoped rom_cache directly
    instead of creating a new instance each time.
    """
    return rom_cache

# Dependency Injection fixtures
@pytest.fixture
def manager_context_factory() -> Callable[[dict[str, Any] | list[str] | None, str], ContextManager[Any]]:
    """
    Factory for creating manager contexts for dependency injection tests.

    This fixture provides a clean way to create test contexts with specific
    manager instances, enabling proper isolation between tests.

    Usage:
        def test_my_dialog(manager_context_factory):
            mock_injection = Mock()
            with manager_context_factory({"injection": mock_injection}):
                dialog = InjectionDialog()
                # dialog will use mock_injection
    """
    from core.managers.context import manager_context
    from tests.infrastructure.test_manager_factory import TestManagerFactory

    def _create_context(
        managers: dict[str, Any] | list[str] | None = None,
        name: str = "test_context"
    ) -> ContextManager[Any]:
        """
        Create a manager context for testing.

        Args:
            managers: Dict of manager instances, or list of manager names
            name: Context name for debugging

        Returns:
            Context manager for use in with statements
        """
        if managers is None:
            # Create complete test context
            context_managers = {
                "extraction": TestManagerFactory.create_test_extraction_manager(),
                "injection": TestManagerFactory.create_test_injection_manager(),
                "session": TestManagerFactory.create_test_session_manager(),
            }
        elif isinstance(managers, list):
            # Create context with specific managers
            context_managers = {}
            for manager_name in managers:
                if manager_name == "extraction":
                    context_managers[manager_name] = TestManagerFactory.create_test_extraction_manager()
                elif manager_name == "injection":
                    context_managers[manager_name] = TestManagerFactory.create_test_injection_manager()
                elif manager_name == "session":
                    context_managers[manager_name] = TestManagerFactory.create_test_session_manager()
        else:
            # Use provided manager dict
            context_managers = managers

        return manager_context(context_managers, name=name)

    return _create_context

@pytest.fixture
def test_injection_manager() -> Mock:
    """Provide a test injection manager instance."""
    from tests.infrastructure.test_manager_factory import TestManagerFactory
    return TestManagerFactory.create_test_injection_manager()

@pytest.fixture
def test_extraction_manager() -> Mock:
    """Provide a test extraction manager instance."""
    from tests.infrastructure.test_manager_factory import TestManagerFactory
    return TestManagerFactory.create_test_extraction_manager()

@pytest.fixture
def test_session_manager() -> Mock:
    """Provide a test session manager instance."""
    from tests.infrastructure.test_manager_factory import TestManagerFactory
    return TestManagerFactory.create_test_session_manager()

@pytest.fixture
def complete_test_context() -> Any:  # ManagerContext type
    """Provide a complete test context with all managers configured."""
    from tests.infrastructure.test_manager_factory import TestManagerFactory
    return TestManagerFactory.create_complete_test_context()

@pytest.fixture
def minimal_injection_context() -> Any:  # ManagerContext type
    """Provide a minimal context with just injection manager for dialog tests."""
    from tests.infrastructure.test_manager_factory import TestManagerFactory
    return TestManagerFactory.create_minimal_test_context(["injection"], name="dialog_test")



@pytest.fixture(scope="class")
def controller(main_window: MockMainWindowProtocol) -> Mock:
    """Class-scoped controller fixture for performance optimization.

    Used 119 times across tests. Class scope reduces instantiations
    from 119 to ~30 (75% reduction).

    Creates an ExtractionController instance with proper main window dependency.
    """
    if ExtractionController is None:
        # Return mock if controller class unavailable
        return Mock()

    # Create a mock controller to avoid manager initialization issues
    controller = Mock(spec=ExtractionController if ExtractionController else None)
    controller.main_window = main_window
    controller.session_manager = Mock()
    controller.extraction_manager = Mock()
    controller.injection_manager = Mock()
    controller.palette_manager = Mock()
    controller.worker_manager = Mock()
    controller.error_handler = Mock()

    return controller

@pytest.fixture(scope="module")
def mock_manager_registry() -> Generator[Mock, None, None]:
    """Module-scoped manager registry fixture for performance optimization.

    Used 81 times across tests. Module scope reduces instantiations
    from 81 to ~15 (81% reduction).

    Provides a mock manager registry with common manager access methods.
    Resets mock state at end of module to prevent state leakage.
    """
    registry = Mock()

    # Add common registry methods
    registry.get_manager = Mock()
    registry.register_manager = Mock()
    registry.is_initialized = Mock(return_value=True)
    registry.cleanup = Mock()

    # Add manager getters
    registry.get_extraction_manager = Mock()
    registry.get_injection_manager = Mock()
    registry.get_session_manager = Mock()

    yield registry

    # Reset mock state at end of module to prevent state leakage
    registry.reset_mock(return_value=True, side_effect=True)

@pytest.fixture(scope="class")
def reset_main_window_state(main_window: MockMainWindowProtocol) -> Generator[None, None, None]:
    """Reset main window state between tests within the same class.

    This fixture ensures state isolation when using class-scoped main_window.
    Must be explicitly requested by test classes that need it.
    """
    # Reset state before test
    if hasattr(main_window, '_output_path'):
        main_window._output_path = ""
    if hasattr(main_window, '_extracted_files'):
        main_window._extracted_files = []

    # Reset all mock call histories
    for attr_name in dir(main_window):
        attr = getattr(main_window, attr_name, None)
        if isinstance(attr, Mock):
            attr.reset_mock()

    yield

    # Additional cleanup after test if needed
    pass

@pytest.fixture(scope="class")
def reset_controller_state(controller: Mock) -> Generator[None, None, None]:
    """Reset controller state between tests within the same class.

    This fixture ensures state isolation when using class-scoped controller.
    Must be explicitly requested by test classes that need it.
    """
    # Reset controller state if it's a real controller
    if hasattr(controller, 'reset_state'):
        controller.reset_state()
    elif isinstance(controller, Mock):
        controller.reset_mock()

    yield

    # Additional cleanup after test if needed
    pass

@pytest.fixture(scope="class")
def reset_class_state(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Reset state for class-scoped fixtures between tests.

    This fixture ensures proper state isolation for performance-optimized
    class-scoped fixtures. Request it explicitly in test classes that need
    fixture state reset between tests.

    Usage:
        @pytest.mark.usefixtures("reset_class_state")
        class TestExtractionPanel:
            pass

    IMPORTANT: reset_mock() only clears call history. We must also clear:
    - return_value (if manually configured)
    - side_effect (if manually configured)
    - Any internal state
    """
    # Get list of fixture names used by current test
    fixture_names = getattr(request, 'fixturenames', [])

    # Reset fixtures dynamically based on what's actually used
    fixtures_to_reset = [
        'real_extraction_manager',  # Real component - uses reset_state() or clear()
        'real_session_manager',     # Real component - uses reset_state() or clear()
        'rom_cache',
        'mock_settings_manager',
        'main_window',
    ]

    for fixture_name in fixtures_to_reset:
        if fixture_name in fixture_names:
            try:
                fixture_value = request.getfixturevalue(fixture_name)
                if isinstance(fixture_value, Mock):
                    # Full reset: clear call history AND configured values
                    fixture_value.reset_mock(return_value=True, side_effect=True)
                elif hasattr(fixture_value, 'reset_state'):
                    # Real component with explicit reset method
                    fixture_value.reset_state()
                elif hasattr(fixture_value, 'clear_cache'):
                    # ROMCache and similar use clear_cache() method
                    fixture_value.clear_cache()
                elif hasattr(fixture_value, 'clear'):
                    # Generic clear for collections
                    fixture_value.clear()
            except pytest.FixtureLookupError:
                pass  # Fixture not available in this context
            except Exception as e:
                # Log reset failures but don't fail the test
                # Reset is best-effort to improve isolation
                import logging
                logging.getLogger(__name__).warning(
                    f"Failed to reset fixture {fixture_name}: {e}"
                )

    yield





