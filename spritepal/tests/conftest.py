"""
Unified pytest configuration for SpritePal tests.

This module consolidates all test configuration into a single, modern approach
that works consistently across all environments (headless, GUI, CI/CD).
"""

import os
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any, Callable, ContextManager, Optional
from unittest.mock import Mock, patch

import pytest

# Add parent directories to path - centralized path setup
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import SpritePal components after path setup
from spritepal.core.managers import cleanup_managers, initialize_managers
from spritepal.utils.constants import BYTES_PER_TILE, VRAM_SPRITE_OFFSET

# Import consolidated mock utilities
from .infrastructure.mock_factory import MockFactory
from .infrastructure.qt_mocks import create_qt_mock_context

# Environment detection
IS_HEADLESS = (
    not os.environ.get("DISPLAY")
    or os.environ.get("QT_QPA_PLATFORM") == "offscreen"
    or os.environ.get("CI")
    or (sys.platform == "linux" and "microsoft" in os.uname().release.lower())
)


def pytest_configure(config):
    """Configure pytest with unified markers for SpritePal tests."""
    markers = [
        "integration: mark test as integration test",
        "unit: mark test as unit test",
        "mock: mark test as using mocks",
        "slow: mark test as slow running",
        "manager: mark test as testing manager classes",
        "gui: mark test as requiring GUI (may be skipped in headless)",
        "mock_gui: mark test as GUI test that uses mocks (safe for headless)",
        "stability: mark test as stability/regression test",
        "phase1_fixes: mark test as validating Phase 1 fixes",
        "stress: mark test as stress/load test",
        "memory: mark test as testing memory management",
        "thread_safety: mark test as testing thread safety",
        "timer: mark test as testing QTimer functionality",
        "no_manager_setup: skip automatic manager setup for this test",
    ]

    for marker in markers:
        config.addinivalue_line("markers", marker)


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on environment capabilities."""
    if IS_HEADLESS:
        skip_gui = pytest.mark.skip(reason="GUI tests skipped in headless environment")
        for item in items:
            # Skip GUI tests that don't use mocks in headless environments
            if "gui" in item.keywords and "mock_gui" not in item.keywords:
                item.add_marker(skip_gui)


@pytest.fixture(scope="session", autouse=True)
def qt_environment_setup():
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


@pytest.fixture(autouse=True)
def setup_managers(request):
    """
    Setup managers for all tests.

    This fixture ensures proper manager initialization and cleanup
    for every test, replacing duplicated setup across test files.
    Skips setup if test is marked with 'no_manager_setup'.
    """
    # Skip manager setup if test is marked with no_manager_setup
    if request.node.get_closest_marker("no_manager_setup"):
        yield
        return

    initialize_managers("TestApp")
    yield
    cleanup_managers()


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
def temp_files() -> Generator[Callable[[bytes, str], str], None, None]:
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
    temp_files: Callable[[bytes, str], str]
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

    # Create temporary files
    vram_file = temp_files(vram_data, ".dmp")
    cgram_file = temp_files(cgram_data, ".dmp")
    oam_file = temp_files(oam_data, ".dmp")

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
    test_data_factory: Callable[..., bytearray]
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
def mock_main_window() -> Any:  # MockMainWindowProtocol but avoid import issues
    """Provide a fully configured mock main window."""
    return MockFactory.create_main_window()


@pytest.fixture
def mock_extraction_worker() -> Any:  # MockExtractionWorkerProtocol
    """Provide a fully configured mock extraction worker."""
    return MockFactory.create_extraction_worker()


@pytest.fixture
def mock_extraction_manager() -> Any:  # MockExtractionManagerProtocol
    """Provide a fully configured mock extraction manager."""
    return MockFactory.create_extraction_manager()


@pytest.fixture
def mock_injection_manager() -> Any:  # MockInjectionManagerProtocol
    """Provide a fully configured mock injection manager."""
    return MockFactory.create_injection_manager()


@pytest.fixture
def mock_session_manager() -> Any:  # MockSessionManagerProtocol
    """Provide a fully configured mock session manager."""
    return MockFactory.create_session_manager()


@pytest.fixture
def mock_file_dialogs() -> dict[str, Mock]:
    """Provide mock file dialog functions."""
    return MockFactory.create_file_dialogs()


@pytest.fixture
def mock_rom_cache() -> Mock:
    """Provide a mock ROM cache for testing."""
    return MockFactory.create_rom_cache()


# Dependency Injection fixtures
@pytest.fixture
def manager_context_factory() -> Callable[..., ContextManager[Any]]:
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
        managers: Optional[dict[str, Any | None, list[str]]] = None,
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


# Safe Qt fixtures for both headless and GUI environments
@pytest.fixture
def safe_qtbot(qtbot: Any) -> Any:  # QtBot | Mock but avoid circular import
    """Provide a qtbot that works in both headless and GUI environments."""
    if IS_HEADLESS:
        # Create a mock qtbot for headless environments
        mock_qtbot = Mock()
        mock_qtbot.wait = Mock()
        mock_qtbot.waitSignal = Mock(return_value=Mock())
        mock_qtbot.waitUntil = Mock()
        mock_qtbot.addWidget = Mock()
        return mock_qtbot
    return qtbot


@pytest.fixture
def safe_qapp(qapp: Any) -> Any:  # QApplication | Mock but avoid circular import
    """Provide a QApplication that works in both headless and GUI environments."""
    if IS_HEADLESS:
        mock_app = Mock()
        mock_app.processEvents = Mock()
        mock_app.quit = Mock()
        return mock_app
    return qapp


@pytest.fixture(autouse=True)
def cleanup_workers(request):
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
        WorkerManager.cleanup_all()  # type: ignore[attr-defined]  # WorkerManager may have different interface
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
        from PyQt6.QtCore import QThread
        from PyQt6.QtWidgets import QApplication

        # Process any pending events to allow threads to finish
        app = QApplication.instance()
        if app:
            for _ in range(5):  # Process events multiple times
                app.processEvents()
                QThread.msleep(10)  # Small delay between processing
