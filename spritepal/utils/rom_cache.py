"""ROM scan results caching system for SpritePal (Fixed version)
Caches expensive ROM scanning operations to improve performance with proper error handling.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

try:
    from utils.logging_config import get_logger
except ImportError:
    # Fallback logger
    import logging
    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

# Delayed import to avoid circular dependency
def get_settings_manager():
    """Get settings manager with delayed import to avoid circular dependency"""
    try:
        from utils.settings_manager import get_settings_manager as _gsm
        return _gsm()
    except ImportError:
        logger.warning("Could not import settings manager")
        return None

logger = get_logger(__name__)


class ROMCache:
    """Manages caching of ROM scan results for performance optimization."""

    CACHE_VERSION = "1.0"
    CACHE_DIR_NAME = ".spritepal_rom_cache"

    def __init__(self, cache_dir: str | None = None) -> None:
        """Initialize ROM cache with robust error handling.

        Args:
            cache_dir: Optional custom cache directory. If None, uses settings or default

        """
        # Get settings manager (might be None if managers not initialized yet)
        try:
            self.settings_manager = get_settings_manager()
        except (ImportError, AttributeError, RuntimeError) as e:
            logger.warning(f"Could not get settings manager during ROM cache initialization: {e}")
            self.settings_manager = None

        # Check if caching is enabled in settings
        if self.settings_manager:
            self._cache_enabled = self.settings_manager.get_cache_enabled()
            if not self._cache_enabled:
                logger.info("ROM caching is disabled in settings")
                self.cache_dir = Path.home() / self.CACHE_DIR_NAME  # Still set for compatibility
                return
        else:
            self._cache_enabled = True  # Default to enabled if no settings

        # Determine cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        elif self.settings_manager:
            # Check for custom cache location in settings
            custom_location = self.settings_manager.get_cache_location()
            if custom_location:
                self.cache_dir = Path(custom_location)
            else:
                self.cache_dir = Path.home() / self.CACHE_DIR_NAME
        else:
            self.cache_dir = Path.home() / self.CACHE_DIR_NAME

        # Create cache directory if it doesn't exist, with error handling
        if self._cache_enabled:
            self._cache_enabled = self._setup_cache_directory()

    @property
    def cache_enabled(self) -> bool:
        """Get whether caching is enabled."""
        return self._cache_enabled

    def _setup_cache_directory(self) -> bool:
        """Set up cache directory with fallbacks."""

        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"ROM cache directory: {self.cache_dir}")
        except (OSError, PermissionError) as e:
            logger.warning(f"Failed to create cache directory {self.cache_dir}: {e}")
            # Fallback to temp directory
            fallback_dir = Path(tempfile.gettempdir()) / self.CACHE_DIR_NAME
            try:
                fallback_dir.mkdir(parents=True, exist_ok=True)
                self.cache_dir = fallback_dir
                logger.info(f"Using fallback cache directory: {self.cache_dir}")
            except (OSError, PermissionError) as e:
                logger.exception(f"Failed to create fallback cache directory: {e}")
                return False
            else:
                return True
        else:
            return True

    def _get_rom_hash(self, rom_path: str) -> str:
        """Generate SHA-256 hash of ROM file for cache key with proper error handling.

        Args:
            rom_path: Path to ROM file

        Returns:
            Hex digest of ROM file hash, or path-based hash for non-existent files

        """
        try:
            if os.path.exists(rom_path):
                sha256_hash = hashlib.sha256()
                with open(rom_path, "rb") as f:
                    # Read in chunks to handle large files efficiently
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha256_hash.update(chunk)
                return sha256_hash.hexdigest()
            # For non-existent files (like test scenarios), use path-based hash
            path_data = f"nonexistent_{os.path.abspath(rom_path)}"
            return hashlib.sha256(path_data.encode()).hexdigest()
        except (OSError, IOError, PermissionError) as e:
            # Ultimate fallback: just use the path itself
            logger.debug(f"Could not read ROM file for hashing, using path-based hash: {e}")
            return hashlib.sha256(str(rom_path).encode()).hexdigest()

    def _get_cache_file_path(self, rom_hash: str, cache_type: str) -> Path:
        """Get cache file path for a ROM hash and cache type."""
        filename = f"{rom_hash}_{cache_type}.json"
        return self.cache_dir / filename

    def _is_cache_valid(self, cache_file: Path, rom_path: str) -> bool:
        """Check if cache file is valid and not stale with robust error handling."""
        if not cache_file.exists():
            return False

        try:
            # Get expiration days from settings
            if self.settings_manager:
                expiration_days = self.settings_manager.get_cache_expiration_days()
            else:
                expiration_days = 30  # Default fallback

            max_age = expiration_days * 24 * 3600  # Convert days to seconds

            # For non-existent ROM files (test scenarios), only check cache age
            if not os.path.exists(rom_path):
                # Check cache age
                cache_age = time.time() - cache_file.stat().st_mtime
                return cache_age <= max_age

            # For real ROM files, check modification time too
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age > max_age:
                return False

            # Check if ROM file has been modified since cache creation
            rom_mtime = os.path.getmtime(rom_path)
            cache_mtime = cache_file.stat().st_mtime

        except (OSError, IOError) as e:
            logger.debug(f"Error checking cache validity for {cache_file}: {e}")
            return False
        else:
            return rom_mtime <= cache_mtime

    def _save_cache_data(self, cache_file: Path, cache_data: dict[str, Any]) -> bool:
        """Safely save cache data with error handling and unique temp files."""
        if not self._cache_enabled:
            return False

        try:
            # Ensure cache directory exists before saving (thread-safe)
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Create unique temp file name to prevent collisions
            temp_suffix = f".tmp.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex[:8]}"
            temp_file = cache_file.with_suffix(temp_suffix)

            # Write to temp file then move to avoid corruption
            with open(temp_file, "w") as f:
                json.dump(cache_data, f, indent=2)
            temp_file.replace(cache_file)
        except Exception as e:
            # Clean up temp file if it exists
            try:
                if "temp_file" in locals() and temp_file.exists():
                    temp_file.unlink(missing_ok=True)
            except (OSError, FileNotFoundError):
                pass  # Ignore cleanup errors
            logger.warning(f"Failed to save cache file {cache_file}: {e}")
            return False
        else:
            return True

    def _load_cache_data(self, cache_file: Path, max_retries: int = 3) -> dict[str, Any] | None:
        """Safely load cache data with error handling and retry logic."""
        for attempt in range(max_retries):
            try:
                with open(cache_file) as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                if attempt == max_retries - 1:
                    logger.warning(f"Failed to load cache file {cache_file} after {max_retries} attempts: {e}")
                    return None
                # Exponential backoff for retry
                time.sleep(0.01 * (2 ** attempt))
            except Exception as e:
                # For other errors, don't retry
                logger.warning(f"Failed to load cache file {cache_file}: {e}")
                return None
        return None

    def save_partial_scan_results(self, rom_path: str, scan_params: dict[str, int],
                                 found_sprites: list[dict[str, Any]],
                                 current_offset: int, completed: bool = False) -> bool:
        """Save partial scan results for incremental progress."""
        if not self._cache_enabled:
            return False

        progress_data = {
            "found_sprites": found_sprites,
            "current_offset": current_offset,
            "last_updated": time.time(),
            "completed": completed,
            "total_found": len(found_sprites),
            "scan_range": {
                "start": scan_params.get("start_offset", 0),
                "end": scan_params.get("end_offset", 0),
                "step": scan_params.get("alignment", scan_params.get("step", 0x100)),  # Support both alignment and step
            },
        }

        try:
            rom_hash = self._get_rom_hash(rom_path)
            scan_id = self._get_scan_id(scan_params)
            cache_file = self._get_cache_file_path(rom_hash, f"scan_progress_{scan_id}")

            cache_data = {
                "version": self.CACHE_VERSION,
                "rom_path": os.path.abspath(rom_path),
                "rom_hash": rom_hash,
                "scan_params": scan_params,
                "cached_at": time.time(),
                "scan_progress": progress_data,
            }

            return self._save_cache_data(cache_file, cache_data)

        except Exception as e:
            logger.warning(f"Failed to save scan progress: {e}")
            return False

    def get_partial_scan_results(self, rom_path: str, scan_params: dict[str, int]) -> dict[str, Any] | None:
        """Get partial scan results for resuming."""
        if not self._cache_enabled:
            return None

        try:
            rom_hash = self._get_rom_hash(rom_path)
            scan_id = self._get_scan_id(scan_params)
            cache_file = self._get_cache_file_path(rom_hash, f"scan_progress_{scan_id}")

            if not self._is_cache_valid(cache_file, rom_path):
                return None

            cache_data = self._load_cache_data(cache_file)
            if not cache_data:
                return None

            # Validate cache format
            if (cache_data.get("version") != self.CACHE_VERSION or
                "scan_progress" not in cache_data):
                return None

            return cache_data["scan_progress"]

        except Exception as e:
            logger.warning(f"Failed to load scan progress: {e}")
            return None

    def _get_scan_id(self, scan_params: dict[str, int]) -> str:
        """Generate unique scan ID from parameters."""
        # Create consistent hash from scan parameters
        param_str = json.dumps(scan_params, sort_keys=True)
        scan_id = hashlib.sha256(param_str.encode()).hexdigest()[:16]
        logger.debug(f"Scan ID for params {scan_params}: {scan_id}")
        return scan_id

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics with error handling."""
        try:
            if not self._cache_enabled or not self.cache_dir.exists():
                return {
                    "cache_dir": str(self.cache_dir),
                    "cache_enabled": False,
                    "total_files": 0,
                    "total_size_bytes": 0,
                    "scan_progress_caches": 0,
                    "cache_dir_exists": False,
                }

            cache_files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files if f.exists())

            sprite_location_files = [f for f in cache_files if "_sprite_locations.json" in f.name]
            rom_info_files = [f for f in cache_files if "_rom_info.json" in f.name]
            scan_progress_files = [f for f in cache_files if "_scan_progress_" in f.name]

            return {
                "cache_dir": str(self.cache_dir),
                "cache_enabled": self._cache_enabled,
                "total_files": len(cache_files),
                "total_size_bytes": total_size,
                "sprite_location_caches": len(sprite_location_files),
                "rom_info_caches": len(rom_info_files),
                "scan_progress_caches": len(scan_progress_files),
                "cache_dir_exists": self.cache_dir.exists(),
            }

        except Exception as e:
            return {"error": str(e), "cache_enabled": False}

    def clear_cache(self, older_than_days: int | None = None) -> int:
        """Clear cache files with error handling."""
        if not self._cache_enabled:
            return 0

        removed_count = 0
        try:
            cutoff_time = None
            if older_than_days is not None:
                cutoff_time = time.time() - (older_than_days * 24 * 3600)

            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    if cutoff_time is None or cache_file.stat().st_mtime < cutoff_time:
                        cache_file.unlink()
                        removed_count += 1
                except (OSError, PermissionError):
                    pass  # Continue with other files

        except Exception as e:
            logger.warning(f"Failed to clear cache: {e}")

        return removed_count

    def get_sprite_locations(self, rom_path: str) -> dict[str, Any] | None:
        """Get cached sprite locations for ROM.

        Args:
            rom_path: Path to ROM file

        Returns:
            Dictionary of sprite locations or None if not cached

        """
        if not self._cache_enabled:
            return None

        try:
            rom_hash = self._get_rom_hash(rom_path)
            cache_file = self._get_cache_file_path(rom_hash, "sprite_locations")

            if not self._is_cache_valid(cache_file, rom_path):
                return None

            cache_data = self._load_cache_data(cache_file)
            if not cache_data:
                return None

            # Validate cache format
            if (cache_data.get("version") != self.CACHE_VERSION or
                "sprite_locations" not in cache_data):
                return None

            # Restore SpritePointer objects from cached dictionaries
            sprite_locations = cache_data["sprite_locations"]
            restored_locations = {}

            for name, location_data in sprite_locations.items():
                if isinstance(location_data, dict) and "offset" in location_data:
                    # Import SpritePointer only when needed to avoid circular imports
                    try:
                        from core.rom_injector import SpritePointer
                        # Restore SpritePointer object from cached data
                        restored_locations[name] = SpritePointer(
                            offset=location_data["offset"],
                            bank=location_data.get("bank", 0),
                            address=location_data.get("address", 0),
                            compressed_size=location_data.get("compressed_size"),
                            offset_variants=location_data.get("offset_variants"),
                        )
                    except ImportError:
                        # Fallback: return dict if SpritePointer can't be imported
                        restored_locations[name] = location_data
                else:
                    # Keep as-is for non-SpritePointer data
                    restored_locations[name] = location_data

        except Exception as e:
            logger.warning(f"Failed to load sprite locations from cache: {e}")
            return None
        else:
            return restored_locations

    def save_sprite_locations(self, rom_path: str, sprite_locations: dict[str, Any],
                            rom_header: dict[str, Any] | None = None) -> bool:
        """Save sprite locations to cache.

        Args:
            rom_path: Path to ROM file
            sprite_locations: Dictionary of sprite locations to cache
            rom_header: Optional ROM header information

        Returns:
            True if saved successfully, False otherwise

        """
        if not self._cache_enabled:
            return False

        try:
            rom_hash = self._get_rom_hash(rom_path)
            cache_file = self._get_cache_file_path(rom_hash, "sprite_locations")

            cache_data = {
                "version": self.CACHE_VERSION,
                "rom_path": os.path.abspath(rom_path),
                "rom_hash": rom_hash,
                "cached_at": time.time(),
                "sprite_locations": sprite_locations,
            }

            # Include ROM header if provided
            if rom_header:
                cache_data["rom_header"] = rom_header

            # Convert SpritePointer objects to serializable format if needed
            serializable_locations = {}
            for name, location in sprite_locations.items():
                if hasattr(location, "offset"):
                    # This is a SpritePointer object - capture all fields
                    serializable_locations[name] = {
                        "offset": location.offset,
                        "bank": getattr(location, "bank", 0),
                        "address": getattr(location, "address", 0),
                        "compressed_size": getattr(location, "compressed_size", None),
                        "offset_variants": getattr(location, "offset_variants", None),
                    }
                else:
                    # Already serializable
                    serializable_locations[name] = location

            cache_data["sprite_locations"] = serializable_locations

            return self._save_cache_data(cache_file, cache_data)

        except Exception as e:
            logger.warning(f"Failed to save sprite locations to cache: {e}")
            return False

    def get_rom_info(self, rom_path: str) -> dict[str, Any] | None:
        """Get cached ROM information (header, etc.).

        Args:
            rom_path: Path to ROM file

        Returns:
            Dictionary of ROM info or None if not cached

        """
        if not self._cache_enabled:
            return None

        try:
            rom_hash = self._get_rom_hash(rom_path)
            cache_file = self._get_cache_file_path(rom_hash, "rom_info")

            if not self._is_cache_valid(cache_file, rom_path):
                return None

            cache_data = self._load_cache_data(cache_file)
            if not cache_data:
                return None

            # Validate cache format
            if (cache_data.get("version") != self.CACHE_VERSION or
                "rom_info" not in cache_data):
                return None

            return cache_data["rom_info"]

        except Exception as e:
            logger.warning(f"Failed to load ROM info from cache: {e}")
            return None

    def save_rom_info(self, rom_path: str, rom_info: dict[str, Any]) -> bool:
        """Save ROM information to cache.

        Args:
            rom_path: Path to ROM file
            rom_info: Dictionary of ROM information to cache

        Returns:
            True if saved successfully, False otherwise

        """
        if not self._cache_enabled:
            return False

        try:
            rom_hash = self._get_rom_hash(rom_path)
            cache_file = self._get_cache_file_path(rom_hash, "rom_info")

            cache_data = {
                "version": self.CACHE_VERSION,
                "rom_path": os.path.abspath(rom_path),
                "rom_hash": rom_hash,
                "cached_at": time.time(),
                "rom_info": rom_info,
            }

            return self._save_cache_data(cache_file, cache_data)

        except Exception as e:
            logger.warning(f"Failed to save ROM info to cache: {e}")
            return False

    def clear_scan_progress_cache(self, rom_path: str | None = None,
                                 scan_params: dict[str, int] | None = None) -> int:
        """Clear scan progress caches."""
        if not self._cache_enabled:
            return 0

        removed_count = 0
        try:
            if rom_path and scan_params:
                # Clear specific scan cache
                rom_hash = self._get_rom_hash(rom_path)
                scan_id = self._get_scan_id(scan_params)
                cache_file = self._get_cache_file_path(rom_hash, f"scan_progress_{scan_id}")
                if cache_file.exists():
                    cache_file.unlink()
                    removed_count = 1
            else:
                # Clear all scan progress caches
                for cache_file in self.cache_dir.glob("*_scan_progress_*.json"):
                    try:
                        cache_file.unlink()
                        removed_count += 1
                    except (OSError, PermissionError):
                        pass
        except (OSError, PermissionError):
            pass

        return removed_count

    def refresh_settings(self) -> None:
        """Refresh cache settings from settings manager."""
        # Try to get settings manager if we don't have one
        if not self.settings_manager:
            try:
                self.settings_manager = get_settings_manager()
            except (ImportError, AttributeError, RuntimeError) as e:
                logger.warning(f"Could not get settings manager for cache refresh: {e}")
                return

        if not self.settings_manager:
            return

        # Update cache enabled state
        old_enabled = self._cache_enabled
        self._cache_enabled = self.settings_manager.get_cache_enabled()

        if old_enabled and not self._cache_enabled:
            logger.info("ROM caching has been disabled")
        elif not old_enabled and self._cache_enabled:
            logger.info("ROM caching has been enabled")

        # Update cache location if enabled
        if self._cache_enabled:
            custom_location = self.settings_manager.get_cache_location()
            if custom_location:
                new_dir = Path(custom_location)
                if new_dir != self.cache_dir:
                    logger.info(f"Cache directory changed from {self.cache_dir} to {new_dir}")
                    self.cache_dir = new_dir
                    self._cache_enabled = self._setup_cache_directory()


# Global cache instance
_rom_cache_instance: ROMCache | None = None
_rom_cache_lock = threading.Lock()

def get_rom_cache() -> ROMCache:
    """Get the global ROM cache instance (thread-safe)."""
    global _rom_cache_instance
    if _rom_cache_instance is None:
        with _rom_cache_lock:
            # Double-check locking pattern
            if _rom_cache_instance is None:
                _rom_cache_instance = ROMCache()
    return _rom_cache_instance
