"""
Spatial data structure for efficient sprite location management.

Provides optimized storage and querying of sprite locations with spatial
indexing for fast range queries and nearest-neighbor searches.
"""

from __future__ import annotations

import bisect
import json
import threading
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from utils.logging_config import get_logger

from .data_structures import RegionType, SpriteLocation

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

logger = get_logger(__name__)


class SpriteRegionMap:
    """
    Efficient spatial data structure for sprite locations.

    Maintains sorted collections for fast range queries and provides
    spatial indexing for nearest-neighbor searches and region analysis.
    """

    def __init__(self, rom_size: int = 0) -> None:
        """
        Initialize the region map.

        Args:
            rom_size: Size of the ROM file in bytes
        """
        self.rom_size = rom_size

        # Main storage: sorted by offset for efficient range queries
        self._sprites: list[SpriteLocation] = []

        # Index by offset for O(log n) lookups
        self._offset_index: dict[int, SpriteLocation] = {}

        # Spatial indexing for fast region queries
        self._region_buckets: dict[RegionType, list[SpriteLocation]] = defaultdict(list)

        # Statistics and metadata
        self._statistics = {
            "total_sprites": 0,
            "coverage_ratio": 0.0,
            "density_map": {},
            "region_distribution": {}
        }

        # Thread safety
        self._lock = threading.RLock()

        # Change tracking for incremental updates
        self._version = 0
        self._dirty = False

    def add_sprite(self, sprite: SpriteLocation) -> bool:
        """
        Add a sprite to the region map.

        Args:
            sprite: Sprite location to add

        Returns:
            True if sprite was added, False if it already existed
        """
        with self._lock:
            # Check for existing sprite at same offset
            if sprite.offset in self._offset_index:
                existing = self._offset_index[sprite.offset]
                if existing.confidence >= sprite.confidence:
                    return False  # Keep higher confidence sprite

                # Remove existing sprite
                self.remove_sprite(sprite.offset)

            # Insert in sorted order
            insert_pos = bisect.bisect_left(self._sprites, sprite, key=lambda s: s.offset)
            self._sprites.insert(insert_pos, sprite)

            # Update indices
            self._offset_index[sprite.offset] = sprite
            self._region_buckets[sprite.region_type].append(sprite)

            # Update metadata
            self._version += 1
            self._dirty = True
            self._update_statistics()

            logger.debug(f"Added sprite at 0x{sprite.offset:06X} with confidence {sprite.confidence:.3f}")
            return True

    def remove_sprite(self, offset: int) -> bool:
        """
        Remove a sprite by offset.

        Args:
            offset: Offset of sprite to remove

        Returns:
            True if sprite was removed, False if not found
        """
        with self._lock:
            if offset not in self._offset_index:
                return False

            sprite = self._offset_index[offset]

            # Remove from main list
            self._sprites.remove(sprite)

            # Remove from indices
            del self._offset_index[offset]
            self._region_buckets[sprite.region_type].remove(sprite)

            # Update metadata
            self._version += 1
            self._dirty = True
            self._update_statistics()

            logger.debug(f"Removed sprite at 0x{offset:06X}")
            return True

    def get_sprite(self, offset: int) -> SpriteLocation | None:
        """
        Get sprite at specific offset.

        Args:
            offset: Offset to query

        Returns:
            Sprite at offset or None if not found
        """
        with self._lock:
            return self._offset_index.get(offset)

    def get_sprites_in_range(self, start: int, end: int) -> list[SpriteLocation]:
        """
        Get all sprites within a byte range.

        Args:
            start: Start offset (inclusive)
            end: End offset (exclusive)

        Returns:
            List of sprites in range, sorted by offset
        """
        with self._lock:
            # Use binary search for efficient range query
            start_idx = bisect.bisect_left(self._sprites, start, key=lambda s: s.offset)
            end_idx = bisect.bisect_left(self._sprites, end, key=lambda s: s.offset)

            return self._sprites[start_idx:end_idx]

    def get_sprites_by_region(self, region_type: RegionType) -> list[SpriteLocation]:
        """
        Get all sprites of a specific region type.

        Args:
            region_type: Type of region to query

        Returns:
            List of sprites in region, sorted by offset
        """
        with self._lock:
            sprites = self._region_buckets[region_type].copy()
            return sorted(sprites, key=lambda s: s.offset)

    def find_nearest_sprites(
        self,
        offset: int,
        count: int = 5,
        max_distance: int | None = None
    ) -> list[tuple[SpriteLocation, int]]:
        """
        Find nearest sprites to a given offset.

        Args:
            offset: Target offset
            count: Maximum number of sprites to return
            max_distance: Maximum distance to search (None = no limit)

        Returns:
            List of (sprite, distance) tuples sorted by distance
        """
        with self._lock:
            if not self._sprites:
                return []

            # Find insertion point
            insert_idx = bisect.bisect_left(self._sprites, offset, key=lambda s: s.offset)

            # Collect candidates from both directions
            candidates = []

            # Search backwards
            for i in range(insert_idx - 1, -1, -1):
                sprite = self._sprites[i]
                distance = abs(sprite.offset - offset)

                if max_distance is not None and distance > max_distance:
                    break

                candidates.append((sprite, distance))

                if len(candidates) >= count * 2:  # Get extra for sorting
                    break

            # Search forwards
            for i in range(insert_idx, len(self._sprites)):
                sprite = self._sprites[i]
                distance = abs(sprite.offset - offset)

                if max_distance is not None and distance > max_distance:
                    break

                candidates.append((sprite, distance))

                if len(candidates) >= count * 2:  # Get extra for sorting
                    break

            # Sort by distance and return top results
            candidates.sort(key=lambda x: x[1])
            return candidates[:count]

    def get_gaps(self, min_size: int = 1024) -> list[tuple[int, int]]:
        """
        Find gaps between sprites that could contain undiscovered sprites.

        Args:
            min_size: Minimum gap size to report

        Returns:
            List of (start, end) tuples representing gaps
        """
        with self._lock:
            if len(self._sprites) < 2:
                return []

            gaps = []

            for i in range(len(self._sprites) - 1):
                current_end = self._sprites[i].end_offset
                next_start = self._sprites[i + 1].offset

                gap_size = next_start - current_end
                if gap_size >= min_size:
                    gaps.append((current_end, next_start))

            return gaps

    def get_density_map(self, bucket_size: int = 0x10000) -> dict[int, float]:
        """
        Calculate sprite density across ROM regions.

        Args:
            bucket_size: Size of each density bucket in bytes

        Returns:
            Dictionary mapping bucket offset to density (sprites per bucket)
        """
        with self._lock:
            if self.rom_size == 0:
                return {}

            buckets = defaultdict(int)

            for sprite in self._sprites:
                bucket = (sprite.offset // bucket_size) * bucket_size
                buckets[bucket] += 1

            # Convert to density (sprites per bucket)
            return dict(buckets)

    def get_region_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive statistics about the region map.

        Returns:
            Dictionary with various statistics
        """
        with self._lock:
            if self._dirty:
                self._update_statistics()

            return self._statistics.copy()

    def _update_statistics(self) -> None:
        """Update internal statistics (called with lock held)."""
        self._statistics["total_sprites"] = len(self._sprites)

        # Calculate coverage ratio
        if self.rom_size > 0:
            covered_bytes = sum(sprite.compressed_size for sprite in self._sprites)
            self._statistics["coverage_ratio"] = covered_bytes / self.rom_size

        # Update density map
        self._statistics["density_map"] = self.get_density_map()

        # Region distribution
        region_counts = defaultdict(int)
        for sprite in self._sprites:
            region_counts[sprite.region_type.value] += 1
        self._statistics["region_distribution"] = dict(region_counts)

        self._dirty = False

    def clear(self) -> None:
        """Clear all sprites from the region map."""
        with self._lock:
            self._sprites.clear()
            self._offset_index.clear()
            self._region_buckets.clear()
            self._version += 1
            self._dirty = True
            self._update_statistics()

            logger.info("Cleared region map")

    def get_version(self) -> int:
        """Get current version number (increments on changes)."""
        return self._version

    def __len__(self) -> int:
        """Get number of sprites in the map."""
        return len(self._sprites)

    def __iter__(self) -> Iterator[SpriteLocation]:
        """Iterate over all sprites in offset order."""
        with self._lock:
            # Return a copy to avoid modification during iteration
            return iter(self._sprites.copy())

    def __contains__(self, offset: int) -> bool:
        """Check if a sprite exists at the given offset."""
        return offset in self._offset_index

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize region map to dictionary.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        with self._lock:
            return {
                "version": self._version,
                "rom_size": self.rom_size,
                "sprites": [sprite.to_dict() for sprite in self._sprites],
                "statistics": self.get_region_statistics()
            }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpriteRegionMap:
        """
        Deserialize region map from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Reconstructed region map
        """
        region_map = cls(rom_size=data.get("rom_size", 0))

        # Reconstruct sprites
        for sprite_data in data.get("sprites", []):
            # Convert back from dictionary format
            sprite = SpriteLocation(
                offset=sprite_data["offset_int"],
                compressed_size=sprite_data["compressed_size"],
                decompressed_size=sprite_data["decompressed_size"],
                confidence=sprite_data["confidence"],
                region_type=RegionType(sprite_data["region_type"]),
                tile_count=sprite_data["tile_count"],
                visual_complexity=sprite_data["visual_complexity"],
                similarity_fingerprint=b"",  # Would need to be stored separately
                discovery_strategy=data.get("discovery_strategy", "linear"),
                metadata=sprite_data.get("metadata", {})
            )
            region_map.add_sprite(sprite)

        region_map._version = data.get("version", 0)
        return region_map

    def save_to_file(self, filepath: Path) -> None:
        """
        Save region map to file.

        Args:
            filepath: Path to save the region map
        """
        try:
            data = self.to_dict()
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved region map to {filepath}")

        except Exception as e:
            logger.exception(f"Failed to save region map to {filepath}: {e}")
            raise

    @classmethod
    def load_from_file(cls, filepath: Path) -> SpriteRegionMap:
        """
        Load region map from file.

        Args:
            filepath: Path to load the region map from

        Returns:
            Loaded region map
        """
        try:
            with open(filepath) as f:
                data = json.load(f)

            region_map = cls.from_dict(data)
            logger.info(f"Loaded region map from {filepath}")
            return region_map

        except Exception as e:
            logger.exception(f"Failed to load region map from {filepath}: {e}")
            raise
