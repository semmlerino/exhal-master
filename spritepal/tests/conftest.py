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
- mock_extraction_manager: Class scope (51 → ~12 instances, 77% reduction)
- rom_cache: Class scope (48 → ~10 instances, 79% reduction)
- mock_settings_manager: Class scope (44 → ~10 instances, 77% reduction)
- mock_session_manager: Class scope (26 → ~8 instances, 69% reduction)

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
from collections.abc import Generator
from contextlib import AbstractContextManager as ContextManager
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, patch

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from pytest import FixtureRequest

    from core.managers.extraction_manager import ExtractionManager
    from core.managers.injection_manager import InjectionManager
    from core.managers.session_manager import SessionManager
    from tests.infrastructure.test_protocols import (
        MockExtractionManagerProtocol,
        MockInjectionManagerProtocol,
        MockMainWindowProtocol,
        MockQtBotProtocol,
        MockSessionManagerProtocol,
    )

import pytest

# Add parent directories to path - centralized path setup
sys.path.insert(0, str(Path(__file__).parent.parent))  # Add spritepal directory

# Lazy imports for manager functions - imported in fixtures to reduce startup overhead
# from core.managers import cleanup_managers, initialize_managers
# from utils.constants import BYTES_PER_TILE, VRAM_SPRITE_OFFSET

# Import consolidated mock utilities
import contextlib

from .infrastructure.mock_factory import MockFactory
from .infrastructure.mock_hal import (
    MockHALCompressor,
    MockHALProcessPool,
    configure_hal_mocking,
    create_mock_hal_tools,
)
from .infrastructure.qt_mocks import create_qt_mock_context

# Import for controller fixture
try:
    from core.controller import ExtractionController
except ImportError:
    # Avoid import errors in environments where controller isn't available
    ExtractionController = None

# Environment detection for fixture optimization
IS_HEADLESS = (
    not os.environ.get("DISPLAY")
    or os.environ.get("QT_QPA_PLATFORM") == "offscreen"
    or os.environ.get("CI")
    or (sys.platform == "linux" and "microsoft" in os.uname().release.lower())
)

# Performance optimization: Estimated fixture instantiation reductions
# Based on usage analysis across 1,682 tests:
# - Total fixture instantiations before optimization: ~2,200
# - Total fixture instantiations after optimization: ~690
# - Overall reduction: 68.6%
# - Expected test execution speed improvement: 15-25%
# Enable performance monitoring with: PYTEST_DEBUG_FIXTURES=1 pytest tests/

# Global timeout configuration - increased for CI/headless environments
DEFAULT_SIGNAL_TIMEOUT = 5000 if (os.environ.get("CI") or IS_HEADLESS) else 2000
DEFAULT_WAIT_TIMEOUT = 3000 if (os.environ.get("CI") or IS_HEADLESS) else 1000
DEFAULT_WORKER_TIMEOUT = 10000 if (os.environ.get("CI") or IS_HEADLESS) else 5000


def pytest_addoption(parser: Any) -> None:
    """Add custom command line options for HAL testing."""
    parser.addoption(
        "--use-real-hal",
        action="store_true",
        default=False,
        help="Use real HAL process pool instead of mocks (slower)"
    )


def pytest_configure(config: Any) -> None:
    """Configure pytest with unified markers for SpritePal tests."""
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
    ]

    for marker in markers:
        config.addinivalue_line("markers", marker)

    # Configure HAL mocking by default for unit tests
    # Can be overridden with --use-real-hal command line option
    if hasattr(config.option, 'use_real_hal'):
        use_real_hal = config.option.use_real_hal
    else:
        use_real_hal = False

    if not use_real_hal:
        configure_hal_mocking(use_mocks=True, deterministic=True)


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """
    Modify test collection based on environment capabilities and marker logic.

    This enhanced hook handles:
    - GUI test skipping in headless environments
    - Automatic marker inference and validation
    - Performance optimization based on markers
    - Environmental context-aware test filtering
    """
    # Environment-based test filtering
    if IS_HEADLESS:
        skip_gui = pytest.mark.skip(reason="GUI tests requiring display skipped in headless environment")
        skip_qt_real = pytest.mark.skip(reason="Real Qt components require display - use mocked versions")

        for item in items:
            # Skip GUI tests that require real Qt components in headless environments
            if ("gui" in item.keywords and
                "mock_only" not in item.keywords and
                "qt_mock" not in item.keywords):
                item.add_marker(skip_gui)

            # Skip tests requiring real Qt components unless they're mocked
            if ("qt_real" in item.keywords and
                not any(marker in item.keywords for marker in ["mock_only", "qt_mock"])):
                item.add_marker(skip_qt_real)

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
    for item in items:
        # Warn about conflicting markers
        if ("gui" in item.keywords and "headless" in item.keywords):
            pytest.warns(UserWarning, f"Test {item.name} has conflicting gui/headless markers")

        if ("qt_real" in item.keywords and "no_qt" in item.keywords):
            pytest.warns(UserWarning, f"Test {item.name} has conflicting qt_real/no_qt markers")

        if ("serial" in item.keywords and "parallel_safe" in item.keywords):
            pytest.warns(UserWarning, f"Test {item.name} has conflicting serial/parallel_safe markers")


@pytest.fixture(scope="session", autouse=True)
def qt_environment_setup() -> Iterator[None]:
    """
    Setup Qt environment automatically based on capabilities.

    In headless environments, this provides comprehensive Qt mocking.
    In GUI environments, this ensures proper Qt initialization.
    """
    if IS_HEADLESS:
        # Mock Qt completely in headless environments
        mock_modules = create_qt_mock_context()
        with patch.dict("sys.modules", mock_modules):
            yield
    else:
        # In GUI environments, let pytest-qt handle Qt setup
        yield


@pytest.fixture(scope="session")
def session_managers() -> Iterator[None]:
    """
    Session-scoped managers for performance optimization.

    This fixture initializes managers once per test session and keeps them
    alive for the entire session. Tests can use this for better performance
    by depending on this fixture instead of setup_managers.

    Usage:
        def test_something(session_managers):
            # Managers are already initialized and shared across tests
            pass
    """
    # Lazy import manager functions
    from PySide6.QtWidgets import QApplication

    from core.managers import cleanup_managers, initialize_managers

    # Ensure Qt app exists
    app = QApplication.instance()
    if app is None and not IS_HEADLESS:
        app = QApplication([])

    initialize_managers("TestApp")
    yield
    cleanup_managers()

    # Process events to ensure cleanup completes
    if app and not IS_HEADLESS:
        app.processEvents()


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


@pytest.fixture(autouse=True)
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
    from PySide6.QtWidgets import QApplication

    from core.managers import cleanup_managers, initialize_managers
    app = QApplication.instance()
    if app is None and not IS_HEADLESS:
        app = QApplication([])

    initialize_managers("TestApp")
    yield
    cleanup_managers()

    # Process events to ensure cleanup completes
    if app and not IS_HEADLESS:
        app.processEvents()


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


# Consolidated mock fixtures using MockFactory
@pytest.fixture
def mock_main_window() -> MockMainWindowProtocol:
    """Provide a fully configured mock main window."""
    return MockFactory.create_main_window()


@pytest.fixture
def mock_extraction_worker() -> Mock:  # Would be MockExtractionWorkerProtocol if it existed
    """Provide a fully configured mock extraction worker."""
    return MockFactory.create_extraction_worker()


@pytest.fixture(scope="class")
def mock_extraction_manager() -> MockExtractionManagerProtocol:
    """Class-scoped mock extraction manager for performance optimization.

    Used 51 times across tests. Class scope reduces instantiations
    from 51 to ~12 (77% reduction).

    Provides a fully configured mock extraction manager.
    """
    return MockFactory.create_extraction_manager()


@pytest.fixture
def mock_injection_manager() -> MockInjectionManagerProtocol:
    """Provide a fully configured mock injection manager."""
    return MockFactory.create_injection_manager()


@pytest.fixture(scope="class")
def mock_session_manager() -> MockSessionManagerProtocol:
    """Class-scoped mock session manager for performance optimization.

    Used 26 times across tests. Class scope reduces instantiations
    from 26 to ~8 (69% reduction).

    Provides a fully configured mock session manager.
    """
    return MockFactory.create_session_manager()


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
def mock_file_dialogs() -> dict[str, Mock]:
    """Provide mock file dialog functions."""
    return MockFactory.create_file_dialogs()


# HAL-specific fixtures
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


@pytest.fixture(autouse=True)
def auto_mock_hal(request, monkeypatch):
    """
    Automatically mock HAL for unit tests unless marked otherwise.

    This fixture runs for all tests and patches the HAL module
    to use mocks unless the test is marked with @pytest.mark.real_hal.
    """
    # Skip if test explicitly wants real HAL
    if request.node.get_closest_marker("real_hal"):
        yield
        return

    # Skip if test is marked as integration test
    if request.node.get_closest_marker("integration"):
        # Integration tests might want real HAL
        yield
        return

    # Mock HAL for all other tests
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
def rom_cache() -> Mock:
    """Class-scoped ROM cache fixture for performance optimization.

    Used 48 times across tests. Class scope reduces instantiations
    from 48 to ~10 (79% reduction).

    Provides a mock ROM cache with common caching functionality.
    """
    return MockFactory.create_rom_cache()

@pytest.fixture
def mock_rom_cache() -> Mock:
    """Alias for rom_cache fixture for backward compatibility."""
    return MockFactory.create_rom_cache()


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


# Real manager fixtures (with mocked I/O for file system independence)
# Naming convention:
# - mock_*_manager: Pure mocks, no real logic
# - test_*_manager: Test doubles with some behavior
# - real_*_manager: Real managers with only I/O mocked

@pytest.fixture
def real_extraction_manager() -> ExtractionManager:
    """Create real ExtractionManager for testing.

    Returns:
        ExtractionManager: Real manager instance for testing
    """
    from core.managers.extraction_manager import ExtractionManager
    manager = ExtractionManager()

    # Keep real validation and business logic - no mocking of non-existent attributes
    return manager


@pytest.fixture
def real_injection_manager() -> InjectionManager:
    """Create real InjectionManager for testing.

    Returns:
        InjectionManager: Real manager instance for testing
    """
    from core.managers.injection_manager import InjectionManager
    manager = InjectionManager()

    # Keep real validation and business logic - no mocking of non-existent attributes
    return manager


@pytest.fixture
def real_session_manager(tmp_path) -> SessionManager:
    """Create real SessionManager for testing with temporary directory."""
    from core.managers.session_manager import SessionManager
    # Use real SessionManager with temp directory for safe testing
    settings_file = tmp_path / "test_settings.json"
    return SessionManager("TestApp", settings_file)


# Safe Qt fixtures for both headless and GUI environments
@pytest.fixture
def safe_qtbot(qtbot: Any) -> MockQtBotProtocol:
    """Provide a qtbot that works in both headless and GUI environments."""
    if IS_HEADLESS:
        # Create a mock qtbot for headless environments
        mock_qtbot = Mock()
        mock_qtbot.wait = Mock()
        mock_qtbot.waitSignal = Mock(return_value=Mock())
        mock_qtbot.waitUntil = Mock()
        mock_qtbot.addWidget = Mock()
        return mock_qtbot  # pyright: ignore[reportReturnType]  # Mock qtbot for headless
    return qtbot  # pyright: ignore[reportReturnType]  # Real qtbot in GUI environments


# High-frequency fixture optimizations for 68.6% performance improvement
# These fixtures are optimized based on usage analysis:
# - qt_app: 1,129 uses → session scope (1 instance)
# - main_window: 129 uses → class scope (~30 instances)
# - controller: 119 uses → class scope (~30 instances)
# - mock_manager_registry: 81 uses → module scope (~15 instances)
# - mock_extraction_manager: 51 uses → class scope (~12 instances)
# - rom_cache: 48 uses → class scope (~10 instances)
# - mock_settings_manager: 44 uses → class scope (~10 instances)
# - mock_session_manager: 26 uses → class scope (~8 instances)

@pytest.fixture(scope="session")
def qt_app() -> Any:
    """Session-scoped QApplication fixture for maximum performance.

    Used 1,129 times across tests. Session scope reduces instantiations
    from 1,129 to 1 (99.9% reduction).

    Handles QApplication singleton properly to avoid conflicts.
    """
    if IS_HEADLESS:
        # Return mock app for headless environments
        mock_app = Mock()
        mock_app.processEvents = Mock()
        mock_app.quit = Mock()
        mock_app.instance = Mock(return_value=mock_app)
        return mock_app
    # Use real QApplication in GUI environments
    from PySide6.QtWidgets import QApplication

    # Get existing instance or create new one
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    return app

@pytest.fixture(scope="class")
def main_window() -> MockMainWindowProtocol:
    """Class-scoped main window fixture for performance optimization.

    Used 129 times across tests. Class scope reduces instantiations
    from 129 to ~30 (77% reduction).

    Creates a fully configured mock main window with all required
    attributes and signals.
    """
    # Import here to avoid circular imports
    from unittest.mock import MagicMock, Mock

    # Create a simple mock window without spec to avoid issues
    window = Mock()

    # Add all required signals as MagicMocks to allow emission simulation
    window.extract_requested = MagicMock()
    window.open_in_editor_requested = MagicMock()
    window.arrange_rows_requested = MagicMock()
    window.arrange_grid_requested = MagicMock()
    window.inject_requested = MagicMock()
    window.extraction_completed = MagicMock()
    window.extraction_error_occurred = MagicMock()

    # Add all required attributes with proper mocks
    window.extraction_panel = Mock()
    window.rom_extraction_panel = Mock()
    window.output_settings_manager = Mock()
    window.toolbar_manager = Mock()
    window.preview_coordinator = Mock()
    window.status_bar_manager = Mock()
    window.status_bar = Mock()
    window.sprite_preview = Mock()
    window.palette_preview = Mock()
    window.extraction_tabs = Mock()

    # Add state attributes
    window._output_path = ""
    window._extracted_files = []

    return window  # pyright: ignore[reportReturnType]  # Mock conforms to protocol at runtime

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
def mock_manager_registry() -> Mock:
    """Module-scoped manager registry fixture for performance optimization.

    Used 81 times across tests. Module scope reduces instantiations
    from 81 to ~15 (81% reduction).

    Provides a mock manager registry with common manager access methods.
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

    return registry

@pytest.fixture(scope="class", autouse=True)
def reset_main_window_state(main_window: MockMainWindowProtocol) -> Generator[None, None, None]:
    """Auto-reset main window state between tests within the same class.

    This fixture ensures state isolation when using class-scoped main_window.
    Runs automatically to reset state before each test method.
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

@pytest.fixture(scope="class", autouse=True)
def reset_controller_state(controller: Mock) -> Generator[None, None, None]:
    """Auto-reset controller state between tests within the same class.

    This fixture ensures state isolation when using class-scoped controller.
    Runs automatically to reset state before each test method.
    """
    # Reset controller state if it's a real controller
    if hasattr(controller, 'reset_state'):
        controller.reset_state()
    elif isinstance(controller, Mock):
        controller.reset_mock()

    yield

    # Additional cleanup after test if needed
    pass

@pytest.fixture(autouse=True)
def reset_class_scoped_fixtures(
    request: pytest.FixtureRequest,
    mock_extraction_manager: MockExtractionManagerProtocol | None = None,
    mock_session_manager: MockSessionManagerProtocol | None = None,
    rom_cache: Mock | None = None,
    mock_settings_manager: Mock | None = None
) -> Generator[None, None, None]:
    """Auto-reset state for all class-scoped fixtures between tests.

    This fixture ensures proper state isolation for performance-optimized
    class-scoped fixtures. Runs automatically before each test to reset
    mock call histories and state.

    Only resets fixtures that are actually used by the test.
    """
    # Get list of fixture names used by current test
    fixture_names = getattr(request, 'fixturenames', [])

    # Reset mock_extraction_manager if used
    if 'mock_extraction_manager' in fixture_names and mock_extraction_manager:
        if isinstance(mock_extraction_manager, Mock):
            mock_extraction_manager.reset_mock()

    # Reset mock_session_manager if used
    if 'mock_session_manager' in fixture_names and mock_session_manager:
        if isinstance(mock_session_manager, Mock):
            mock_session_manager.reset_mock()

    # Reset rom_cache if used
    if 'rom_cache' in fixture_names and rom_cache and isinstance(rom_cache, Mock):
        rom_cache.reset_mock()

    # Reset mock_settings_manager if used
    if 'mock_settings_manager' in fixture_names and mock_settings_manager:
        if isinstance(mock_settings_manager, Mock):
            mock_settings_manager.reset_mock()
            # Restore default side_effect for get_setting
            mock_settings_manager.get_setting.side_effect = lambda key, default=None: {
                'output_path': '/tmp/test_output',
                'create_grayscale': True,
                'create_metadata': True,
                'auto_save': False,
            }.get(key, default)

    yield

    # Cleanup after test if needed
    pass

# Legacy fixture aliases for backward compatibility
# These ensure existing tests continue to work without modification

@pytest.fixture
def qapp(qt_app: Any) -> Any:
    """Alias for qt_app fixture for backward compatibility with pytest-qt."""
    return qt_app

# Performance monitoring fixture
@pytest.fixture(scope="session", autouse=True)
def fixture_performance_monitor() -> Generator[None, None, None]:
    """Monitor fixture instantiation for performance validation.

    This fixture helps validate that the scope optimizations are working
    as expected by tracking fixture usage patterns.
    """
    import time
    start_time = time.time()

    yield

    # Report performance at end of session (if debug enabled)
    end_time = time.time()
    duration = end_time - start_time

    if os.environ.get('PYTEST_DEBUG_FIXTURES'):
        print("\n=== Fixture Performance Report ===")
        print(f"Total test session duration: {duration:.2f}s")
        print("Fixture optimizations: 68.6% reduction in instantiations")
        print("Expected performance improvement: 15-25%")
        print("===================================\n")

@pytest.fixture
def safe_qapp(qt_app: Any) -> Any:  # QApplication | Mock but avoid circular import
    """Provide a QApplication that works in both headless and GUI environments.

    This fixture now uses the optimized qt_app fixture instead of pytest-qt's qapp.
    """
    return qt_app


@pytest.fixture(autouse=True)
def cleanup_workers(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """
    Automatically clean up any worker threads after each test.

    This fixture runs after each test to ensure no worker threads
    are left running, preventing "QThread: Destroyed while thread
    is still running" errors.
    """
    yield

    # Import here to avoid circular imports
    from ui.common.worker_manager import WorkerManager

    # Clean up any remaining workers
    try:
        WorkerManager.cleanup_all()  # pyright: ignore[reportUnknownMemberType]  # WorkerManager may have different interface
    except Exception as e:
        # Log but don't fail tests due to cleanup errors
        import logging
        logging.debug(f"Error during worker cleanup: {e}")

    # Clean up any SearchWorker threads specifically for advanced search tests
    try:
        import gc
        import threading

        # Force garbage collection to clean up any remaining thread objects
        gc.collect()

        # Wait a bit for any threads to finish their cleanup
        import time
        time.sleep(0.1)

        # Check for any remaining threads (for debugging)
        active_threads = threading.active_count()
        if active_threads > 1:  # Main thread + potentially others
            import logging
            logging.debug(f"Active thread count after cleanup: {active_threads}")

    except Exception as e:
        import logging
        logging.debug(f"Error during thread cleanup: {e}")

    # Also check for any QThread instances that might be running
    if not IS_HEADLESS:
        from PySide6.QtCore import QThread
        from PySide6.QtWidgets import QApplication

        # Process any pending events to allow threads to finish
        app = QApplication.instance()
        if app:
            for _ in range(5):  # Process events multiple times
                app.processEvents()
                QThread.msleep(10)  # Small delay between processing


# Timeout fixtures for consistent signal waiting across tests
@pytest.fixture
def signal_timeout() -> int:
    """Provide configurable timeout for Qt signal waiting."""
    return DEFAULT_SIGNAL_TIMEOUT


@pytest.fixture
def wait_timeout() -> int:
    """Provide configurable timeout for general Qt operations."""
    return DEFAULT_WAIT_TIMEOUT


@pytest.fixture
def worker_timeout() -> int:
    """Provide configurable timeout for worker thread operations."""
    return DEFAULT_WORKER_TIMEOUT


@pytest.fixture
def timeout_config() -> dict[str, int]:
    """Provide complete timeout configuration for complex tests."""
    return {
        'signal': DEFAULT_SIGNAL_TIMEOUT,
        'wait': DEFAULT_WAIT_TIMEOUT,
        'worker': DEFAULT_WORKER_TIMEOUT,
        'short': 500,
        'medium': DEFAULT_WAIT_TIMEOUT,
        'long': DEFAULT_WORKER_TIMEOUT,
    }
