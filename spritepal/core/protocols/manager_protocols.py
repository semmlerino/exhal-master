"""
Protocol definitions for managers to break circular dependencies.
These protocols define the interfaces that managers must implement.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from PySide6.QtCore import SignalInstance
    from PySide6.QtWidgets import QStatusBar


class ExtractionManagerProtocol(Protocol):
    """Protocol for extraction manager."""

    def extract_from_rom(
        self,
        rom_path: Path,
        offset: int,
        size: int | None = None
    ) -> list[Any]:
        """
        Extract sprites from ROM at given offset.

        Args:
            rom_path: Path to ROM file
            offset: Starting offset in ROM
            size: Optional size to extract

        Returns:
            List of extracted sprite data
        """
        ...

    def get_rom_header(self, rom_path: Path) -> dict[str, Any]:
        """
        Get ROM header information.

        Args:
            rom_path: Path to ROM file

        Returns:
            Dictionary with header information
        """
        ...

    def read_rom_header(self, rom_path: str) -> dict[str, Any]:
        """
        Read ROM header from file path.

        Args:
            rom_path: Path to ROM file as string

        Returns:
            Dictionary with header information
        """
        ...

    def get_known_sprite_locations(self, rom_path: str) -> dict[str, Any]:
        """
        Get known sprite locations for ROM.

        Args:
            rom_path: Path to ROM file as string

        Returns:
            Dictionary with sprite locations
        """
        ...

    def validate_rom(self, rom_path: Path) -> bool:
        """
        Validate if file is a valid ROM.

        Args:
            rom_path: Path to ROM file

        Returns:
            True if valid ROM
        """
        ...

    def validate_extraction_params(self, params: dict[str, Any]) -> None:
        """
        Validate extraction parameters.

        Args:
            params: Dictionary of extraction parameters

        Raises:
            ValueError: If parameters are invalid
        """
        ...

class InjectionManagerProtocol(Protocol):
    """Protocol for injection manager."""

    def inject_to_rom(
        self,
        rom_path: Path,
        sprites: list[Any],
        offset: int | None = None
    ) -> bool:
        """
        Inject sprites into ROM.

        Args:
            rom_path: Path to ROM file
            sprites: List of sprites to inject
            offset: Optional target offset

        Returns:
            True if successful
        """
        ...

    def validate_injection(
        self,
        rom_path: Path,
        sprites: list[Any]
    ) -> bool:
        """
        Validate if injection is feasible.

        Args:
            rom_path: Path to ROM file
            sprites: Sprites to inject

        Returns:
            True if injection is valid
        """
        ...

    def get_free_space(self, rom_path: Path) -> list[tuple[int, int]]:
        """
        Find free space regions in ROM.

        Args:
            rom_path: Path to ROM file

        Returns:
            List of (offset, size) tuples for free regions
        """
        ...

    def get_smart_vram_suggestion(
        self,
        sprite_path: str,
        metadata_path: str
    ) -> str:
        """
        Get smart VRAM file suggestion for injection.

        Args:
            sprite_path: Path to sprite file
            metadata_path: Path to metadata file

        Returns:
            Suggested VRAM file path
        """
        ...

    def start_injection(self, params: dict[str, Any]) -> bool:
        """
        Start injection process with given parameters.

        Args:
            params: Dictionary of injection parameters

        Returns:
            True if injection started successfully
        """
        ...

class NavigationManagerProtocol(Protocol):
    """Protocol for navigation manager."""

    def navigate_to_offset(self, offset: int) -> None:
        """
        Navigate to specific ROM offset.

        Args:
            offset: Target offset
        """
        ...

    def get_current_offset(self) -> int:
        """
        Get current navigation offset.

        Returns:
            Current offset
        """
        ...

    def get_navigation_history(self) -> list[int]:
        """
        Get navigation history.

        Returns:
            List of previously visited offsets
        """
        ...

    def navigate_back(self) -> int | None:
        """
        Navigate to previous offset.

        Returns:
            Previous offset or None if at start
        """
        ...

    def navigate_forward(self) -> int | None:
        """
        Navigate to next offset in history.

        Returns:
            Next offset or None if at end
        """
        ...

class SessionManagerProtocol(Protocol):
    """Protocol for session manager."""

    def save_session(self, path: Path | None = None) -> bool:
        """
        Save current session state.

        Args:
            path: Optional path to save to

        Returns:
            True if successful
        """
        ...

    def load_session(self, path: Path) -> bool:
        """
        Load session state from file.

        Args:
            path: Path to session file

        Returns:
            True if successful
        """
        ...

    def get_session_data(self) -> dict[str, Any]:
        """
        Get current session data.

        Returns:
            Dictionary with session state
        """
        ...

    def clear_session(self) -> None:
        """Clear current session data."""
        ...

    def get(self, category: str, key: str, default: Any = None) -> Any:
        """
        Get a setting value.

        Args:
            category: Setting category
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value or default
        """
        ...

    def set(self, category: str, key: str, value: Any) -> None:
        """
        Set a setting value.

        Args:
            category: Setting category
            key: Setting key
            value: Value to set
        """
        ...

class ContextManagerProtocol(Protocol):
    """Protocol for context manager."""

    def get_context(self, key: str) -> Any | None:
        """
        Get context value by key.

        Args:
            key: Context key

        Returns:
            Context value or None
        """
        ...

    def set_context(self, key: str, value: Any) -> None:
        """
        Set context value.

        Args:
            key: Context key
            value: Context value
        """
        ...

    def clear_context(self) -> None:
        """Clear all context data."""
        ...

    def get_all_context(self) -> dict[str, Any]:
        """
        Get all context data.

        Returns:
            Dictionary with all context
        """
        ...

class RegistryManagerProtocol(Protocol):
    """Protocol for registry manager."""

    def register(self, key: str, value: Any) -> None:
        """
        Register a value.

        Args:
            key: Registry key
            value: Value to register
        """
        ...

    def unregister(self, key: str) -> None:
        """
        Unregister a value.

        Args:
            key: Registry key
        """
        ...

    def get(self, key: str) -> Any | None:
        """
        Get registered value.

        Args:
            key: Registry key

        Returns:
            Registered value or None
        """
        ...

    def get_all(self) -> dict[str, Any]:
        """
        Get all registered values.

        Returns:
            Dictionary with all registrations
        """
        ...

class CacheManagerProtocol(Protocol):
    """Protocol for cache manager."""

    def get(self, key: str) -> Any | None:
        """
        Get cached value.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        ...

    def put(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional time-to-live in seconds
        """
        ...

    def invalidate(self, key: str) -> None:
        """
        Invalidate cache entry.

        Args:
            key: Cache key
        """
        ...

    def clear(self) -> None:
        """Clear all cache entries."""
        ...

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        ...


class MainWindowProtocol(Protocol):
    """Protocol for main window interface required by controllers."""

    # Signals
    extract_requested: SignalInstance
    open_in_editor_requested: SignalInstance
    arrange_rows_requested: SignalInstance
    arrange_grid_requested: SignalInstance
    inject_requested: SignalInstance

    # UI Components
    extraction_panel: Any
    sprite_preview: Any
    palette_preview: Any
    preview_coordinator: Any
    status_bar: QStatusBar
    status_bar_manager: Any
    rom_extraction_panel: Any

    def get_extraction_params(self) -> dict[str, Any]:
        """
        Get extraction parameters from UI.

        Returns:
            Dictionary with extraction parameters
        """
        ...

    def get_output_path(self) -> str:
        """
        Get output path for extraction.

        Returns:
            Output path string
        """
        ...

    def extraction_complete(self, extracted_files: list[str]) -> None:
        """
        Handle extraction completion.

        Args:
            extracted_files: List of extracted file paths
        """
        ...

    def extraction_failed(self, error_message: str) -> None:
        """
        Handle extraction failure.

        Args:
            error_message: Error message to display
        """
        ...

    def show_cache_operation_badge(self, badge_text: str) -> None:
        """
        Show cache operation badge.

        Args:
            badge_text: Text to display in badge
        """
        ...

    def hide_cache_operation_badge(self) -> None:
        """Hide cache operation badge."""
        ...
