"""
Testing Infrastructure for SpritePal

This module provides comprehensive testing infrastructure to support
real Qt testing and reduce over-mocking patterns. It includes:

- TestApplicationFactory: Standardized Qt application setup
- RealManagerFixtureFactory: Real manager instances with proper Qt parents  
- TestDataRepository: Centralized test data management
- QtTestingFramework: Standardized patterns for Qt component testing

The infrastructure is designed to:
1. Enable real Qt testing instead of extensive mocking
2. Catch architectural bugs (especially Qt lifecycle issues)
3. Provide maintainable and understandable test patterns
4. Support both fast unit tests and comprehensive integration tests
"""

from .qt_application_factory import TestApplicationFactory, TestQtContext, qt_test_context
from .manager_fixture_factory import RealManagerFixtureFactory
from .test_data_repository import TestDataRepository
from .qt_testing_framework import (
    QtTestingFramework, 
    qt_widget_test, 
    qt_dialog_test, 
    qt_worker_test,
    validate_qt_object_lifecycle
)

__all__ = [
    "TestApplicationFactory",
    "TestQtContext", 
    "qt_test_context",
    "RealManagerFixtureFactory",
    "TestDataRepository",
    "QtTestingFramework",
    "qt_widget_test",
    "qt_dialog_test", 
    "qt_worker_test",
    "validate_qt_object_lifecycle",
]