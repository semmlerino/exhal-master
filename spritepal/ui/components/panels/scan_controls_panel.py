"""
Scan Controls Panel for Manual Offset Dialog

Handles all scanning functionality including range scanning, full ROM scanning,
pause/stop controls, and worker management.
"""

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spritepal.core.managers.extraction_manager import ExtractionManager
    from spritepal.core.rom_extractor import ROMExtractor

from PyQt6.QtCore import QMutex, QMutexLocker, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from spritepal.ui.components.dialogs import RangeScanDialog
from spritepal.ui.components.visualization import ROMMapWidget
from spritepal.ui.rom_extraction.workers import RangeScanWorker
from spritepal.ui.styles import get_panel_style
from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)


class ScanControlsPanel(QWidget):
    """Panel for controlling ROM scanning operations"""

    # Signals
    sprite_found = pyqtSignal(int, float)  # offset, quality
    scan_status_changed = pyqtSignal(str)  # status message
    progress_update = pyqtSignal(int)  # progress value
    scan_started = pyqtSignal()
    scan_finished = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(get_panel_style())

        # State
        self.rom_path: str = ""
        self.rom_size: int = 0x400000
        self.current_offset: int = 0x200000
        self.is_scanning: bool = False
        self.found_sprites: list[tuple[int, float]] = []

        # Manager references (set by parent)
        self.extraction_manager: ExtractionManager | None = None
        self.rom_extractor: ROMExtractor | None = None
        self._manager_mutex = QMutex()  # Thread safety for manager access

        # Worker reference
        self.range_scan_worker: RangeScanWorker | None = None

        # ROM map reference (set by parent)
        self.rom_map: ROMMapWidget | None = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Initialize the scan controls UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)  # Reduced padding
        layout.setSpacing(4)  # Tighter spacing

        label = QLabel("Enhanced Controls")
        label.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 4px;")  # Smaller and tighter
        layout.addWidget(label)

        # Scan controls
        scan_row = QHBoxLayout()
        self.scan_range_btn = QPushButton("Scan Range")
        self.scan_range_btn.setToolTip("Scan a range around current offset for sprites")
        scan_row.addWidget(self.scan_range_btn)

        self.scan_all_btn = QPushButton("Scan Entire ROM")
        self.scan_all_btn.setToolTip("Scan the entire ROM for sprite locations (slow)")
        scan_row.addWidget(self.scan_all_btn)
        layout.addLayout(scan_row)

        # Scan control buttons (pause/stop)
        control_row = QHBoxLayout()
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setToolTip("Pause or resume the current scan")
        self.pause_btn.setVisible(False)  # Hidden by default
        control_row.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setToolTip("Stop the current scan")
        self.stop_btn.setVisible(False)  # Hidden by default
        control_row.addWidget(self.stop_btn)

        control_row.addStretch()  # Push buttons to left
        layout.addLayout(control_row)

        self.setLayout(layout)

    def _connect_signals(self):
        """Connect internal signals"""
        _ = self.scan_range_btn.clicked.connect(self._scan_range)
        _ = self.scan_all_btn.clicked.connect(self._scan_all)
        _ = self.pause_btn.clicked.connect(self._toggle_pause)
        _ = self.stop_btn.clicked.connect(self._stop_scan)

    def set_rom_data(self, rom_path: str, rom_size: int, extraction_manager: "ExtractionManager"):
        """Set ROM data for scanning operations"""
        with QMutexLocker(self._manager_mutex):
            self.rom_path = rom_path
            self.rom_size = rom_size
            self.extraction_manager = extraction_manager
            self.rom_extractor = extraction_manager.get_rom_extractor()

    def _get_managers_safely(self) -> tuple["ExtractionManager | None", "ROMExtractor | None"]:
        """Get manager references safely with thread protection"""
        with QMutexLocker(self._manager_mutex):
            return self.extraction_manager, self.rom_extractor

    def set_rom_map(self, rom_map: ROMMapWidget):
        """Set the ROM map reference for visualization updates"""
        self.rom_map = rom_map

    def set_current_offset(self, offset: int):
        """Update the current offset for range scanning"""
        self.current_offset = offset

    def _scan_range(self):
        """Scan a range around current offset"""
        extraction_manager, rom_extractor = self._get_managers_safely()
        if not self.rom_path or not rom_extractor:
            self.scan_status_changed.emit("No ROM loaded")
            return

        if self.is_scanning:
            self.scan_status_changed.emit("Scan already in progress")
            return

        # Show range selection dialog
        dialog = RangeScanDialog(self.current_offset, self.rom_size, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        start_offset, end_offset = dialog.get_range()

        # Additional validation in case dialog validation was bypassed
        if not self._validate_scan_parameters(start_offset, end_offset):
            return

        # Confirm the scan
        range_kb = (end_offset - start_offset) // 1024
        result = _ = QMessageBox.question(
            self,
            "Confirm Range Scan",
            f"Scan range 0x{start_offset:06X} - 0x{end_offset:06X} ({range_kb} KB)?\n\n"
            f"This may take a few moments depending on the range size.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if result != QMessageBox.StandardButton.Yes:
            return

        self._start_range_scan(start_offset, end_offset)

    def _scan_all(self):
        """Scan entire ROM"""
        extraction_manager, rom_extractor = self._get_managers_safely()
        if not self.rom_path or not rom_extractor:
            self.scan_status_changed.emit("No ROM loaded")
            return

        if self.is_scanning:
            self.scan_status_changed.emit("Scan already in progress")
            return

        # Warn about performance impact
        rom_mb = self.rom_size // (1024 * 1024)
        result = _ = QMessageBox.question(
            self,
            "Confirm Full ROM Scan",
            f"Scan entire ROM ({rom_mb} MB)?\n\n"
            f"This will scan the full ROM for sprite data and may take several minutes.\n"
            f"The UI will remain responsive during scanning.\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No  # Default to No for safety
        )

        if result != QMessageBox.StandardButton.Yes:
            return

        # Validate full ROM scan parameters
        start_offset, end_offset = 0, self.rom_size - 1
        if not self._validate_scan_parameters(start_offset, end_offset):
            return

        # Start full ROM scan
        self._start_range_scan(start_offset, end_offset)

    def _start_range_scan(self, start_offset: int, end_offset: int):
        """Start scanning a specific range"""
        self.is_scanning = True
        self.found_sprites.clear()

        # Clear existing sprites from ROM map
        if self.rom_map:
            self.rom_map.clear_sprites()

        # Update status
        range_kb = (end_offset - start_offset) // 1024
        self.scan_status_changed.emit(f"Scanning {range_kb} KB range...")

        # Disable scan buttons during operation and show control buttons
        self.scan_range_btn.setEnabled(False)
        self.scan_all_btn.setEnabled(False)
        self.pause_btn.setVisible(True)
        self.stop_btn.setVisible(True)
        self.pause_btn.setText("Pause")  # Reset pause button text

        # Emit scan started signal
        self.scan_started.emit()

        # Create range scanning worker
        self._start_range_scan_worker(start_offset, end_offset)

    def _start_range_scan_worker(self, start_offset: int, end_offset: int):
        """Start the worker thread for range scanning with enhanced error recovery"""
        # Get ROM extractor safely
        extraction_manager, rom_extractor = self._get_managers_safely()
        if not rom_extractor:
            self.scan_status_changed.emit("ROM extractor not available")
            self._finish_scan()  # Reset UI state
            return

        # Validate ROM file accessibility
        try:
            if not self.rom_path or not os.path.exists(self.rom_path):
                self.scan_status_changed.emit("ROM file not found or inaccessible")
                self._finish_scan()
                return

            # Check file permissions
            if not os.access(self.rom_path, os.R_OK):
                self.scan_status_changed.emit("Cannot read ROM file - check permissions")
                self._finish_scan()
                return
        except OSError as e:
            self.scan_status_changed.emit(f"ROM file error: {e}")
            self._finish_scan()
            return

        # Clean up existing range scan worker with enhanced error handling
        if self.range_scan_worker:
            try:
                self.range_scan_worker.quit()
                if not self.range_scan_worker.wait(3000):  # 3 second timeout
                    logger.warning("Range scan worker cleanup timeout, terminating")
                    self.range_scan_worker.terminate()
                    if not self.range_scan_worker.wait(1000):  # 1 second for termination
                        logger.error("Range scan worker failed to terminate")
            except RuntimeError as e:
                logger.warning(f"Error during worker cleanup: {e}")
                # Continue anyway, worker may already be cleaned up

        # Create range scan worker with proper bounds and error handling
        try:
            step_size = 0x100  # 256 byte steps for comprehensive scanning
            self.range_scan_worker = RangeScanWorker(
                self.rom_path, start_offset, end_offset, step_size, rom_extractor
            )
        except Exception as e:
            logger.exception("Failed to create range scan worker")
            self.scan_status_changed.emit(f"Cannot start scan: {e}")
            self._finish_scan()
            return

        # Connect signals with error handling
        try:
            self.range_scan_worker.sprite_found.connect(self._on_range_sprite_found)
            self.range_scan_worker.progress_update.connect(self._on_range_scan_progress)
            self.range_scan_worker.scan_complete.connect(self._on_range_scan_complete)
            self.range_scan_worker.scan_paused.connect(self._on_scan_paused)
            self.range_scan_worker.scan_resumed.connect(self._on_scan_resumed)
            self.range_scan_worker.scan_stopped.connect(self._on_scan_stopped)

            # Start the worker with error recovery
            self.range_scan_worker.start()

        except RuntimeError as e:
            logger.exception("Failed to start range scan worker")
            self.scan_status_changed.emit(f"Scan startup failed: {e}")
            self._finish_scan()
        except Exception as e:
            logger.exception("Unexpected error starting scan")
            self.scan_status_changed.emit(f"Unexpected scan error: {e}")
            self._finish_scan()

    def _on_range_sprite_found(self, offset: int, quality: float):
        """Handle sprite found during range scan"""
        # Add to our found sprites list
        self.found_sprites.append((offset, quality))

        # Add to ROM map visualization
        if self.rom_map:
            self.rom_map.add_found_sprite(offset, quality)

        # Emit progress update
        self.progress_update.emit(offset)

        # Emit sprite found signal
        self.sprite_found.emit(offset, quality)

        # Update status
        count = len(self.found_sprites)
        self.scan_status_changed.emit(f"Scanning... Found {count} sprite{'s' if count != 1 else ''}")

    def _on_range_scan_progress(self, current_offset: int):
        """Handle progress updates during range scan"""
        self.progress_update.emit(current_offset)

    def _on_range_scan_complete(self, found: bool):
        """Handle range scan completion"""
        self._finish_scan()

        # Update final status
        sprite_count = len(self.found_sprites)
        if sprite_count > 0:
            self.scan_status_changed.emit(f"Range scan complete: {sprite_count} sprites found")
        else:
            self.scan_status_changed.emit("Range scan complete: No sprites found")

    def _toggle_pause(self):
        """Toggle pause/resume for the current scan"""
        if not self.range_scan_worker:
            return

        if self.range_scan_worker.is_paused():
            self.range_scan_worker.resume_scan()
        else:
            self.range_scan_worker.pause_scan()

    def _stop_scan(self):
        """Stop the current scan"""
        if self.range_scan_worker:
            self.range_scan_worker.stop_scan()

    def _on_scan_paused(self):
        """Handle scan paused signal"""
        self.pause_btn.setText("Resume")
        self.scan_status_changed.emit("Scan paused - click Resume to continue")

    def _on_scan_resumed(self):
        """Handle scan resumed signal"""
        self.pause_btn.setText("Pause")
        count = len(self.found_sprites)
        self.scan_status_changed.emit(f"Scanning... Found {count} sprite{'s' if count != 1 else ''}")

    def _on_scan_stopped(self):
        """Handle scan stopped signal"""
        self._finish_scan()

        # Update status
        sprite_count = len(self.found_sprites)
        self.scan_status_changed.emit(f"Scan stopped by user: {sprite_count} sprites found")

    def _finish_scan(self):
        """Common scan cleanup operations"""
        self.is_scanning = False

        # Re-enable scan buttons and hide control buttons
        self.scan_range_btn.setEnabled(True)
        self.scan_all_btn.setEnabled(True)
        self.pause_btn.setVisible(False)
        self.stop_btn.setVisible(False)

        # Emit scan finished signal
        self.scan_finished.emit()

    def cleanup_workers(self):
        """Clean up any running worker threads with timeouts to prevent hangs"""
        if self.range_scan_worker:
            self.range_scan_worker.quit()
            if not self.range_scan_worker.wait(5000):  # 5 second timeout
                logger.warning("Range scan worker did not stop gracefully, terminating")
                self.range_scan_worker.terminate()
                if not self.range_scan_worker.wait(2000):  # 2 second timeout for termination
                    logger.error("Range scan worker failed to terminate")
            self.range_scan_worker = None

    def get_found_sprites(self) -> list[tuple[int, float]]:
        """Get the list of found sprites"""
        return self.found_sprites.copy()

    def _validate_scan_parameters(self, start_offset: int, end_offset: int) -> bool:
        """Validate scan parameters before starting scan"""
        # Validation constants
        MIN_SCAN_SIZE = 0x100  # 256 bytes minimum
        MAX_SAFE_SCAN_SIZE = 0x400000  # 4MB for safe performance
        MAX_SCAN_SIZE = 0x2000000  # 32MB absolute maximum

        # Basic range validation
        if start_offset < 0:
            self.scan_status_changed.emit("Invalid start offset: cannot be negative")
            return False

        if end_offset >= self.rom_size:
            self.scan_status_changed.emit(f"Invalid end offset: exceeds ROM size (0x{self.rom_size:06X})")
            return False

        if start_offset >= end_offset:
            self.scan_status_changed.emit("Invalid range: start offset must be less than end offset")
            return False

        # Size validation
        scan_size = end_offset - start_offset + 1

        if scan_size < MIN_SCAN_SIZE:
            self.scan_status_changed.emit(f"Scan range too small: {scan_size} bytes (minimum {MIN_SCAN_SIZE})")
            return False

        if scan_size > MAX_SCAN_SIZE:
            self.scan_status_changed.emit(
                f"Scan range too large: {scan_size / (1024*1024):.1f} MB (maximum {MAX_SCAN_SIZE / (1024*1024):.0f} MB)"
            )
            return False

        # Performance warning for large scans
        if scan_size > MAX_SAFE_SCAN_SIZE:
            scan_mb = scan_size / (1024 * 1024)
            result = _ = QMessageBox.question(
                self,
                "Large Scan Warning",
                f"Scan size is {scan_mb:.1f} MB, which may take several minutes.\n\n"
                f"Large scans can impact system performance.\n"
                f"Continue with scan?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if result != QMessageBox.StandardButton.Yes:
                self.scan_status_changed.emit("Large scan cancelled by user")
                return False

        return True

    def is_scan_active(self) -> bool:
        """Check if a scan is currently active"""
        return self.is_scanning
