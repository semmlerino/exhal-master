"""
Extraction worker implementations using the new base classes.

These workers handle VRAM and ROM extraction operations by delegating
to the ExtractionManager while providing consistent threading interfaces.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, TypedDict, override

from PyQt6.QtCore import QMetaObject, QObject
from PIL import Image

if TYPE_CHECKING:
    from spritepal.core.managers import ExtractionManager
    from spritepal.core.managers.factory import ManagerFactory

from spritepal.core.managers import get_extraction_manager
from spritepal.core.managers.factory import get_default_factory, create_per_worker_factory
from spritepal.utils.image_utils import pil_to_qpixmap
from spritepal.utils.logging_config import get_logger

from .specialized import ExtractionWorkerBase

logger = get_logger(__name__)


# Type definitions for extraction parameters
class VRAMExtractionParams(TypedDict, total=False):
    """Type definition for VRAM extraction parameters"""
    vram_path: str
    cgram_path: Optional[str]
    oam_path: Optional[str]
    vram_offset: Optional[int]
    output_base: str
    create_grayscale: bool
    create_metadata: bool
    grayscale_mode: bool


class ROMExtractionParams(TypedDict, total=False):
    """Type definition for ROM extraction parameters"""
    rom_path: str
    sprite_offset: int
    output_base: str
    sprite_name: str
    cgram_path: Optional[str]


class VRAMExtractionWorker(ExtractionWorkerBase):
    """
    Worker for VRAM extraction operations.
    
    Handles extraction of sprites from VRAM memory dumps using the
    ExtractionManager, providing progress updates and preview generation.
    """
    
    def __init__(self, params: VRAMExtractionParams, parent: Optional[QObject] = None) -> None:
        manager = get_extraction_manager()
        super().__init__(manager=manager, parent=parent)
        self.params = params
        self._operation_name = "VRAMExtractionWorker"
    
    @override
    def connect_manager_signals(self) -> None:
        """Connect extraction manager signals to worker signals."""
        if not isinstance(self.manager, type(get_extraction_manager())):
            logger.error("Invalid manager type for VRAM extraction")
            return
            
        # Type cast for better type checking
        extraction_manager: ExtractionManager = self.manager
        
        # Connect standard progress signal
        connection1 = extraction_manager.extraction_progress.connect(
            lambda msg: self.emit_progress(50, msg)
        )
        self._connections.append(connection1)
        
        # Connect extraction-specific signals
        connection2 = extraction_manager.palettes_extracted.connect(self.palettes_ready.emit)
        connection3 = extraction_manager.active_palettes_found.connect(self.active_palettes_ready.emit)
        self._connections.extend([connection2, connection3])
        
        # Handle preview generation with PIL to QPixmap conversion
        def on_preview_generated(img: Image.Image, tile_count: int) -> None:
            try:
                pixmap = pil_to_qpixmap(img)
                self.preview_ready.emit(pixmap, tile_count)
                self.preview_image_ready.emit(img)
            except Exception as e:
                logger.error(f"Failed to convert preview image: {e}")
                self.emit_warning(f"Preview generation failed: {e}")
        
        connection4 = extraction_manager.preview_generated.connect(on_preview_generated)
        self._connections.append(connection4)
        
        logger.debug(f"{self._operation_name}: Connected {len(self._connections)} manager signals")
    
    @override
    def perform_operation(self) -> None:
        """Perform VRAM extraction via manager."""
        try:
            # Type cast for better type safety
            extraction_manager: ExtractionManager = self.manager
            
            # Check for cancellation before starting
            self.check_cancellation()
            
            logger.info(f"{self._operation_name}: Starting VRAM extraction")
            self.emit_progress(10, "Starting VRAM extraction...")
            
            # Perform extraction using manager
            extracted_files = extraction_manager.extract_from_vram(
                vram_path=self.params["vram_path"],
                output_base=self.params["output_base"],
                cgram_path=self.params.get("cgram_path"),
                oam_path=self.params.get("oam_path"),
                vram_offset=self.params.get("vram_offset"),
                create_grayscale=self.params.get("create_grayscale", True),
                create_metadata=self.params.get("create_metadata", True),
                grayscale_mode=self.params.get("grayscale_mode", False),
            )
            
            # Check for cancellation after extraction
            self.check_cancellation()
            
            # Emit completion signals
            self.extraction_finished.emit(extracted_files)
            self.operation_finished.emit(True, f"Successfully extracted {len(extracted_files)} files")
            
            logger.info(f"{self._operation_name}: Extraction completed successfully")
            
        except InterruptedError:
            # Re-raise cancellation to be handled by base class
            raise
        except Exception as e:
            error_msg = f"VRAM extraction failed: {e!s}"
            logger.error(f"{self._operation_name}: {error_msg}", exc_info=e)
            self.emit_error(error_msg, e)
            self.operation_finished.emit(False, error_msg)


class ROMExtractionWorker(ExtractionWorkerBase):
    """
    Worker for ROM extraction operations.
    
    Handles extraction of sprites from ROM files using the ExtractionManager,
    providing progress updates during the extraction process.
    """
    
    def __init__(self, params: ROMExtractionParams, parent: Optional[QObject] = None) -> None:
        manager = get_extraction_manager()
        super().__init__(manager=manager, parent=parent)
        self.params = params
        self._operation_name = "ROMExtractionWorker"
    
    @override
    def connect_manager_signals(self) -> None:
        """Connect extraction manager signals to worker signals."""
        if not isinstance(self.manager, type(get_extraction_manager())):
            logger.error("Invalid manager type for ROM extraction")
            return
            
        # Type cast for better type checking
        extraction_manager: ExtractionManager = self.manager
        
        # Connect standard progress signal
        connection = extraction_manager.extraction_progress.connect(
            lambda msg: self.emit_progress(50, msg)
        )
        self._connections.append(connection)
        
        logger.debug(f"{self._operation_name}: Connected {len(self._connections)} manager signals")
    
    @override
    def perform_operation(self) -> None:
        """Perform ROM extraction via manager."""
        try:
            # Type cast for better type safety
            extraction_manager: ExtractionManager = self.manager
            
            # Check for cancellation before starting
            self.check_cancellation()
            
            logger.info(f"{self._operation_name}: Starting ROM extraction")
            self.emit_progress(10, "Starting ROM extraction...")
            
            # Perform extraction using manager
            extracted_files = extraction_manager.extract_from_rom(
                rom_path=self.params["rom_path"],
                offset=self.params["sprite_offset"],
                output_base=self.params["output_base"],
                sprite_name=self.params["sprite_name"],
                cgram_path=self.params.get("cgram_path"),
            )
            
            # Check for cancellation after extraction
            self.check_cancellation()
            
            # Emit completion signals
            self.extraction_finished.emit(extracted_files)
            self.operation_finished.emit(True, f"Successfully extracted {len(extracted_files)} files")
            
            logger.info(f"{self._operation_name}: ROM extraction completed successfully")
            
        except InterruptedError:
            # Re-raise cancellation to be handled by base class
            raise
        except Exception as e:
            error_msg = f"ROM extraction failed: {e!s}"
            logger.error(f"{self._operation_name}: {error_msg}", exc_info=e)
            self.emit_error(error_msg, e)
            self.operation_finished.emit(False, error_msg)


# Worker-owned manager pattern (Phase 2 architecture)
class WorkerOwnedVRAMExtractionWorker(ExtractionWorkerBase):
    """
    VRAM extraction worker that owns its own ExtractionManager instance.
    
    This pattern provides perfect thread isolation and eliminates cross-thread
    issues by ensuring each worker has its own manager with proper Qt parent.
    Recommended for new code.
    """
    
    def __init__(
        self, 
        params: VRAMExtractionParams, 
        manager_factory: Optional["ManagerFactory"] = None,
        parent: Optional[QObject] = None
    ) -> None:
        # Create manager factory if none provided
        if manager_factory is None:
            # We can't use self as parent yet since super().__init__ hasn't been called
            # So we'll fix the parent after initialization
            from spritepal.core.managers.factory import StandardManagerFactory
            manager_factory = StandardManagerFactory(default_parent_strategy="none")
        
        # Create the manager (parent will be set after super init)
        manager = manager_factory.create_extraction_manager(parent=parent)
        
        # Initialize parent class with the manager
        super().__init__(manager=manager, parent=parent)
        
        # Now fix the manager's parent to be this worker for proper ownership
        manager.setParent(self)
        
        self.params = params
        self._operation_name = "WorkerOwnedVRAMExtractionWorker"
        
        logger.info(f"{self._operation_name}: Created with worker-owned manager")
    
    @override
    def connect_manager_signals(self) -> None:
        """Connect extraction manager signals to worker signals."""
        if not isinstance(self.manager, type(get_extraction_manager())):
            logger.error("Invalid manager type for VRAM extraction")
            return
            
        # Type cast for better type checking
        extraction_manager: ExtractionManager = self.manager
        
        # Connect standard progress signal
        connection1 = extraction_manager.extraction_progress.connect(
            lambda msg: self.emit_progress(50, msg)
        )
        self._connections.append(connection1)
        
        # Connect extraction-specific signals
        connection2 = extraction_manager.palettes_extracted.connect(self.palettes_ready.emit)
        connection3 = extraction_manager.active_palettes_found.connect(self.active_palettes_ready.emit)
        self._connections.extend([connection2, connection3])
        
        # Handle preview generation with PIL to QPixmap conversion
        def on_preview_generated(img: Image.Image, tile_count: int) -> None:
            try:
                pixmap = pil_to_qpixmap(img)
                self.preview_ready.emit(pixmap, tile_count)
                self.preview_image_ready.emit(img)
            except Exception as e:
                logger.error(f"Failed to convert preview image: {e}")
                self.emit_warning(f"Preview generation failed: {e}")
        
        connection4 = extraction_manager.preview_generated.connect(on_preview_generated)
        self._connections.append(connection4)
        
        logger.debug(f"{self._operation_name}: Connected {len(self._connections)} manager signals")
    
    @override
    def perform_operation(self) -> None:
        """Perform VRAM extraction via worker-owned manager."""
        try:
            # Type cast for better type safety
            extraction_manager: ExtractionManager = self.manager
            
            # Check for cancellation before starting
            self.check_cancellation()
            
            logger.info(f"{self._operation_name}: Starting VRAM extraction")
            self.emit_progress(10, "Starting VRAM extraction...")
            
            # Perform extraction using manager
            extracted_files = extraction_manager.extract_from_vram(
                vram_path=self.params["vram_path"],
                output_base=self.params["output_base"],
                cgram_path=self.params.get("cgram_path"),
                oam_path=self.params.get("oam_path"),
                vram_offset=self.params.get("vram_offset"),
                create_grayscale=self.params.get("create_grayscale", True),
                create_metadata=self.params.get("create_metadata", True),
                grayscale_mode=self.params.get("grayscale_mode", False),
            )
            
            # Check for cancellation after extraction
            self.check_cancellation()
            
            # Emit completion signals
            self.extraction_finished.emit(extracted_files)
            self.operation_finished.emit(True, f"Successfully extracted {len(extracted_files)} files")
            
            logger.info(f"{self._operation_name}: Extraction completed successfully")
            
        except InterruptedError:
            # Re-raise cancellation to be handled by base class
            raise
        except Exception as e:
            error_msg = f"VRAM extraction failed: {e!s}"
            logger.error(f"{self._operation_name}: {error_msg}", exc_info=e)
            self.emit_error(error_msg, e)
            self.operation_finished.emit(False, error_msg)


class WorkerOwnedROMExtractionWorker(ExtractionWorkerBase):
    """
    ROM extraction worker that owns its own ExtractionManager instance.
    
    This pattern provides perfect thread isolation and eliminates cross-thread
    issues by ensuring each worker has its own manager with proper Qt parent.
    Recommended for new code.
    """
    
    def __init__(
        self, 
        params: ROMExtractionParams, 
        manager_factory: Optional["ManagerFactory"] = None,
        parent: Optional[QObject] = None
    ) -> None:
        # Create manager factory if none provided
        if manager_factory is None:
            # We can't use self as parent yet since super().__init__ hasn't been called
            # So we'll fix the parent after initialization
            from spritepal.core.managers.factory import StandardManagerFactory
            manager_factory = StandardManagerFactory(default_parent_strategy="none")
        
        # Create the manager (parent will be set after super init)
        manager = manager_factory.create_extraction_manager(parent=parent)
        
        # Initialize parent class with the manager
        super().__init__(manager=manager, parent=parent)
        
        # Now fix the manager's parent to be this worker for proper ownership
        manager.setParent(self)
        
        self.params = params
        self._operation_name = "WorkerOwnedROMExtractionWorker"
        
        logger.info(f"{self._operation_name}: Created with worker-owned manager")
    
    @override
    def connect_manager_signals(self) -> None:
        """Connect extraction manager signals to worker signals."""
        if not isinstance(self.manager, type(get_extraction_manager())):
            logger.error("Invalid manager type for ROM extraction")
            return
            
        # Type cast for better type checking
        extraction_manager: ExtractionManager = self.manager
        
        # Connect standard progress signal
        connection = extraction_manager.extraction_progress.connect(
            lambda msg: self.emit_progress(50, msg)
        )
        self._connections.append(connection)
        
        logger.debug(f"{self._operation_name}: Connected {len(self._connections)} manager signals")
    
    @override
    def perform_operation(self) -> None:
        """Perform ROM extraction via worker-owned manager."""
        try:
            # Type cast for better type safety
            extraction_manager: ExtractionManager = self.manager
            
            # Check for cancellation before starting
            self.check_cancellation()
            
            logger.info(f"{self._operation_name}: Starting ROM extraction")
            self.emit_progress(10, "Starting ROM extraction...")
            
            # Perform extraction using manager
            extracted_files = extraction_manager.extract_from_rom(
                rom_path=self.params["rom_path"],
                offset=self.params["sprite_offset"],
                output_base=self.params["output_base"],
                sprite_name=self.params["sprite_name"],
                cgram_path=self.params.get("cgram_path"),
            )
            
            # Check for cancellation after extraction
            self.check_cancellation()
            
            # Emit completion signals
            self.extraction_finished.emit(extracted_files)
            self.operation_finished.emit(True, f"Successfully extracted {len(extracted_files)} files")
            
            logger.info(f"{self._operation_name}: ROM extraction completed successfully")
            
        except InterruptedError:
            # Re-raise cancellation to be handled by base class
            raise
        except Exception as e:
            error_msg = f"ROM extraction failed: {e!s}"
            logger.error(f"{self._operation_name}: {error_msg}", exc_info=e)
            self.emit_error(error_msg, e)
            self.operation_finished.emit(False, error_msg)