"""
Testing Infrastructure for SpritePal

This module provides comprehensive testing infrastructure to support
real Qt testing and reduce over-mocking patterns. It includes:

- TestApplicationFactory: Standardized Qt application setup (Qt-dependent)
- RealManagerFixtureFactory: Real manager instances with proper Qt parents (Qt-dependent)
- TestDataRepository: Centralized test data management (Qt-independent)
- QtTestingFramework: Standardized patterns for Qt component testing (Qt-dependent)

The infrastructure is designed to:
1. Enable real Qt testing instead of extensive mocking
2. Catch architectural bugs (especially Qt lifecycle issues)
3. Provide maintainable and understandable test patterns
4. Support both fast unit tests and comprehensive integration tests
5. Work in both Qt and headless environments

In headless environments (without PySide6), Qt-dependent features will raise
HeadlessModeError with helpful messages, while Qt-independent features remain available.
"""

from .environment_detection import get_environment_info, is_pyside6_available
from .test_data_repository import TestDataRepository

# Always available (Qt-independent)
__all__ = ["TestDataRepository", "get_environment_info", "is_pyside6_available"]

# Conditional imports based on Qt availability
if is_pyside6_available():
    try:
        from .manager_fixture_factory import RealManagerFixtureFactory
        from .qt_application_factory import (
            TestApplicationFactory,
            TestQtContext,
            qt_test_context,
        )
        from .qt_testing_framework import (
            QtTestingFramework,
            qt_dialog_test,
            qt_widget_test,
            qt_worker_test,
            validate_qt_object_lifecycle,
        )

        # Add Qt-dependent exports
        __all__.extend([
            "QtTestingFramework",
            "RealManagerFixtureFactory",
            "TestApplicationFactory",
            "TestQtContext",
            "qt_dialog_test",
            "qt_test_context",
            "qt_widget_test",
            "qt_worker_test",
            "validate_qt_object_lifecycle",
        ])

    except ImportError as e:
        # PySide6 is available but Qt modules failed to import
        # This can happen in some CI environments
        import warnings
        warnings.warn(
            f"PySide6 is available but Qt modules failed to import: {e}. "
            f"Falling back to headless mode.",
            RuntimeWarning, stacklevel=2
        )
        # Override detection function locally
        def _override_detection():
            return False
        is_pyside6_available = _override_detection

# Provide fallback implementations for headless environments
if not is_pyside6_available():
    from .headless_fallbacks import (
        HeadlessQtTestingFramework as QtTestingFramework,
    )
    from .headless_fallbacks import (
        HeadlessRealManagerFixtureFactory as RealManagerFixtureFactory,
    )
    from .headless_fallbacks import (
        HeadlessTestApplicationFactory as TestApplicationFactory,
    )
    from .headless_fallbacks import (
        HeadlessTestQtContext as TestQtContext,
    )
    from .headless_fallbacks import (
        headless_qt_dialog_test as qt_dialog_test,
    )
    from .headless_fallbacks import (
        headless_qt_test_context as qt_test_context,
    )
    from .headless_fallbacks import (
        headless_qt_widget_test as qt_widget_test,
    )
    from .headless_fallbacks import (
        headless_qt_worker_test as qt_worker_test,
    )
    from .headless_fallbacks import (
        headless_validate_qt_object_lifecycle as validate_qt_object_lifecycle,
    )

    # Add fallback exports (these will raise HeadlessModeError when used)
    __all__.extend([
        "QtTestingFramework",
        "RealManagerFixtureFactory",
        "TestApplicationFactory",
        "TestQtContext",
        "qt_dialog_test",
        "qt_test_context",
        "qt_widget_test",
        "qt_worker_test",
        "validate_qt_object_lifecycle",
    ])
