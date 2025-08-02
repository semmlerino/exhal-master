"""
Specialized worker base classes for different operation types.

These classes extend the base worker classes with domain-specific
signals and behavior for extraction, injection, and scanning operations.
"""

from typing import Any, Optional

from core.managers.base_manager import BaseManager
from PyQt6.QtCore import QObject, pyqtSignal

from .base import BaseWorker, ManagedWorker


class ExtractionWorkerBase(ManagedWorker):
    """
    Base class for extraction workers with extraction-specific signals.

    Provides signals for preview generation, palette data, and other
    extraction-specific events.
    """

    # Extraction-specific signals
    preview_ready = pyqtSignal(object, int)  # pixmap/image, tile_count
    preview_image_ready = pyqtSignal(object)  # PIL image for palette application
    palettes_ready = pyqtSignal(dict)  # palette data
    active_palettes_ready = pyqtSignal(list)  # active palette indices
    extraction_finished = pyqtSignal(list)  # list of extracted files

    def __init__(self, manager: BaseManager, parent: Optional[QObject] = None) -> None:
        super().__init__(manager=manager, parent=parent)
        self._operation_name = "ExtractionWorker"


class InjectionWorkerBase(ManagedWorker):
    """
    Base class for injection workers with injection-specific signals.

    Provides signals for compression information, progress percentages,
    and other injection-specific events.
    """

    # Injection-specific signals
    progress_percent = pyqtSignal(int)  # Progress percentage (0-100)
    compression_info = pyqtSignal(dict)  # Compression statistics
    injection_finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, manager: BaseManager, parent: Optional[QObject] = None) -> None:
        super().__init__(manager=manager, parent=parent)
        self._operation_name = "InjectionWorker"


class ScanWorkerBase(BaseWorker):
    """
    Base class for scanning workers with scan-specific signals.

    Used for ROM scanning, sprite searching, and other discovery operations.
    Note: Inherits from BaseWorker (not ManagedWorker) as scan operations
    often contain their own business logic.
    """

    # Scan-specific signals
    item_found = pyqtSignal(dict)  # Found item information
    scan_stats = pyqtSignal(dict)  # Scan statistics and metadata
    scan_progress = pyqtSignal(int, int)  # current, total
    scan_finished = pyqtSignal(bool)  # success

    # Cache-related signals (for ROM scanning)
    cache_status = pyqtSignal(str)  # Cache status message
    cache_progress = pyqtSignal(int)  # Cache save progress 0-100

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._operation_name = "ScanWorker"

    def emit_item_found(self, item_info: dict[str, Any]) -> None:
        """
        Emit when an item is found during scanning.

        Args:
            item_info: Dictionary containing item details
        """
        self.item_found.emit(item_info)

    def emit_scan_progress(self, current: int, total: int) -> None:
        """
        Emit scan progress in current/total format.

        Args:
            current: Current item being processed
            total: Total items to process
        """
        self.scan_progress.emit(current, total)

        # Also emit standard progress percentage
        if total > 0:
            percent = int((current / total) * 100)
            self.emit_progress(percent, f"Scanning {current}/{total}")


class PreviewWorkerBase(BaseWorker):
    """
    Base class for preview generation workers.

    Used for generating sprite previews, ROM map visualizations,
    and other UI preview operations.
    """

    # Preview-specific signals
    preview_ready = pyqtSignal(object)  # Generated preview (QPixmap, PIL Image, etc.)
    preview_failed = pyqtSignal(str)  # Preview generation failed

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._operation_name = "PreviewWorker"

    def emit_preview_ready(self, preview: Any) -> None:
        """
        Emit when preview is ready.

        Args:
            preview: Generated preview object
        """
        self.preview_ready.emit(preview)

    def emit_preview_failed(self, error_message: str) -> None:
        """
        Emit when preview generation fails.

        Args:
            error_message: Error description
        """
        self.preview_failed.emit(error_message)
        self.emit_error(error_message)
