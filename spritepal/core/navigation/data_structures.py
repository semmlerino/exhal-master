"""
Core data structures for smart sprite navigation system.

Provides foundational types for representing sprite locations, navigation hints,
and spatial relationships in ROM files.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RegionType(Enum):
    """Classification of ROM regions by sprite likelihood."""
    UNKNOWN = "unknown"
    HIGH_DENSITY = "high_density"  # Areas with many sprites
    SPARSE = "sparse"              # Few sprites, large gaps
    PALETTE_DATA = "palette_data"  # Palette information
    COMPRESSED = "compressed"      # Compressed sprite data
    UNCOMPRESSED = "uncompressed"  # Raw tile data
    METADATA = "metadata"          # Sprite headers/indices


class NavigationStrategy(Enum):
    """Available navigation strategies."""
    LINEAR = "linear"              # Traditional linear scan
    PATTERN_BASED = "pattern"      # Based on learned patterns
    SIMILARITY = "similarity"      # Content similarity search
    PREDICTIVE = "predictive"      # ML-inspired prediction
    HYBRID = "hybrid"             # Multiple strategies combined


@dataclass(frozen=True)
class SpriteLocation:
    """Immutable representation of a sprite's location and properties."""

    # Core location data
    offset: int
    compressed_size: int
    decompressed_size: int

    # Quality metrics
    confidence: float
    region_type: RegionType

    # Metadata for learning and navigation
    tile_count: int
    visual_complexity: float
    similarity_fingerprint: bytes
    discovery_strategy: NavigationStrategy

    # Additional context
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: 0.0)

    def __post_init__(self) -> None:
        """Validate data consistency."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0,1], got {self.confidence}")
        if self.compressed_size <= 0 or self.decompressed_size <= 0:
            raise ValueError("Sizes must be positive")
        if self.offset < 0:
            raise ValueError("Offset must be non-negative")

    @property
    def end_offset(self) -> int:
        """Calculate the end offset of this sprite."""
        return self.offset + self.compressed_size

    @property
    def density_ratio(self) -> float:
        """Calculate compression ratio (higher = more compressed)."""
        return self.decompressed_size / self.compressed_size if self.compressed_size > 0 else 1.0

    def overlaps_with(self, other: SpriteLocation) -> bool:
        """Check if this sprite overlaps with another."""
        return not (self.end_offset <= other.offset or other.end_offset <= self.offset)

    def distance_to(self, other: SpriteLocation) -> int:
        """Calculate byte distance to another sprite."""
        if self.overlaps_with(other):
            return 0
        return min(abs(self.offset - other.end_offset), abs(other.offset - self.end_offset))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "offset": f"0x{self.offset:06X}",
            "offset_int": self.offset,
            "compressed_size": self.compressed_size,
            "decompressed_size": self.decompressed_size,
            "confidence": round(self.confidence, 3),
            "region_type": self.region_type.value,
            "tile_count": self.tile_count,
            "visual_complexity": round(self.visual_complexity, 3),
            "discovery_strategy": self.discovery_strategy.value,
            "density_ratio": round(self.density_ratio, 3),
            "metadata": self.metadata
        }


@dataclass
class NavigationHint:
    """Intelligent suggestion for next sprite location."""

    target_offset: int
    confidence: float
    reasoning: str
    strategy_used: NavigationStrategy
    expected_region_type: RegionType

    # Optional preview data
    estimated_size: int | None = None
    similarity_score: float | None = None
    pattern_strength: float | None = None

    # Ranking factors
    priority: float = 0.5  # 0.0 = low, 1.0 = high priority
    distance_penalty: float = 0.0  # Penalty for being far from current location

    def __post_init__(self) -> None:
        """Validate hint data."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0,1], got {self.confidence}")
        if not 0.0 <= self.priority <= 1.0:
            raise ValueError(f"Priority must be in [0,1], got {self.priority}")
        if self.target_offset < 0:
            raise ValueError("Target offset must be non-negative")

    @property
    def score(self) -> float:
        """Calculate overall hint score considering all factors."""
        base_score = self.confidence * self.priority
        return max(0.0, base_score - self.distance_penalty)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "target_offset": f"0x{self.target_offset:06X}",
            "target_offset_int": self.target_offset,
            "confidence": round(self.confidence, 3),
            "score": round(self.score, 3),
            "reasoning": self.reasoning,
            "strategy": self.strategy_used.value,
            "region_type": self.expected_region_type.value,
            "priority": round(self.priority, 3),
            "estimated_size": self.estimated_size,
            "similarity_score": round(self.similarity_score, 3) if self.similarity_score else None,
            "pattern_strength": round(self.pattern_strength, 3) if self.pattern_strength else None
        }


@dataclass
class NavigationContext:
    """Context for navigation operations including user preferences and history."""

    # Current position and preferences
    current_offset: int = 0
    preferred_strategies: list[NavigationStrategy] = field(default_factory=list)

    # User behavior tracking
    recently_visited: list[int] = field(default_factory=list)
    favorite_regions: list[tuple[int, int]] = field(default_factory=list)  # (start, end) tuples
    rejected_hints: set[int] = field(default_factory=set)

    # Search parameters
    max_distance: int = 0x100000  # Maximum distance to search
    min_confidence: float = 0.6
    max_hints: int = 10

    # Learning parameters
    enable_learning: bool = True
    learning_rate: float = 0.1

    def add_visited(self, offset: int) -> None:
        """Add an offset to recently visited list."""
        if offset in self.recently_visited:
            self.recently_visited.remove(offset)
        self.recently_visited.insert(0, offset)

        # Keep only recent visits
        if len(self.recently_visited) > 100:
            self.recently_visited = self.recently_visited[:100]

    def add_favorite_region(self, start: int, end: int) -> None:
        """Add a region to favorites based on user interaction."""
        region = (start, end)
        if region not in self.favorite_regions:
            self.favorite_regions.append(region)

        # Keep only most relevant regions
        if len(self.favorite_regions) > 20:
            self.favorite_regions = self.favorite_regions[:20]

    def reject_hint(self, offset: int) -> None:
        """Mark a hint as rejected by the user."""
        self.rejected_hints.add(offset)

    def is_in_favorite_region(self, offset: int) -> bool:
        """Check if offset is in any favorite region."""
        return any(start <= offset <= end for start, end in self.favorite_regions)

    def get_distance_penalty(self, target_offset: int) -> float:
        """Calculate distance penalty for a target offset."""
        distance = abs(target_offset - self.current_offset)
        if distance > self.max_distance:
            return 1.0  # Maximum penalty

        # Linear penalty based on distance
        return min(0.5, distance / self.max_distance)


def create_similarity_fingerprint(sprite_data: bytes, tile_count: int) -> bytes:
    """
    Create a compact fingerprint for sprite similarity comparison.

    Args:
        sprite_data: Raw sprite tile data
        tile_count: Number of tiles in the sprite

    Returns:
        Compact bytes fingerprint for similarity comparison
    """
    # Use a combination of data hash and structural features
    data_hash = hashlib.md5(sprite_data).digest()[:8]  # First 8 bytes of MD5

    # Add structural information
    size_bytes = tile_count.to_bytes(2, "little")

    # Simple complexity measure (count of unique bytes)
    unique_bytes = len(set(sprite_data[:min(256, len(sprite_data))]))
    complexity_bytes = unique_bytes.to_bytes(1, "little")

    return data_hash + size_bytes + complexity_bytes
