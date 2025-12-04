# pyright: recommended
# pyright: reportPrivateUsage=false  # Factory may access private members for configuration
# pyright: reportUnknownMemberType=warning  # Mock attributes are dynamic

"""
Fixture factory pattern for creating safe Qt fixtures with consistent configuration.

This module provides a factory pattern for creating Qt fixtures that:
1. Handles environment detection automatically
2. Provides consistent configuration across test types
3. Manages resource lifecycle properly
4. Supports both real and mock implementations
5. Integrates with pytest fixture system

Key Classes:
- QtFixtureFactory: Main factory for creating Qt fixtures
- FixtureConfiguration: Configuration container for fixture settings
- FixtureRegistry: Registry for managing created fixtures
- FixtureValidator: Validation utilities for fixtures

Usage:
    from tests.infrastructure.fixture_factory import QtFixtureFactory

    factory = QtFixtureFactory()
    qtbot = factory.create_qtbot()
    qapp = factory.create_qapp()

    # With custom configuration
    config = FixtureConfiguration(headless_override=True)
    factory = QtFixtureFactory(config)

    # Cleanup
    factory.cleanup_all()

Integration with pytest:
    @pytest.fixture
    def qt_fixture_factory():
        factory = QtFixtureFactory()
        yield factory
        factory.cleanup_all()

Environment Handling:
- Automatic detection of headless vs GUI environments
- Fallback mechanisms for unsupported environments
- Configuration override capabilities
- Integration with existing environment detection

Thread Safety:
- Thread-safe fixture creation and management
- Proper cleanup in multi-threaded environments
- Resource sharing controls
"""

from __future__ import annotations

import logging
import threading
import weakref
from collections.abc import Callable
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from pytest import FixtureRequest

# Import safe fixture components
from .environment_detection import EnvironmentInfo, get_environment_info
from .safe_fixtures import (
    SafeDialogFactory,
    SafeQApplication,
    SafeQApplicationProtocol,
    SafeQtBot,
    SafeQtBotProtocol,
    SafeWidgetFactory,
    create_safe_dialog_factory,
    create_safe_qapp,
    create_safe_qtbot,
    create_safe_widget_factory,
)

# Configure logging
logger = logging.getLogger(__name__)

# Type variables
T = TypeVar('T')
FixtureType = TypeVar('FixtureType')

@dataclass
class FixtureConfiguration:
    """
    Configuration container for fixture creation settings.

    Provides centralized configuration for all fixture types with
    reasonable defaults and override capabilities.
    """

    # Environment overrides
    headless_override: bool | None = None
    """Override headless detection (None = auto-detect)"""

    force_mock: bool = False
    """Force mock implementations even in GUI environments"""

    force_real: bool = False
    """Force real implementations even in headless environments"""

    # Performance settings
    enable_session_scope: bool = True
    """Enable session-scoped fixtures for performance"""

    enable_cleanup_validation: bool = True
    """Enable validation during cleanup"""

    # Timeout configurations
    default_signal_timeout: int = 5000
    """Default timeout for signal operations (ms)"""

    default_wait_timeout: int = 3000
    """Default timeout for wait operations (ms)"""

    worker_timeout: int = 10000
    """Default timeout for worker operations (ms)"""

    # Error handling
    strict_mode: bool = False
    """Raise exceptions on fixture creation failures"""

    fallback_on_error: bool = True
    """Use fallback implementations on errors"""

    # Debugging
    enable_debug_logging: bool = False
    """Enable debug logging for fixture operations"""

    validate_fixture_api: bool = True
    """Validate fixture API compatibility"""

    # Resource management
    auto_cleanup: bool = True
    """Automatically cleanup fixtures on factory destruction"""

    max_qtbot_instances: int = 10
    """Maximum number of qtbot instances to cache"""

    max_qapp_instances: int = 1
    """Maximum number of QApplication instances (should be 1)"""

    # Feature flags
    features: dict[str, bool] = field(default_factory=dict)
    """Feature flags for experimental functionality"""

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.force_mock and self.force_real:
            raise ValueError("Cannot force both mock and real implementations")

        if self.max_qapp_instances > 1:
            logger.warning("Multiple QApplication instances may cause issues")

        # Set up default features
        if not self.features:
            self.features = {
                'adaptive_qtbot': True,
                'smart_cleanup': True,
                'error_recovery': True,
                'performance_monitoring': False,
            }

class FixtureCreationError(Exception):
    """Raised when fixture creation fails."""

    def __init__(self, fixture_type: str, original_error: Exception):
        self.fixture_type = fixture_type
        self.original_error = original_error
        super().__init__(f"Failed to create {fixture_type}: {original_error}")

class FixtureRegistry:
    """
    Registry for managing created fixtures and their lifecycle.

    Provides centralized tracking of fixtures for proper cleanup
    and resource management.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._fixtures: weakref.WeakSet[Any] = weakref.WeakSet()
        self._qtbots: list[SafeQtBot] = []
        self._qapps: list[SafeQApplication] = []
        self._factories: list[SafeWidgetFactory | SafeDialogFactory] = []
        self._cleanup_callbacks: list[Callable[[], None]] = []

    def register_qtbot(self, qtbot: SafeQtBot) -> None:
        """Register qtbot for management."""
        with self._lock:
            self._qtbots.append(qtbot)
            self._fixtures.add(qtbot)

    def register_qapp(self, qapp: SafeQApplication) -> None:
        """Register QApplication for management."""
        with self._lock:
            self._qapps.append(qapp)
            self._fixtures.add(qapp)

    def register_factory(self, factory: SafeWidgetFactory | SafeDialogFactory) -> None:
        """Register factory for management."""
        with self._lock:
            self._factories.append(factory)
            self._fixtures.add(factory)

    def register_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Register cleanup callback."""
        with self._lock:
            self._cleanup_callbacks.append(callback)

    def get_fixture_count(self) -> dict[str, int]:
        """Get count of registered fixtures by type."""
        with self._lock:
            return {
                'qtbots': len(self._qtbots),
                'qapps': len(self._qapps),
                'factories': len(self._factories),
                'total': len(self._fixtures),
            }

    def cleanup_all(self) -> None:
        """Cleanup all registered fixtures."""
        with self._lock:
            errors = []

            # Run custom cleanup callbacks first
            for callback in self._cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    errors.append(f"Cleanup callback error: {e}")

            # Cleanup qtbots
            for qtbot in self._qtbots:
                try:
                    qtbot.cleanup()
                except Exception as e:
                    errors.append(f"qtbot cleanup error: {e}")

            # Cleanup factories
            for factory in self._factories:
                try:
                    factory.cleanup()
                except Exception as e:
                    errors.append(f"factory cleanup error: {e}")

            # Cleanup QApplications last
            for qapp in self._qapps:
                try:
                    qapp.cleanup()
                except Exception as e:
                    errors.append(f"QApplication cleanup error: {e}")

            # Clear lists
            self._qtbots.clear()
            self._qapps.clear()
            self._factories.clear()
            self._cleanup_callbacks.clear()

            if errors:
                logger.warning(f"Cleanup errors occurred: {'; '.join(errors)}")

class QtFixtureFactory:
    """
    Main factory for creating safe Qt fixtures with consistent configuration.

    Provides a centralized way to create Qt fixtures that automatically
    adapt to the environment and provide consistent behavior across tests.
    """

    def __init__(
        self,
        config: FixtureConfiguration | None = None,
        env_info: EnvironmentInfo | None = None
    ):
        """
        Initialize factory with configuration.

        Args:
            config: Configuration for fixture creation
            env_info: Environment information (auto-detected if None)
        """
        self.config = config or FixtureConfiguration()
        self.env_info = env_info or get_environment_info()
        self.registry = FixtureRegistry()

        # Configure logging if requested
        if self.config.enable_debug_logging:
            logging.getLogger(__name__).setLevel(logging.DEBUG)

        # Cache for session-scoped fixtures
        self._qtbot_cache: SafeQtBotProtocol | None = None
        self._qapp_cache: SafeQApplicationProtocol | None = None

        logger.debug(f"QtFixtureFactory initialized (headless={self._is_headless()})")

    def _is_headless(self) -> bool:
        """Determine if running in headless mode based on config and environment."""
        if self.config.headless_override is not None:
            return self.config.headless_override

        if self.config.force_mock:
            return True

        if self.config.force_real:
            return False

        return self.env_info.is_headless

    def create_qtbot(self, request: FixtureRequest | None = None) -> SafeQtBotProtocol:
        """
        Create qtbot fixture with factory configuration.

        Args:
            request: Optional pytest request for integration

        Returns:
            SafeQtBotProtocol implementation

        Raises:
            FixtureCreationError: If creation fails and strict mode enabled
        """
        # Use cached instance if session scope enabled
        if self.config.enable_session_scope and self._qtbot_cache:
            return self._qtbot_cache

        try:
            qtbot = create_safe_qtbot(request)

            # Validate API if requested
            if self.config.validate_fixture_api:
                self._validate_qtbot_api(qtbot)

            # Cache for session scope
            if self.config.enable_session_scope:
                self._qtbot_cache = qtbot

            # Register for management
            if isinstance(qtbot, SafeQtBot):
                self.registry.register_qtbot(qtbot)

            logger.debug("QtBot created successfully")
            return qtbot

        except Exception as e:
            logger.error(f"Failed to create qtbot: {e}")

            if self.config.strict_mode:
                raise FixtureCreationError('qtbot', e) from e

            if self.config.fallback_on_error:
                # Return mock qtbot as fallback
                fallback_qtbot = SafeQtBot(headless=True)
                self.registry.register_qtbot(fallback_qtbot)
                logger.warning("Using fallback mock qtbot")
                return fallback_qtbot

            raise

    def create_qapp(self, args: list[str] | None = None) -> SafeQApplicationProtocol:
        """
        Create QApplication fixture with factory configuration.

        Args:
            args: Command line arguments for QApplication

        Returns:
            SafeQApplicationProtocol implementation

        Raises:
            FixtureCreationError: If creation fails and strict mode enabled
        """
        # Use cached instance if session scope enabled
        if self.config.enable_session_scope and self._qapp_cache:
            return self._qapp_cache

        try:
            qapp = create_safe_qapp(args)

            # Validate API if requested
            if self.config.validate_fixture_api:
                self._validate_qapp_api(qapp)

            # Cache for session scope
            if self.config.enable_session_scope:
                self._qapp_cache = qapp

            # Register for management
            if isinstance(qapp, SafeQApplication):
                self.registry.register_qapp(qapp)

            logger.debug("QApplication created successfully")
            return qapp

        except Exception as e:
            logger.error(f"Failed to create QApplication: {e}")

            if self.config.strict_mode:
                raise FixtureCreationError('qapp', e) from e

            if self.config.fallback_on_error:
                # Return mock QApplication as fallback
                fallback_qapp = SafeQApplication(headless=True)
                self.registry.register_qapp(fallback_qapp)
                logger.warning("Using fallback mock QApplication")
                return fallback_qapp

            raise

    def create_widget_factory(self) -> SafeWidgetFactory:
        """
        Create widget factory with factory configuration.

        Returns:
            SafeWidgetFactory instance
        """
        try:
            factory = create_safe_widget_factory()
            self.registry.register_factory(factory)
            logger.debug("Widget factory created successfully")
            return factory

        except Exception as e:
            logger.error(f"Failed to create widget factory: {e}")

            if self.config.strict_mode:
                raise FixtureCreationError('widget_factory', e) from e

            if self.config.fallback_on_error:
                fallback_factory = SafeWidgetFactory(headless=True)
                self.registry.register_factory(fallback_factory)
                return fallback_factory

            raise

    def create_dialog_factory(self) -> SafeDialogFactory:
        """
        Create dialog factory with factory configuration.

        Returns:
            SafeDialogFactory instance
        """
        try:
            factory = create_safe_dialog_factory()
            self.registry.register_factory(factory)
            logger.debug("Dialog factory created successfully")
            return factory

        except Exception as e:
            logger.error(f"Failed to create dialog factory: {e}")

            if self.config.strict_mode:
                raise FixtureCreationError('dialog_factory', e) from e

            if self.config.fallback_on_error:
                fallback_factory = SafeDialogFactory(headless=True)
                self.registry.register_factory(fallback_factory)
                return fallback_factory

            raise

    def _validate_qtbot_api(self, qtbot: SafeQtBotProtocol) -> None:
        """Validate qtbot has expected API."""
        required_methods = ['wait', 'waitSignal', 'waitUntil', 'addWidget']
        for method in required_methods:
            if not hasattr(qtbot, method):
                raise ValueError(f"qtbot missing required method: {method}")

    def _validate_qapp_api(self, qapp: SafeQApplicationProtocol) -> None:
        """Validate QApplication has expected API."""
        required_methods = ['processEvents', 'quit', 'exit']
        for method in required_methods:
            if not hasattr(qapp, method):
                raise ValueError(f"QApplication missing required method: {method}")

    @contextmanager
    def qt_context(self, request: FixtureRequest | None = None) -> Generator[dict[str, Any], None, None]:
        """
        Context manager providing complete Qt environment.

        Args:
            request: Optional pytest request

        Yields:
            Dictionary with Qt environment components
        """
        qtbot = self.create_qtbot(request)
        qapp = self.create_qapp()
        widget_factory = self.create_widget_factory()
        dialog_factory = self.create_dialog_factory()

        qt_env = {
            'qtbot': qtbot,
            'qapp': qapp,
            'widget_factory': widget_factory,
            'dialog_factory': dialog_factory,
            'config': self.config,
            'env_info': self.env_info,
        }

        try:
            logger.debug("Entering Qt context")
            yield qt_env
        finally:
            logger.debug("Exiting Qt context")
            # Cleanup handled by registry

    def get_statistics(self) -> dict[str, Any]:
        """Get factory usage statistics."""
        fixture_counts = self.registry.get_fixture_count()

        return {
            'fixtures_created': fixture_counts,
            'session_scope_enabled': self.config.enable_session_scope,
            'cache_hits': {
                'qtbot': self._qtbot_cache is not None,
                'qapp': self._qapp_cache is not None,
            },
            'environment': {
                'headless': self._is_headless(),
                'ci': self.env_info.is_ci,
                'qt_available': self.env_info.pyside6_available,
            },
            'configuration': {
                'strict_mode': self.config.strict_mode,
                'fallback_enabled': self.config.fallback_on_error,
                'debug_logging': self.config.enable_debug_logging,
            }
        }

    def cleanup_all(self) -> None:
        """Cleanup all fixtures created by this factory."""
        logger.debug("Starting factory cleanup")

        try:
            self.registry.cleanup_all()

            # Clear cache
            self._qtbot_cache = None
            self._qapp_cache = None

            logger.debug("Factory cleanup completed")

        except Exception as e:
            logger.error(f"Error during factory cleanup: {e}")
            if self.config.strict_mode:
                raise

    def __del__(self) -> None:
        """Cleanup on destruction if auto-cleanup enabled."""
        if self.config.auto_cleanup:
            with suppress(Exception):
                self.cleanup_all()

# Factory validator utility

class FixtureValidator:
    """Utility for validating fixture behavior and configuration."""

    @staticmethod
    def validate_factory_config(config: FixtureConfiguration) -> list[str]:
        """
        Validate factory configuration.

        Returns:
            List of validation warnings/errors
        """
        issues = []

        if config.force_mock and config.force_real:
            issues.append("Cannot force both mock and real implementations")

        if config.max_qapp_instances > 1:
            issues.append("Multiple QApplication instances may cause issues")

        if config.strict_mode and not config.fallback_on_error:
            issues.append("Strict mode without fallback may cause test failures")

        if config.default_signal_timeout < 100:
            issues.append("Very low signal timeout may cause flaky tests")

        return issues

    @staticmethod
    def validate_fixture_environment() -> dict[str, Any]:
        """Validate that fixture environment is suitable."""
        from .safe_fixtures import validate_fixture_environment
        return validate_fixture_environment()

# Convenience functions for common patterns

def create_test_qt_factory(
    headless: bool | None = None,
    strict: bool = False,
    enable_debug: bool = False
) -> QtFixtureFactory:
    """
    Create Qt fixture factory with common test configuration.

    Args:
        headless: Override headless mode detection
        strict: Enable strict error handling
        enable_debug: Enable debug logging

    Returns:
        Configured QtFixtureFactory
    """
    config = FixtureConfiguration(
        headless_override=headless,
        strict_mode=strict,
        enable_debug_logging=enable_debug,
        fallback_on_error=not strict,
    )

    return QtFixtureFactory(config)

def create_performance_qt_factory() -> QtFixtureFactory:
    """
    Create Qt fixture factory optimized for performance.

    Returns:
        Performance-optimized QtFixtureFactory
    """
    config = FixtureConfiguration(
        enable_session_scope=True,
        enable_cleanup_validation=False,
        validate_fixture_api=False,
        enable_debug_logging=False,
    )

    return QtFixtureFactory(config)

def create_development_qt_factory() -> QtFixtureFactory:
    """
    Create Qt fixture factory with development/debugging features.

    Returns:
        Development-friendly QtFixtureFactory
    """
    config = FixtureConfiguration(
        strict_mode=True,
        enable_debug_logging=True,
        enable_cleanup_validation=True,
        validate_fixture_api=True,
        features={
            'performance_monitoring': True,
            'adaptive_qtbot': True,
            'smart_cleanup': True,
            'error_recovery': True,
        }
    )

    return QtFixtureFactory(config)

# Export public interface
__all__ = [
    'FixtureConfiguration',
    'FixtureCreationError',
    'FixtureRegistry',
    'FixtureValidator',
    'QtFixtureFactory',
    'create_development_qt_factory',
    'create_performance_qt_factory',
    'create_test_qt_factory',
]
