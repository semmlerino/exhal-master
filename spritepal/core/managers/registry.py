"""
Registry for accessing manager instances
"""

import threading
from typing import Any

from PyQt6.QtWidgets import QApplication
from utils.logging_config import get_logger

from .exceptions import ManagerError
from .extraction_manager import ExtractionManager
from .injection_manager import InjectionManager
from .session_manager import SessionManager


class ManagerRegistry:
    """Singleton registry for manager instances"""

    _instance: "ManagerRegistry | None" = None
    _lock: threading.Lock = threading.Lock()

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
        Initialize all managers with proper error handling and cleanup

        Args:
            app_name: Application name for settings
            settings_path: Optional custom settings path (for testing)
            
        Raises:
            ManagerError: If manager initialization fails
        """
        with self._lock:  # Ensure thread-safe initialization
            # Skip if already initialized
            if self.is_initialized():
                self._logger.debug("Managers already initialized, skipping")
                return

            self._logger.info("Initializing managers...")

            # Get Qt application instance for proper parent management
            app = QApplication.instance()
            if not app:
                self._logger.warning("No QApplication instance found - managers will have no Qt parent")
                qt_parent = None
            else:
                qt_parent = app
                self._logger.debug("Using QApplication as Qt parent for managers")

            # Track which managers were created for cleanup on failure
            created_managers = []

            try:
                # Initialize session manager first as others may depend on it
                # SessionManager inherits from BaseManager (QObject), so it can take a parent
                self._logger.debug("Creating SessionManager...")
                session_manager = SessionManager(app_name, settings_path)
                session_manager.setParent(qt_parent)  # Set parent after creation
                self._managers["session"] = session_manager
                created_managers.append("session")
                self._logger.debug("SessionManager created successfully")

                # Initialize Qt-based managers with proper parent to prevent lifecycle issues
                self._logger.debug("Creating ExtractionManager...")
                self._managers["extraction"] = ExtractionManager(parent=qt_parent)
                created_managers.append("extraction")
                self._logger.debug("ExtractionManager created successfully")

                self._logger.debug("Creating InjectionManager...")
                self._managers["injection"] = InjectionManager(parent=qt_parent)
                created_managers.append("injection")
                self._logger.debug("InjectionManager created successfully")

                # Future managers will be added here

                self._logger.info("All managers initialized successfully")

            except Exception as e:
                self._logger.error(f"Manager initialization failed: {e}")

                # Cleanup any managers that were created before the failure
                for manager_name in created_managers:
                    try:
                        if manager_name in self._managers:
                            manager = self._managers[manager_name]
                            manager.cleanup()
                            del self._managers[manager_name]
                            self._logger.debug(f"Cleaned up {manager_name} manager after initialization failure")
                    except Exception as cleanup_error:
                        self._logger.error(f"Error cleaning up {manager_name} manager: {cleanup_error}")

                # Re-raise as ManagerError
                raise ManagerError(f"Failed to initialize managers: {e}") from e

    def cleanup_managers(self) -> None:
        """Cleanup all managers"""
        self._logger.info("Cleaning up managers...")

        # Cleanup in reverse order
        for name in reversed(list(self._managers.keys())):
            try:
                manager = self._managers[name]
                manager.cleanup()
                self._logger.debug(f"Cleaned up {name} manager")
            except (AttributeError, RuntimeError):
                self._logger.exception(f"Error cleaning up {name} manager")
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
        Get a manager by name with type checking and dependency validation

        Args:
            name: Manager name
            expected_type: Expected manager type

        Returns:
            Manager instance

        Raises:
            ManagerError: If manager not found, wrong type, or not properly initialized
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

        # Validate that the manager is properly initialized
        if not manager.is_initialized():
            raise ManagerError(
                f"{name.capitalize()} manager found but not properly initialized. "
                "This may indicate a partial initialization failure."
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

    def validate_manager_dependencies(self) -> bool:
        """
        Validate that all managers and their dependencies are properly initialized
        
        Returns:
            True if all dependencies are satisfied, False otherwise
            
        Raises:
            ManagerError: If critical dependency issues are found
        """
        if not self.is_initialized():
            self._logger.warning("Managers not initialized, cannot validate dependencies")
            return False

        self._logger.debug("Validating manager dependencies...")

        try:
            # Validate that all managers are individually initialized
            for name, manager in self._managers.items():
                if not manager.is_initialized():
                    raise ManagerError(f"{name} manager not properly initialized")

            # Validate specific dependency relationships
            # InjectionManager depends on SessionManager
            injection_manager = self._managers.get("injection")
            session_manager = self._managers.get("session")

            if injection_manager and not session_manager:
                raise ManagerError("InjectionManager requires SessionManager but it's not available")

            self._logger.debug("All manager dependencies validated successfully")
            return True

        except Exception as e:
            self._logger.error(f"Manager dependency validation failed: {e}")
            return False


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


def validate_manager_dependencies() -> bool:
    """
    Validate that all manager dependencies are satisfied
    
    Returns:
        True if all dependencies are valid, False otherwise
    """
    return _registry.validate_manager_dependencies()
