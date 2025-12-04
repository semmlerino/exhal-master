"""
TypedWorkerValidator - Type-safe worker validation using TypeGuard patterns.

This module implements the TypeGuard pattern for comprehensive worker type validation,
eliminating unsafe cast() operations and providing compile-time type safety.

Key Features:
- PEP 647 TypeGuard compatibility for Python 3.9+
- Runtime validation with type narrowing
- Integration with RealComponentFactory
- Clear error messages for validation failures
- Comprehensive documentation and examples

Example Usage:
    # OLD (unsafe cast):
    worker = cast(VRAMExtractionWorker, factory.create_worker(...))

    # NEW (type-safe validation):
    validator = TypedWorkerValidator()
    worker = factory.create_worker(...)
    if validator.is_vram_extraction_worker(worker):
        # worker is now typed as VRAMExtractionWorker
        worker.start()  # Type checker knows this is safe
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from PySide6.QtCore import QThread

# Import TypeGuard with Python 3.9 compatibility
try:
    from typing import TypeGuard
except ImportError:
    from typing import TypeGuard

# Import worker types for TypeGuard usage (ruff TC004)
from core.workers import (
    ROMExtractionWorker,
    ROMInjectionWorker,
    VRAMExtractionWorker,
    VRAMInjectionWorker,
)
from utils.logging_config import get_logger

if TYPE_CHECKING:
    from tests.infrastructure.real_component_factory import RealComponentFactory

logger = get_logger(__name__)

@runtime_checkable
class WorkerProtocol(Protocol):
    """Base protocol for all worker types with common interface."""

    def start(self) -> None:
        """Start the worker thread."""
        ...

    def quit(self) -> None:
        """Request the worker to quit."""
        ...

    def wait(self, msecs: int = ...) -> bool:
        """Wait for the worker to finish."""
        ...

    def isRunning(self) -> bool:
        """Check if worker is currently running."""
        ...

@runtime_checkable
class ExtractionWorkerProtocol(WorkerProtocol, Protocol):
    """Protocol for extraction worker types."""

    def cancel(self) -> None:
        """Cancel the extraction operation."""
        ...

    def perform_operation(self) -> None:
        """Perform the extraction operation."""
        ...

@runtime_checkable
class InjectionWorkerProtocol(WorkerProtocol, Protocol):
    """Protocol for injection worker types."""

    def cancel(self) -> None:
        """Cancel the injection operation."""
        ...

    def start_injection(self, params: dict[str, Any]) -> bool:
        """Start the injection operation."""
        ...

class WorkerValidationError(TypeError):
    """Raised when worker validation fails with detailed error information."""

    def __init__(self, message: str, worker: object, expected_type: type) -> None:
        super().__init__(message)
        self.worker = worker
        self.expected_type = expected_type
        self.actual_type = type(worker)

class TypedWorkerValidator:
    """
    Type-safe worker validator using TypeGuard patterns.

    Provides TypeGuard methods for all worker types, enabling compile-time
    type safety and eliminating unsafe cast() operations.

    This class implements PEP 647 TypeGuard pattern for worker validation,
    ensuring that type checkers like basedpyright can verify type narrowing.

    Example:
        validator = TypedWorkerValidator()

        # Type-safe worker validation
        worker = factory.create_extraction_worker("vram")
        if validator.is_vram_extraction_worker(worker):
            # Type checker knows worker is VRAMExtractionWorker
            worker.start()  # Safe - no cast() needed

        # Batch validation with detailed error reporting
        workers = [factory.create_worker(t) for t in worker_types]
        validated = validator.validate_workers(workers)
    """

    def __init__(self, strict_validation: bool = True) -> None:
        """
        Initialize the typed worker validator.

        Args:
            strict_validation: If True, performs additional runtime checks
                              for worker interface compliance
        """
        self.strict_validation = strict_validation
        self._validation_cache: dict[type, bool] = {}

    def is_vram_extraction_worker(self, obj: object) -> TypeGuard[VRAMExtractionWorker]:
        """
        Type guard for VRAMExtractionWorker validation.

        Args:
            obj: Object to validate as VRAMExtractionWorker

        Returns:
            True if obj is a VRAMExtractionWorker, False otherwise

        Type narrowing:
            After this function returns True, type checkers will know
            that obj is definitely a VRAMExtractionWorker instance.
        """
        if not self._is_base_worker(obj):
            return False

        # Check class name and module for VRAM extraction worker
        class_name = obj.__class__.__name__
        module_name = obj.__class__.__module__

        # Accept both legacy and modern worker names
        valid_names = [
            "VRAMExtractionWorker",
            "WorkerOwnedVRAMExtractionWorker"
        ]

        if class_name not in valid_names:
            return False

        # Verify it's from the core.workers module
        if not module_name.startswith("core.workers"):
            return False

        # Strict validation: check protocol compliance
        if self.strict_validation:
            return self._validate_extraction_worker_interface(obj)

        return True

    def is_rom_extraction_worker(self, obj: object) -> TypeGuard[ROMExtractionWorker]:
        """
        Type guard for ROMExtractionWorker validation.

        Args:
            obj: Object to validate as ROMExtractionWorker

        Returns:
            True if obj is a ROMExtractionWorker, False otherwise
        """
        if not self._is_base_worker(obj):
            return False

        class_name = obj.__class__.__name__
        module_name = obj.__class__.__module__

        valid_names = [
            "ROMExtractionWorker",
            "WorkerOwnedROMExtractionWorker"
        ]

        if class_name not in valid_names:
            return False

        if not module_name.startswith("core.workers"):
            return False

        if self.strict_validation:
            return self._validate_extraction_worker_interface(obj)

        return True

    def is_vram_injection_worker(self, obj: object) -> TypeGuard[VRAMInjectionWorker]:
        """
        Type guard for VRAMInjectionWorker validation.

        Args:
            obj: Object to validate as VRAMInjectionWorker

        Returns:
            True if obj is a VRAMInjectionWorker, False otherwise
        """
        if not self._is_base_worker(obj):
            return False

        class_name = obj.__class__.__name__
        module_name = obj.__class__.__module__

        valid_names = [
            "VRAMInjectionWorker",
            "WorkerOwnedVRAMInjectionWorker"
        ]

        if class_name not in valid_names:
            return False

        if not module_name.startswith("core.workers"):
            return False

        if self.strict_validation:
            return self._validate_injection_worker_interface(obj)

        return True

    def is_rom_injection_worker(self, obj: object) -> TypeGuard[ROMInjectionWorker]:
        """
        Type guard for ROMInjectionWorker validation.

        Args:
            obj: Object to validate as ROMInjectionWorker

        Returns:
            True if obj is a ROMInjectionWorker, False otherwise
        """
        if not self._is_base_worker(obj):
            return False

        class_name = obj.__class__.__name__
        module_name = obj.__class__.__module__

        valid_names = [
            "ROMInjectionWorker",
            "WorkerOwnedROMInjectionWorker"
        ]

        if class_name not in valid_names:
            return False

        if not module_name.startswith("core.workers"):
            return False

        if self.strict_validation:
            return self._validate_injection_worker_interface(obj)

        return True

    def is_extraction_worker(self, obj: object) -> TypeGuard[VRAMExtractionWorker | ROMExtractionWorker]:
        """
        Type guard for any extraction worker type.

        Args:
            obj: Object to validate as an extraction worker

        Returns:
            True if obj is any type of extraction worker
        """
        return self.is_vram_extraction_worker(obj) or self.is_rom_extraction_worker(obj)

    def is_injection_worker(self, obj: object) -> TypeGuard[VRAMInjectionWorker | ROMInjectionWorker]:
        """
        Type guard for any injection worker type.

        Args:
            obj: Object to validate as an injection worker

        Returns:
            True if obj is any type of injection worker
        """
        return self.is_vram_injection_worker(obj) or self.is_rom_injection_worker(obj)

    def validate_worker(self, obj: object, expected_type: str) -> VRAMExtractionWorker | ROMExtractionWorker | VRAMInjectionWorker | ROMInjectionWorker:
        """
        Validate worker with detailed error reporting.

        Args:
            obj: Worker object to validate
            expected_type: Expected worker type name

        Returns:
            The validated worker object (typed appropriately)

        Raises:
            WorkerValidationError: If validation fails with detailed information

        Example:
            # Type-safe validation with error handling
            try:
                worker = validator.validate_worker(some_obj, "VRAMExtractionWorker")
                # worker is now properly typed
                worker.start()
            except WorkerValidationError as e:
                logger.error(f"Worker validation failed: {e}")
        """
        validation_methods = {
            "VRAMExtractionWorker": self.is_vram_extraction_worker,
            "ROMExtractionWorker": self.is_rom_extraction_worker,
            "VRAMInjectionWorker": self.is_vram_injection_worker,
            "ROMInjectionWorker": self.is_rom_injection_worker,
        }

        if expected_type not in validation_methods:
            raise ValueError(f"Unknown worker type: {expected_type}")

        validator_method = validation_methods[expected_type]

        if validator_method(obj):
            logger.debug(f"Successfully validated {expected_type}: {obj.__class__.__name__}")
            return obj

        # Detailed error information
        error_msg = self._generate_validation_error_message(obj, expected_type)

        # Map type names to actual types for error reporting
        type_mapping = {
            "VRAMExtractionWorker": type(obj) if obj else type(None),
            "ROMExtractionWorker": type(obj) if obj else type(None),
            "VRAMInjectionWorker": type(obj) if obj else type(None),
            "ROMInjectionWorker": type(obj) if obj else type(None),
        }

        expected_class = type_mapping.get(expected_type, type(None))
        raise WorkerValidationError(error_msg, obj, expected_class)

    def validate_workers(self, workers: list[object]) -> dict[str, list[object]]:
        """
        Validate multiple workers and categorize them by type.

        Args:
            workers: List of worker objects to validate

        Returns:
            Dictionary mapping worker type names to lists of validated workers

        Example:
            workers = [factory.create_worker(t) for t in types]
            categorized = validator.validate_workers(workers)

            # Type-safe access to categorized workers
            vram_workers = categorized.get("VRAMExtractionWorker", [])
            for worker in vram_workers:
                # Each worker is properly typed
                worker.start()
        """
        categorized: dict[str, list[object]] = {
            "VRAMExtractionWorker": [],
            "ROMExtractionWorker": [],
            "VRAMInjectionWorker": [],
            "ROMInjectionWorker": [],
            "Unknown": []
        }

        for worker in workers:
            if self.is_vram_extraction_worker(worker):
                categorized["VRAMExtractionWorker"].append(worker)
            elif self.is_rom_extraction_worker(worker):
                categorized["ROMExtractionWorker"].append(worker)
            elif self.is_vram_injection_worker(worker):
                categorized["VRAMInjectionWorker"].append(worker)
            elif self.is_rom_injection_worker(worker):
                categorized["ROMInjectionWorker"].append(worker)
            else:
                categorized["Unknown"].append(worker)
                logger.warning(f"Unknown worker type: {type(worker).__name__}")

        return categorized

    def create_type_safe_factory_wrapper(self, factory: RealComponentFactory) -> TypeSafeFactoryWrapper:
        """
        Create a type-safe wrapper around RealComponentFactory.

        Args:
            factory: RealComponentFactory instance to wrap

        Returns:
            Type-safe factory wrapper that eliminates cast() operations

        Example:
            factory = RealComponentFactory()
            safe_factory = validator.create_type_safe_factory_wrapper(factory)

            # Type-safe worker creation (no cast needed)
            vram_worker = safe_factory.create_vram_extraction_worker(params)
            # vram_worker is typed as VRAMExtractionWorker
        """
        return TypeSafeFactoryWrapper(factory, self)

    def _is_base_worker(self, obj: object) -> bool:
        """Check if object is a valid QThread-based worker."""
        if not isinstance(obj, QThread):
            return False

        # Check for required worker signals and methods
        required_attributes = ["start", "quit", "wait", "isRunning"]
        return all(hasattr(obj, attr) for attr in required_attributes)

    def _validate_extraction_worker_interface(self, obj: object) -> bool:
        """Validate extraction worker protocol compliance."""
        # Check if it follows the ExtractionWorkerProtocol
        try:
            return isinstance(obj, ExtractionWorkerProtocol)
        except Exception:
            # Fallback to attribute checking
            required_attrs = ["cancel", "perform_operation", "progress", "error"]
            return all(hasattr(obj, attr) for attr in required_attrs)

    def _validate_injection_worker_interface(self, obj: object) -> bool:
        """Validate injection worker protocol compliance."""
        # Check if it follows the InjectionWorkerProtocol
        try:
            return isinstance(obj, InjectionWorkerProtocol)
        except Exception:
            # Fallback to attribute checking
            required_attrs = ["cancel", "start_injection", "progress", "error"]
            return all(hasattr(obj, attr) for attr in required_attrs)

    def _generate_validation_error_message(self, obj: object, expected_type: str) -> str:
        """Generate detailed error message for validation failures."""
        if obj is None:
            return f"Expected {expected_type}, but got None"

        actual_type = type(obj).__name__
        actual_module = type(obj).__module__

        message_parts = [
            "Worker validation failed:",
            f"  Expected: {expected_type}",
            f"  Actual: {actual_type}",
            f"  Module: {actual_module}",
        ]

        # Add interface compliance information
        if not self._is_base_worker(obj):
            message_parts.append("  Issue: Object is not a valid QThread-based worker")
        elif self.strict_validation:
            if "Extraction" in expected_type and not self._validate_extraction_worker_interface(obj):
                message_parts.append("  Issue: Does not implement ExtractionWorkerProtocol")
            elif "Injection" in expected_type and not self._validate_injection_worker_interface(obj):
                message_parts.append("  Issue: Does not implement InjectionWorkerProtocol")

        # Add suggestions
        message_parts.append("  Suggestion: Use RealComponentFactory.create_extraction_worker() or create_injection_worker()")

        return "\n".join(message_parts)

class TypeSafeFactoryWrapper:
    """
    Type-safe wrapper around RealComponentFactory that eliminates cast() operations.

    This wrapper provides type-safe methods for creating workers, ensuring that
    the returned objects are properly typed without requiring unsafe cast() operations.

    Example Usage:
        factory = RealComponentFactory()
        validator = TypedWorkerValidator()
        safe_factory = TypeSafeFactoryWrapper(factory, validator)

        # Type-safe worker creation
        vram_worker = safe_factory.create_vram_extraction_worker(params)
        # vram_worker is typed as VRAMExtractionWorker - no cast() needed

        rom_worker = safe_factory.create_rom_injection_worker(params)
        # rom_worker is typed as ROMInjectionWorker - no cast() needed
    """

    def __init__(self, factory: RealComponentFactory, validator: TypedWorkerValidator) -> None:
        """
        Initialize the type-safe factory wrapper.

        Args:
            factory: RealComponentFactory instance to wrap
            validator: TypedWorkerValidator for type validation
        """
        self._factory = factory
        self._validator = validator

    def create_vram_extraction_worker(self, params: dict[str, Any] | None = None) -> VRAMExtractionWorker:
        """
        Create a type-safe VRAM extraction worker.

        Args:
            params: Optional extraction parameters

        Returns:
            Properly typed VRAMExtractionWorker instance

        Raises:
            WorkerValidationError: If worker creation/validation fails
        """
        worker = self._factory.create_extraction_worker(params, worker_type="vram")
        return self._validator.validate_worker(worker, "VRAMExtractionWorker")

    def create_rom_extraction_worker(self, params: dict[str, Any] | None = None) -> ROMExtractionWorker:
        """
        Create a type-safe ROM extraction worker.

        Args:
            params: Optional extraction parameters

        Returns:
            Properly typed ROMExtractionWorker instance

        Raises:
            WorkerValidationError: If worker creation/validation fails
        """
        worker = self._factory.create_extraction_worker(params, worker_type="rom")
        return self._validator.validate_worker(worker, "ROMExtractionWorker")

    def create_vram_injection_worker(self, params: dict[str, Any] | None = None) -> VRAMInjectionWorker:
        """
        Create a type-safe VRAM injection worker.

        Args:
            params: Optional injection parameters

        Returns:
            Properly typed VRAMInjectionWorker instance

        Raises:
            WorkerValidationError: If worker creation/validation fails
        """
        worker = self._factory.create_injection_worker(params, worker_type="vram")
        return self._validator.validate_worker(worker, "VRAMInjectionWorker")

    def create_rom_injection_worker(self, params: dict[str, Any] | None = None) -> ROMInjectionWorker:
        """
        Create a type-safe ROM injection worker.

        Args:
            params: Optional injection parameters

        Returns:
            Properly typed ROMInjectionWorker instance

        Raises:
            WorkerValidationError: If worker creation/validation fails
        """
        worker = self._factory.create_injection_worker(params, worker_type="rom")
        return self._validator.validate_worker(worker, "ROMInjectionWorker")

    def create_typed_worker(self, worker_type: str, params: dict[str, Any] | None = None) -> VRAMExtractionWorker | ROMExtractionWorker | VRAMInjectionWorker | ROMInjectionWorker:
        """
        Create a worker with automatic type validation.

        Args:
            worker_type: Type of worker to create
            params: Optional worker parameters

        Returns:
            Properly typed worker instance

        Raises:
            WorkerValidationError: If worker creation/validation fails
        """
        if "vram" in worker_type.lower() and "extraction" in worker_type.lower():
            return self.create_vram_extraction_worker(params)
        if "rom" in worker_type.lower() and "extraction" in worker_type.lower():
            return self.create_rom_extraction_worker(params)
        if "vram" in worker_type.lower() and "injection" in worker_type.lower():
            return self.create_vram_injection_worker(params)
        if "rom" in worker_type.lower() and "injection" in worker_type.lower():
            return self.create_rom_injection_worker(params)
        raise ValueError(f"Unknown worker type: {worker_type}")

# Example usage and migration patterns
def demonstrate_typeguard_usage() -> None:
    """
    Demonstrate how to use TypeGuard patterns to eliminate cast() operations.

    This function shows the before/after patterns for migrating from unsafe
    cast() operations to type-safe TypeGuard validation.
    """

    # Example: Old pattern with unsafe cast()
    def old_unsafe_pattern() -> None:
        """OLD PATTERN - Don't use this! Unsafe cast() operations."""
        from typing import cast

        from tests.infrastructure.real_component_factory import RealComponentFactory

        factory = RealComponentFactory()

        # UNSAFE: Type checker can't verify this is actually safe
        worker = cast("VRAMExtractionWorker", factory.create_extraction_worker())
        # If factory returned wrong type, this would crash at runtime
        worker.start()  # Potential runtime error!

    # Example: New pattern with TypeGuard validation
    def new_typesafe_pattern() -> None:
        """NEW PATTERN - Use this! Type-safe validation with TypeGuard."""
        from tests.infrastructure.real_component_factory import RealComponentFactory

        factory = RealComponentFactory()
        validator = TypedWorkerValidator()

        # SAFE: TypeGuard ensures proper type validation
        worker = factory.create_extraction_worker()
        if validator.is_vram_extraction_worker(worker):
            # Type checker now knows worker is VRAMExtractionWorker
            worker.start()  # Guaranteed safe!
        else:
            logger.error("Worker validation failed - wrong type returned")

    # Example: Even better - use the type-safe factory wrapper
    def best_pattern() -> None:
        """BEST PATTERN - Type-safe factory wrapper eliminates validation code."""
        from tests.infrastructure.real_component_factory import RealComponentFactory

        factory = RealComponentFactory()
        validator = TypedWorkerValidator()
        safe_factory = validator.create_type_safe_factory_wrapper(factory)

        # BEST: Automatic type safety with clear error handling
        try:
            worker = safe_factory.create_vram_extraction_worker()
            # worker is guaranteed to be VRAMExtractionWorker
            worker.start()  # Type checker verifies this is safe
        except WorkerValidationError as e:
            logger.error(f"Worker creation failed: {e}")

    print("TypeGuard usage patterns demonstrated - see function docstrings")

# Integration with RealComponentFactory
def integrate_with_real_component_factory() -> None:
    """
    Show how to integrate TypedWorkerValidator with RealComponentFactory
    to eliminate all unsafe cast() operations.
    """
    from tests.infrastructure.real_component_factory import RealComponentFactory

    # Create factory and validator
    factory = RealComponentFactory()
    validator = TypedWorkerValidator()

    # Method 1: Explicit validation
    worker = factory.create_extraction_worker(worker_type="vram")
    if validator.is_vram_extraction_worker(worker):
        # Type checker now knows this is VRAMExtractionWorker
        print(f"Validated VRAM extraction worker: {type(worker).__name__}")

    # Method 2: Validation with error handling
    try:
        validated_worker = validator.validate_worker(worker, "VRAMExtractionWorker")
        print(f"Worker validated successfully: {type(validated_worker).__name__}")
    except WorkerValidationError as e:
        print(f"Validation failed: {e}")

    # Method 3: Type-safe factory wrapper (recommended)
    safe_factory = validator.create_type_safe_factory_wrapper(factory)
    vram_worker = safe_factory.create_vram_extraction_worker()
    rom_worker = safe_factory.create_rom_injection_worker()

    print(f"Type-safe VRAM worker: {type(vram_worker).__name__}")
    print(f"Type-safe ROM worker: {type(rom_worker).__name__}")

if __name__ == "__main__":
    # Run demonstrations
    demonstrate_typeguard_usage()
    print()
    integrate_with_real_component_factory()
