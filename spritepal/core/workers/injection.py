"""
Injection worker implementations using the new base classes.

These workers handle VRAM and ROM injection operations by delegating
to the InjectionManager while providing consistent threading interfaces.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, override

if TYPE_CHECKING:
    from PyQt6.QtCore import QObject

    from spritepal.core.managers import InjectionManager
    from spritepal.core.managers.factory import ManagerFactory

from spritepal.core.managers import get_injection_manager
from spritepal.core.managers.factory import StandardManagerFactory
from spritepal.utils.logging_config import get_logger

from .specialized import InjectionWorkerBase

logger = get_logger(__name__)


# Type definitions for injection parameters
class VRAMInjectionParams(TypedDict, total=False):
    """Type definition for VRAM injection parameters"""
    mode: str  # "vram"
    sprite_path: str
    input_vram: str
    output_vram: str
    offset: int
    metadata_path: str | None


class ROMInjectionParams(TypedDict, total=False):
    """Type definition for ROM injection parameters"""
    mode: str  # "rom"
    sprite_path: str
    input_rom: str
    output_rom: str
    offset: int
    fast_compression: bool
    metadata_path: str | None


class VRAMInjectionWorker(InjectionWorkerBase):
    """
    Worker for VRAM injection operations using singleton InjectionManager.

    Handles injection of sprites into VRAM memory dumps using the global
    InjectionManager, providing progress updates during the injection process.
    """

    def __init__(self, params: VRAMInjectionParams, parent: QObject | None = None) -> None:
        manager = get_injection_manager()
        super().__init__(manager, parent)
        self.params = params
        self._operation_name = "VRAMInjectionWorker"

    @override
    def connect_manager_signals(self) -> None:
        """Connect injection manager signals to worker signals."""
        if not isinstance(self.manager, type(get_injection_manager())):
            logger.error("Invalid manager type for VRAM injection")
            return

        # Type cast for better type checking
        injection_manager: InjectionManager = self.manager

        # Connect standard progress signal
        connection1 = injection_manager.injection_progress.connect(
            lambda msg: self.emit_progress(50, msg)
        )
        self._connections.append(connection1)

        # Connect injection-specific signals
        connection2 = injection_manager.injection_finished.connect(self.injection_finished.emit)
        connection3 = injection_manager.progress_percent.connect(self.progress_percent.emit)
        connection4 = injection_manager.compression_info.connect(self.compression_info.emit)
        self._connections.extend([connection2, connection3, connection4])

        # Connect injection completion to worker operation completion
        def on_injection_finished(success: bool, message: str) -> None:
            """Handle injection completion and emit worker completion signal."""
            self.operation_finished.emit(success, f"Injection {'completed' if success else 'failed'}: {message}")

        connection5 = injection_manager.injection_finished.connect(on_injection_finished)
        self._connections.append(connection5)

        logger.debug(f"{self._operation_name}: Connected {len(self._connections)} manager signals")

    @override
    def perform_operation(self) -> None:
        """Perform VRAM injection via manager."""
        try:
            # Type cast for better type safety
            injection_manager: InjectionManager = self.manager

            # Check for cancellation before starting
            self.check_cancellation()

            logger.info(f"{self._operation_name}: Starting VRAM injection")
            self.emit_progress(10, "Starting VRAM injection...")

            # Perform injection using manager
            success = injection_manager.start_injection(dict(self.params))

            if success:
                logger.info(f"{self._operation_name}: Injection started successfully")
                # The manager will emit completion signals when done via connected signals
            else:
                error_msg = "Failed to start injection"
                logger.error(f"{self._operation_name}: {error_msg}")
                self.emit_error(error_msg)
                self.operation_finished.emit(False, error_msg)

        except InterruptedError:
            # Re-raise cancellation to be handled by base class
            raise
        except Exception as e:
            error_msg = f"VRAM injection failed: {e!s}"
            logger.exception(f"{self._operation_name}: {error_msg}", exc_info=e)
            self.emit_error(error_msg, e)
            self.operation_finished.emit(False, error_msg)


class ROMInjectionWorker(InjectionWorkerBase):
    """
    Worker for ROM injection operations using singleton InjectionManager.

    Handles injection of sprites into ROM files using the global
    InjectionManager, providing progress updates and compression info.
    """

    def __init__(self, params: ROMInjectionParams, parent: QObject | None = None) -> None:
        manager = get_injection_manager()
        super().__init__(manager, parent)
        self.params = params
        self._operation_name = "ROMInjectionWorker"

    @override
    def connect_manager_signals(self) -> None:
        """Connect injection manager signals to worker signals."""
        if not isinstance(self.manager, type(get_injection_manager())):
            logger.error("Invalid manager type for ROM injection")
            return

        # Type cast for better type checking
        injection_manager: InjectionManager = self.manager

        # Connect standard progress signal
        connection1 = injection_manager.injection_progress.connect(
            lambda msg: self.emit_progress(50, msg)
        )
        self._connections.append(connection1)

        # Connect injection-specific signals
        connection2 = injection_manager.injection_finished.connect(self.injection_finished.emit)
        connection3 = injection_manager.progress_percent.connect(self.progress_percent.emit)
        connection4 = injection_manager.compression_info.connect(self.compression_info.emit)
        self._connections.extend([connection2, connection3, connection4])

        # Connect injection completion to worker operation completion
        def on_injection_finished(success: bool, message: str) -> None:
            """Handle injection completion and emit worker completion signal."""
            self.operation_finished.emit(success, f"Injection {'completed' if success else 'failed'}: {message}")

        connection5 = injection_manager.injection_finished.connect(on_injection_finished)
        self._connections.append(connection5)

        logger.debug(f"{self._operation_name}: Connected {len(self._connections)} manager signals")

    @override
    def perform_operation(self) -> None:
        """Perform ROM injection via manager."""
        try:
            # Type cast for better type safety
            injection_manager: InjectionManager = self.manager

            # Check for cancellation before starting
            self.check_cancellation()

            logger.info(f"{self._operation_name}: Starting ROM injection")
            self.emit_progress(10, "Starting ROM injection...")

            # Perform injection using manager
            success = injection_manager.start_injection(dict(self.params))

            if success:
                logger.info(f"{self._operation_name}: ROM injection started successfully")
                # The manager will emit completion signals when done
            else:
                error_msg = "Failed to start ROM injection"
                logger.error(f"{self._operation_name}: {error_msg}")
                self.emit_error(error_msg)
                self.operation_finished.emit(False, error_msg)

        except InterruptedError:
            # Re-raise cancellation to be handled by base class
            raise
        except Exception as e:
            error_msg = f"ROM injection failed: {e!s}"
            logger.exception(f"{self._operation_name}: {error_msg}", exc_info=e)
            self.emit_error(error_msg, e)
            self.operation_finished.emit(False, error_msg)


# Worker-owned manager pattern (Phase 2 architecture)
class WorkerOwnedVRAMInjectionWorker(InjectionWorkerBase):
    """
    VRAM injection worker that owns its own InjectionManager instance.

    This pattern provides perfect thread isolation and eliminates cross-thread
    issues by ensuring each worker has its own manager with proper Qt parent.
    Recommended for new code.
    """

    def __init__(
        self,
        params: VRAMInjectionParams,
        manager_factory: ManagerFactory | None = None,
        parent: QObject | None = None
    ) -> None:
        # Create manager factory if none provided
        if manager_factory is None:
            # We can't use self as parent yet since super().__init__ hasn't been called
            # So we'll fix the parent after initialization
            manager_factory = StandardManagerFactory(default_parent_strategy="none")

        # Create the manager (parent will be set after super init)
        manager = manager_factory.create_injection_manager(parent=parent)

        # Initialize parent class with the manager
        super().__init__(manager, parent)

        # Now fix the manager's parent to be this worker for proper ownership
        manager.setParent(self)

        self.params = params
        self._operation_name = "WorkerOwnedVRAMInjectionWorker"

        logger.info(f"{self._operation_name}: Created with worker-owned manager")

    @override
    def connect_manager_signals(self) -> None:
        """Connect injection manager signals to worker signals."""
        if not isinstance(self.manager, type(get_injection_manager())):
            logger.error("Invalid manager type for VRAM injection")
            return

        # Type cast for better type checking
        injection_manager: InjectionManager = self.manager

        # Connect standard progress signal
        connection1 = injection_manager.injection_progress.connect(
            lambda msg: self.emit_progress(50, msg)
        )
        self._connections.append(connection1)

        # Connect injection-specific signals
        connection2 = injection_manager.injection_finished.connect(self.injection_finished.emit)
        connection3 = injection_manager.progress_percent.connect(self.progress_percent.emit)
        connection4 = injection_manager.compression_info.connect(self.compression_info.emit)
        self._connections.extend([connection2, connection3, connection4])

        # Connect injection completion to worker operation completion
        def on_injection_finished(success: bool, message: str) -> None:
            """Handle injection completion and emit worker completion signal."""
            self.operation_finished.emit(success, f"Injection {'completed' if success else 'failed'}: {message}")

        connection5 = injection_manager.injection_finished.connect(on_injection_finished)
        self._connections.append(connection5)

        logger.debug(f"{self._operation_name}: Connected {len(self._connections)} manager signals")

    @override
    def perform_operation(self) -> None:
        """Perform VRAM injection via worker-owned manager."""
        try:
            # Type cast for better type safety
            injection_manager: InjectionManager = self.manager

            # Check for cancellation before starting
            self.check_cancellation()

            logger.info(f"{self._operation_name}: Starting VRAM injection")
            self.emit_progress(10, "Starting VRAM injection...")

            # Perform injection using manager
            success = injection_manager.start_injection(dict(self.params))

            if success:
                logger.info(f"{self._operation_name}: Injection started successfully")
                # The manager will emit completion signals when done via connected signals
            else:
                error_msg = "Failed to start injection"
                logger.error(f"{self._operation_name}: {error_msg}")
                self.emit_error(error_msg)
                self.operation_finished.emit(False, error_msg)

        except InterruptedError:
            # Re-raise cancellation to be handled by base class
            raise
        except Exception as e:
            error_msg = f"VRAM injection failed: {e!s}"
            logger.exception(f"{self._operation_name}: {error_msg}", exc_info=e)
            self.emit_error(error_msg, e)
            self.operation_finished.emit(False, error_msg)


class WorkerOwnedROMInjectionWorker(InjectionWorkerBase):
    """
    ROM injection worker that owns its own InjectionManager instance.

    This pattern provides perfect thread isolation and eliminates cross-thread
    issues by ensuring each worker has its own manager with proper Qt parent.
    Recommended for new code.
    """

    def __init__(
        self,
        params: ROMInjectionParams,
        manager_factory: ManagerFactory | None = None,
        parent: QObject | None = None
    ) -> None:
        # Create manager factory if none provided
        if manager_factory is None:
            # We can't use self as parent yet since super().__init__ hasn't been called
            # So we'll fix the parent after initialization
            manager_factory = StandardManagerFactory(default_parent_strategy="none")

        # Create the manager (parent will be set after super init)
        manager = manager_factory.create_injection_manager(parent=parent)

        # Initialize parent class with the manager
        super().__init__(manager, parent)

        # Now fix the manager's parent to be this worker for proper ownership
        manager.setParent(self)

        self.params = params
        self._operation_name = "WorkerOwnedROMInjectionWorker"

        logger.info(f"{self._operation_name}: Created with worker-owned manager")

    @override
    def connect_manager_signals(self) -> None:
        """Connect injection manager signals to worker signals."""
        if not isinstance(self.manager, type(get_injection_manager())):
            logger.error("Invalid manager type for ROM injection")
            return

        # Type cast for better type checking
        injection_manager: InjectionManager = self.manager

        # Connect standard progress signal
        connection1 = injection_manager.injection_progress.connect(
            lambda msg: self.emit_progress(50, msg)
        )
        self._connections.append(connection1)

        # Connect injection-specific signals
        connection2 = injection_manager.injection_finished.connect(self.injection_finished.emit)
        connection3 = injection_manager.progress_percent.connect(self.progress_percent.emit)
        connection4 = injection_manager.compression_info.connect(self.compression_info.emit)
        self._connections.extend([connection2, connection3, connection4])

        # Connect injection completion to worker operation completion
        def on_injection_finished(success: bool, message: str) -> None:
            """Handle injection completion and emit worker completion signal."""
            self.operation_finished.emit(success, f"Injection {'completed' if success else 'failed'}: {message}")

        connection5 = injection_manager.injection_finished.connect(on_injection_finished)
        self._connections.append(connection5)

        logger.debug(f"{self._operation_name}: Connected {len(self._connections)} manager signals")

    @override
    def perform_operation(self) -> None:
        """Perform ROM injection via worker-owned manager."""
        try:
            # Type cast for better type safety
            injection_manager: InjectionManager = self.manager

            # Check for cancellation before starting
            self.check_cancellation()

            logger.info(f"{self._operation_name}: Starting ROM injection")
            self.emit_progress(10, "Starting ROM injection...")

            # Perform injection using manager
            success = injection_manager.start_injection(dict(self.params))

            if success:
                logger.info(f"{self._operation_name}: ROM injection started successfully")
                # The manager will emit completion signals when done
            else:
                error_msg = "Failed to start ROM injection"
                logger.error(f"{self._operation_name}: {error_msg}")
                self.emit_error(error_msg)
                self.operation_finished.emit(False, error_msg)

        except InterruptedError:
            # Re-raise cancellation to be handled by base class
            raise
        except Exception as e:
            error_msg = f"ROM injection failed: {e!s}"
            logger.exception(f"{self._operation_name}: {error_msg}", exc_info=e)
            self.emit_error(error_msg, e)
            self.operation_finished.emit(False, error_msg)
