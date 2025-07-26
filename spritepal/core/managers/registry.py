"""
Registry for accessing manager instances
"""

import threading
from typing import Any

from spritepal.core.managers.exceptions import ManagerError
from spritepal.core.managers.extraction_manager import ExtractionManager
from spritepal.core.managers.session_manager import SessionManager
from spritepal.utils.logging_config import get_logger


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

    def initialize_managers(self, app_name: str = "SpritePal") -> None:
        """
        Initialize all managers

        Args:
            app_name: Application name for settings
        """
        with self._lock:  # Ensure thread-safe initialization
            # Skip if already initialized
            if self.is_initialized():
                self._logger.debug("Managers already initialized, skipping")
                return

            self._logger.info("Initializing managers...")

            # Initialize session manager first as others may depend on it
            self._managers["session"] = SessionManager(app_name)

            # Initialize other managers
            self._managers["extraction"] = ExtractionManager()

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
                self._logger.exception(f"Error cleaning up {name} manager")

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
        expected_managers = {"session", "extraction"}
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


def initialize_managers(app_name: str = "SpritePal") -> None:
    """
    Initialize all managers

    Args:
        app_name: Application name for settings
    """
    _registry.initialize_managers(app_name)


def cleanup_managers() -> None:
    """Cleanup all managers"""
    _registry.cleanup_managers()


def are_managers_initialized() -> bool:
    """Check if managers are initialized"""
    return _registry.is_initialized()
