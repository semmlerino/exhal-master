"""
Registry for accessing manager instances
"""

import threading
from typing import Any

from .exceptions import ManagerError
from .extraction_manager import ExtractionManager
from .injection_manager import InjectionManager
from .session_manager import SessionManager
from utils.logging_config import get_logger


class ManagerRegistry:
    """Singleton registry for manager instances"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls) -> "ManagerRegistry":
        """Ensure only one instance exists"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the registry"""
        # Only initialize once
        if hasattr(self, "_initialized"):
            return

        self._logger = get_logger("ManagerRegistry")
        self._managers: dict[str, Any] = {}
        self._initialized = True
        self._logger.info("ManagerRegistry initialized")

    def initialize_managers(self, app_name: str = "SpritePal", settings_path: Any = None) -> None:
        """
        Initialize all managers

        Args:
            app_name: Application name for settings
            settings_path: Optional custom settings path (for testing)
        """
        with self._lock:  # Ensure thread-safe initialization
            # Skip if already initialized
            if self.is_initialized():
                self._logger.debug("Managers already initialized, skipping")
                return

            self._logger.info("Initializing managers...")

            # Get Qt application instance for proper parent management
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if not app:
                self._logger.warning("No QApplication instance found - managers will have no Qt parent")
                qt_parent = None
            else:
                qt_parent = app
                self._logger.debug("Using QApplication as Qt parent for managers")

            # Initialize session manager first as others may depend on it
            # Note: SessionManager doesn't inherit from QObject, so no parent needed
            self._managers["session"] = SessionManager(app_name, settings_path)

            # Initialize Qt-based managers with proper parent to prevent lifecycle issues
            self._managers["extraction"] = ExtractionManager(parent=qt_parent)
            self._managers["injection"] = InjectionManager(parent=qt_parent)

            # Future managers will be added here

            self._logger.info("All managers initialized successfully")

    def cleanup_managers(self) -> None:
        """Cleanup all managers"""
        self._logger.info("Cleaning up managers...")

        # Cleanup in reverse order
        for name in reversed(list(self._managers.keys())):
            try:
                manager = self._managers[name]
                manager.cleanup()
                self._logger.debug(f"Cleaned up {name} manager")
            except Exception:
                self._logger.exception("Error cleaning up %s manager", name)

        self._managers.clear()
        self._logger.info("All managers cleaned up")

    def get_session_manager(self) -> SessionManager:
        """
        Get the session manager instance

        Returns:
            SessionManager instance

        Raises:
            ManagerError: If manager not initialized
        """
        return self._get_manager("session", SessionManager)

    def get_extraction_manager(self) -> ExtractionManager:
        """
        Get the extraction manager instance

        Returns:
            ExtractionManager instance

        Raises:
            ManagerError: If manager not initialized
        """
        return self._get_manager("extraction", ExtractionManager)

    def get_injection_manager(self) -> InjectionManager:
        """
        Get the injection manager instance

        Returns:
            InjectionManager instance

        Raises:
            ManagerError: If manager not initialized
        """
        return self._get_manager("injection", InjectionManager)

    def _get_manager(self, name: str, expected_type: type) -> Any:
        """
        Get a manager by name with type checking

        Args:
            name: Manager name
            expected_type: Expected manager type

        Returns:
            Manager instance

        Raises:
            ManagerError: If manager not found or wrong type
        """
        if name not in self._managers:
            raise ManagerError(
                f"{name.capitalize()} manager not initialized. "
                "Call initialize_managers() first."
            )

        manager = self._managers[name]
        if not isinstance(manager, expected_type):
            raise ManagerError(
                f"Manager type mismatch: expected {expected_type.__name__}, "
                f"got {type(manager).__name__}"
            )

        return manager

    def is_initialized(self) -> bool:
        """Check if managers are initialized"""
        # Check that all expected managers are present
        expected_managers = {"session", "extraction", "injection"}
        return expected_managers.issubset(self._managers.keys())

    def get_all_managers(self) -> dict[str, Any]:
        """Get all registered managers (for testing/debugging)"""
        return self._managers.copy()


# Global instance accessor functions
_registry = ManagerRegistry()


def get_registry() -> ManagerRegistry:
    """Get the global manager registry instance"""
    return _registry


def get_session_manager() -> SessionManager:
    """
    Get the global session manager instance

    Returns:
        SessionManager instance

    Raises:
        ManagerError: If managers not initialized
    """
    return _registry.get_session_manager()


def get_extraction_manager() -> ExtractionManager:
    """
    Get the global extraction manager instance

    Returns:
        ExtractionManager instance

    Raises:
        ManagerError: If managers not initialized
    """
    return _registry.get_extraction_manager()


def get_injection_manager() -> InjectionManager:
    """
    Get the global injection manager instance

    Returns:
        InjectionManager instance

    Raises:
        ManagerError: If managers not initialized
    """
    return _registry.get_injection_manager()


def initialize_managers(app_name: str = "SpritePal", settings_path: Any = None) -> None:
    """
    Initialize all managers

    Args:
        app_name: Application name for settings
        settings_path: Optional custom settings path (for testing)
    """
    _registry.initialize_managers(app_name, settings_path)


def cleanup_managers() -> None:
    """Cleanup all managers"""
    _registry.cleanup_managers()


def are_managers_initialized() -> bool:
    """Check if managers are initialized"""
    return _registry.is_initialized()
