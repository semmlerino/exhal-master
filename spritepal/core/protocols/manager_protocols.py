"""
Manager protocol definitions for dependency injection.

These protocols define the interfaces that controllers, workers, and UI components
depend on, enabling loose coupling and better testability through dependency injection.
"""

from typing import TYPE_CHECKING, Any, Optional, Protocol, runtime_checkable

from PIL import Image
from PySide6.QtCore import Signal

if TYPE_CHECKING:
    pass


@runtime_checkable
class BaseManagerProtocol(Protocol):
    """Base protocol for all managers with common signals and methods."""

    # Common signals
    error_occurred: Signal  # Error message
    warning_occurred: Signal  # Warning message
    operation_started: Signal  # Operation name
    operation_finished: Signal  # Operation name
    progress_updated: Signal  # Operation name, current, total

    def cleanup(self) -> None:
        """Cleanup manager resources."""
        ...


@runtime_checkable
class ExtractionManagerProtocol(BaseManagerProtocol, Protocol):
    """Protocol for extraction manager functionality."""

    # Extraction-specific signals
    extraction_progress: Signal  # Progress message
    preview_generated: Signal  # PIL Image, tile count
    palettes_extracted: Signal  # Palette data
    active_palettes_found: Signal  # Active palette indices
    files_created: Signal  # List of created files
    cache_operation_started: Signal  # Operation type, cache type
    cache_hit: Signal  # Cache type, time saved in seconds
    cache_miss: Signal  # Cache type
    cache_saved: Signal  # Cache type, number of items saved

    def extract_from_vram(
        self,
        vram_path: str,
        output_base: str,
        cgram_path: str | None = None,
        oam_path: str | None = None,
        vram_offset: int | None = None,
        sprite_size: Optional[tuple[int, int | None]] = None,
        create_grayscale: bool = True,
        create_metadata: bool = True,
        grayscale_mode: bool = False,
    ) -> list[str]:
        """Extract sprites from VRAM dump."""
        ...

    def extract_from_rom(
        self,
        rom_path: str,
        offset: int,
        output_base: str,
        sprite_name: str,
        cgram_path: str | None = None,
    ) -> list[str]:
        """Extract sprites from ROM file."""
        ...

    def get_sprite_preview(
        self,
        rom_path: str,
        offset: int,
        sprite_name: str | None = None
    ) -> tuple[bytes, int, int]:
        """Get preview of sprite at offset."""
        ...

    def validate_extraction_params(self, params: dict[str, Any]) -> bool:
        """
        Validate extraction parameters.

        Args:
            params: Parameters to validate

        Returns:
            True if validation passes

        Raises:
            ValidationError: If validation fails
        """
        ...

    def generate_preview(self, vram_path: str, offset: int) -> tuple[Image.Image, int]:
        """Generate a preview image from VRAM at the specified offset."""
        ...

    def get_rom_extractor(self) -> Any:
        """Get ROM extractor instance."""
        ...

    def get_known_sprite_locations(self, rom_path: str) -> dict[str, Any]:
        """Get known sprite locations for ROM."""
        ...

    def read_rom_header(self, rom_path: str) -> dict[str, Any]:
        """Read ROM header information."""
        ...


@runtime_checkable
class InjectionManagerProtocol(BaseManagerProtocol, Protocol):
    """Protocol for injection manager functionality."""

    # Injection-specific signals
    injection_progress: Signal  # Progress message
    injection_finished: Signal  # Success, message
    compression_info: Signal  # ROM compression statistics
    progress_percent: Signal  # Progress percentage (0-100)
    cache_saved: Signal  # Cache type, number of items saved

    def start_injection(self, params: dict[str, Any]) -> bool:
        """Start injection operation."""
        ...

    def validate_injection_params(self, params: dict[str, Any]) -> None:
        """Validate injection parameters."""
        ...

    def get_smart_vram_suggestion(
        self,
        sprite_path: str,
        metadata_path: str = ""
    ) -> str:
        """Get smart VRAM file suggestion."""
        ...

    def is_injection_active(self) -> bool:
        """Check if injection is currently active."""
        ...

    def load_metadata(self, metadata_path: str) -> dict[str, Any | None]:
        """Load metadata from file."""
        ...

    def load_rom_info(self, rom_path: str) -> dict[str, Any | None]:
        """Load ROM information."""
        ...

    def find_suggested_input_vram(
        self,
        sprite_path: str,
        metadata: Optional[dict[str, Any | None]] = None,
        suggested_vram: str = ""
    ) -> str:
        """Find suggested input VRAM file."""
        ...

    def suggest_output_vram_path(self, input_vram_path: str) -> str:
        """Suggest output VRAM path."""
        ...

    def suggest_output_rom_path(self, input_rom_path: str) -> str:
        """Suggest output ROM path."""
        ...

    def convert_vram_to_rom_offset(self, vram_offset_str: str) -> int | None:
        """Convert VRAM offset to ROM offset."""
        ...

    def save_rom_injection_settings(
        self,
        input_rom: str,
        sprite_location_text: str,
        custom_offset: str,
        fast_compression: bool
    ) -> None:
        """Save ROM injection settings."""
        ...

    def load_rom_injection_defaults(
        self,
        sprite_path: str,
        metadata: Optional[dict[str, Any | None]] = None
    ) -> dict[str, Any]:
        """Load ROM injection defaults."""
        ...

    def restore_saved_sprite_location(
        self,
        extraction_vram_offset: str | None,
        sprite_locations: dict[str, int]
    ) -> dict[str, Any]:
        """Restore saved sprite location."""
        ...

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        ...

    def clear_rom_cache(self, older_than_days: int | None = None) -> int:
        """Clear ROM cache."""
        ...

    def get_scan_progress(
        self,
        rom_path: str,
        scan_params: dict[str, Any]
    ) -> dict[str, Any | None]:
        """Get scan progress."""
        ...

    def save_scan_progress(
        self,
        rom_path: str,
        scan_params: dict[str, Any],
        found_sprites: list[dict[str, Any]],
        current_offset: int,
        total_size: int
    ) -> None:
        """Save scan progress."""
        ...

    def clear_scan_progress(
        self,
        rom_path: str | None = None,
        scan_params: Optional[dict[str, Any | None]] = None
    ) -> int:
        """Clear scan progress."""
        ...


@runtime_checkable
class SessionManagerProtocol(BaseManagerProtocol, Protocol):
    """Protocol for session manager functionality."""

    # Session-specific signals
    session_changed: Signal  # Emitted when session state changes
    files_updated: Signal  # Emitted when file paths change
    settings_saved: Signal  # Emitted when settings are saved
    session_restored: Signal  # Emitted when session is restored

    def save_session(self) -> None:
        """Save current session to file."""
        ...

    def restore_session(self) -> dict[str, Any]:
        """Restore session from file."""
        ...

    def get(self, category: str, key: str, default: Any = None) -> Any:
        """Get session value."""
        ...

    def set(self, category: str, key: str, value: Any) -> None:
        """Set session value."""
        ...

    def get_session_data(self) -> dict[str, Any]:
        """Get all session data."""
        ...

    def update_session_data(self, data: dict[str, Any]) -> None:
        """Update session data."""
        ...

    def update_file_paths(
        self,
        vram: str | None = None,
        cgram: str | None = None,
        oam: str | None = None,
        output_dir: str | None = None,
        rom: str | None = None,
    ) -> None:
        """Update file paths in session."""
        ...

    def update_window_state(self, geometry: dict[str, int]) -> None:
        """Update window state."""
        ...

    def get_window_geometry(self) -> dict[str, int]:
        """Get saved window geometry."""
        ...

    def get_recent_files(self, file_type: str) -> list[str]:
        """Get recent files of type."""
        ...

    def clear_session(self) -> None:
        """Clear current session data."""
        ...

    def clear_recent_files(self, file_type: str | None = None) -> None:
        """Clear recent files."""
        ...

    def export_settings(self, file_path: str) -> None:
        """Export settings to file."""
        ...

    def import_settings(self, file_path: str) -> None:
        """Import settings from file."""
        ...


@runtime_checkable
class MainWindowProtocol(Protocol):
    """Protocol for main window functionality needed by controller."""

    # Signals the controller connects to (typed as Any for protocol compatibility)
    extract_requested: Any  # Signal() - no parameters
    open_in_editor_requested: Any  # Signal(str) - string parameter
    arrange_rows_requested: Any  # Signal(str) - string parameter
    arrange_grid_requested: Any  # Signal(str) - string parameter
    inject_requested: Any  # Signal() - no parameters

    # UI components accessed by controller
    status_bar: Any  # QStatusBar
    sprite_preview: Any  # SpritePreviewWidget
    preview_coordinator: Any  # PreviewCoordinator
    palette_preview: Any  # PalettePreviewWidget
    extraction_panel: Any  # ExtractionPanel
    status_bar_manager: Any  # StatusBarManager
    rom_extraction_panel: Any  # ROMExtractionPanel

    def get_extraction_params(self) -> dict[str, Any]:
        """Get extraction parameters from UI."""
        ...

    def extraction_failed(self, error_message: str) -> None:
        """Handle extraction failure."""
        ...

    def extraction_complete(self, extracted_files: list[str]) -> None:
        """Handle extraction completion."""
        ...

    def get_output_path(self) -> str:
        """Get output path for extraction."""
        ...

    def show_cache_operation_badge(self, badge_text: str) -> None:
        """Show cache operation badge."""
        ...

    def hide_cache_operation_badge(self) -> None:
        """Hide cache operation badge."""
        ...

    def update_cache_status(self) -> None:
        """Update cache status display."""
        ...
