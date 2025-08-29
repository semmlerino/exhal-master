"""
Signal Router Component

Central signal coordination hub that maintains exact signal emission patterns
from the original UnifiedManualOffsetDialog.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QMutex, QMutexLocker, QObject, Signal

if TYPE_CHECKING:
    from ui.dialogs.manual_offset.components.tab_manager_component import (
        TabManagerComponent,
    )
    from ui.dialogs.manual_offset.components.worker_coordinator_component import (
        WorkerCoordinatorComponent,
    )

from utils.logging_config import get_logger

logger = get_logger(__name__)

class SignalRouterComponent(QObject):
    """
    Manages signal routing and coordination for the Manual Offset Dialog.

    This component ensures that signals are emitted in the exact same patterns
    as the original implementation, maintaining backward compatibility.
    """

    # External signals with proper typing
    offset_changed: Signal = Signal(int)
    sprite_found: Signal = Signal(int, str)
    validation_failed: Signal = Signal(str)

    # Internal signals for component communication
    request_preview: Signal = Signal(int)  # offset
    preview_ready: Signal = Signal(bytes, int, int, str)  # tile_data, width, height, name
    status_update: Signal = Signal(str)  # status message

    def __init__(self, dialog: Any) -> None:
        """Initialize the signal router."""
        super().__init__()
        self.dialog = dialog
        self._mutex = QMutex()  # For thread-safe signal management

    def emit_offset_changed(self, offset: int) -> None:
        """Emit offset changed signal."""
        logger.debug(f"Emitting offset_changed: 0x{offset:06X}")
        self.offset_changed.emit(offset)

    def emit_sprite_found(self, offset: int, name: str) -> None:
        """Emit sprite found signal."""
        logger.debug(f"Emitting sprite_found: 0x{offset:06X}, {name}")
        self.sprite_found.emit(offset, name)

    def emit_validation_failed(self, message: str) -> None:
        """Emit validation failed signal."""
        logger.debug(f"Emitting validation_failed: {message}")
        self.validation_failed.emit(message)

    def connect_to_tabs(self, tab_manager: TabManagerComponent) -> None:
        """Connect to tab manager signals."""
        with QMutexLocker(self._mutex):
            # Connect to browse tab offset changes
            if tab_manager.browse_tab and hasattr(tab_manager.browse_tab, 'offset_changed'):
                tab_manager.browse_tab.offset_changed.connect(self.emit_offset_changed)
                logger.debug("Connected to browse tab offset_changed signal")

            # Connect to any sprite found signals from tabs
            if tab_manager.history_tab and hasattr(tab_manager.history_tab, 'sprite_selected'):
                tab_manager.history_tab.sprite_selected.connect(
                    lambda offset, name="": self.emit_sprite_found(offset, name)
                )

            # Connect to gallery tab if it has sprite selection signals
            if tab_manager.gallery_tab and hasattr(tab_manager.gallery_tab, 'sprite_selected'):
                tab_manager.gallery_tab.sprite_selected.connect(
                    lambda offset, name="": self.emit_sprite_found(offset, name)
                )

    def connect_to_workers(self, worker_coordinator: WorkerCoordinatorComponent) -> None:
        """Connect to worker coordinator signals."""
        with QMutexLocker(self._mutex):
            # Connect to preview coordinator if available
            if worker_coordinator._preview_coordinator:
                # Connect preview ready signals if available
                if hasattr(worker_coordinator._preview_coordinator, 'preview_ready'):
                    worker_coordinator._preview_coordinator.preview_ready.connect(
                        self.preview_ready.emit
                    )

            # Connect to any worker status updates
            if worker_coordinator.preview_worker and hasattr(worker_coordinator.preview_worker, 'status_update'):
                worker_coordinator.preview_worker.status_update.connect(self.status_update.emit)

    def cleanup(self) -> None:
        """Clean up signal connections."""
        with QMutexLocker(self._mutex):
            logger.debug("Cleaning up signal router")
            # Disconnect all signals to prevent memory leaks
            try:
                self.offset_changed.disconnect()
            except (RuntimeError, TypeError) as e:
                logger.debug(f"Signal already disconnected or no connections: offset_changed - {e}")

            try:
                self.sprite_found.disconnect()
            except (RuntimeError, TypeError) as e:
                logger.debug(f"Signal already disconnected or no connections: sprite_found - {e}")

            try:
                self.validation_failed.disconnect()
            except (RuntimeError, TypeError) as e:
                logger.debug(f"Signal already disconnected or no connections: validation_failed - {e}")

            try:
                self.request_preview.disconnect()
            except (RuntimeError, TypeError) as e:
                logger.debug(f"Signal already disconnected or no connections: request_preview - {e}")

            try:
                self.preview_ready.disconnect()
            except (RuntimeError, TypeError) as e:
                logger.debug(f"Signal already disconnected or no connections: preview_ready - {e}")

            try:
                self.status_update.disconnect()
            except (RuntimeError, TypeError) as e:
                logger.debug(f"Signal already disconnected or no connections: status_update - {e}")
