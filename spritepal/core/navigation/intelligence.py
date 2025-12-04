"""
Intelligence layer for pattern recognition and predictive navigation.

Provides ML-inspired algorithms for learning sprite storage patterns,
predicting locations, and analyzing ROM structure.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Any

from utils.logging_config import get_logger

from .data_structures import (
    NavigationHint,
    NavigationStrategy,
    RegionType,
    SpriteLocation,
)

if TYPE_CHECKING:
    from .region_map import SpriteRegionMap

logger = get_logger(__name__)

class PatternAnalyzer:
    """
    Analyzes sprite storage patterns in ROM files.

    Detects recurring patterns in sprite locations, sizes, and organization
    to improve navigation predictions.
    """

    def __init__(self) -> None:
        self.patterns: dict[str, Any] = {}
        self._analysis_cache: dict[str, Any] = {}

    def analyze_spacing_patterns(self, region_map: SpriteRegionMap) -> dict[str, Any]:
        """
        Analyze spacing patterns between sprites.

        Args:
            region_map: Sprite location data

        Returns:
            Dictionary with spacing pattern analysis
        """
        sprites = list(region_map)
        if len(sprites) < 2:
            return {"spacing_patterns": [], "confidence": 0.0}

        # Calculate distances between consecutive sprites
        distances = []
        for i in range(len(sprites) - 1):
            distance = sprites[i + 1].offset - sprites[i].end_offset
            if distance >= 0:  # Only positive gaps
                distances.append(distance)

        if not distances:
            return {"spacing_patterns": [], "confidence": 0.0}

        # Find common spacing patterns
        distance_counter = Counter(distances)
        common_distances = distance_counter.most_common(10)

        # Calculate statistics
        mean_distance = statistics.mean(distances)
        median_distance = statistics.median(distances)
        stdev_distance = statistics.stdev(distances) if len(distances) > 1 else 0

        # Detect alignment patterns (powers of 2, common alignments)
        alignment_patterns = self._detect_alignment_patterns([s.offset for s in sprites])

        pattern_data = {
            "common_distances": common_distances,
            "mean_distance": mean_distance,
            "median_distance": median_distance,
            "stdev_distance": stdev_distance,
            "alignment_patterns": alignment_patterns,
            "total_gaps": len(distances),
            "confidence": self._calculate_spacing_confidence(distances)
        }

        self.patterns["spacing"] = pattern_data
        return pattern_data

    def analyze_size_patterns(self, region_map: SpriteRegionMap) -> dict[str, Any]:
        """
        Analyze sprite size patterns and distributions.

        Args:
            region_map: Sprite location data

        Returns:
            Dictionary with size pattern analysis
        """
        sprites = list(region_map)
        if not sprites:
            return {"size_patterns": [], "confidence": 0.0}

        # Analyze compressed sizes
        compressed_sizes = [s.compressed_size for s in sprites]
        decompressed_sizes = [s.decompressed_size for s in sprites]
        tile_counts = [s.tile_count for s in sprites]

        # Find common sizes
        size_counter = Counter(compressed_sizes)
        common_sizes = size_counter.most_common(10)

        # Calculate compression ratios
        compression_ratios = [s.density_ratio for s in sprites]

        # Size categories (small, medium, large sprites)
        size_categories = self._categorize_sizes(compressed_sizes)

        pattern_data = {
            "common_compressed_sizes": common_sizes,
            "mean_compressed_size": statistics.mean(compressed_sizes),
            "mean_decompressed_size": statistics.mean(decompressed_sizes),
            "mean_tile_count": statistics.mean(tile_counts),
            "compression_ratio_stats": {
                "mean": statistics.mean(compression_ratios),
                "median": statistics.median(compression_ratios),
                "stdev": statistics.stdev(compression_ratios) if len(compression_ratios) > 1 else 0
            },
            "size_categories": size_categories,
            "confidence": self._calculate_size_confidence(compressed_sizes)
        }

        self.patterns["sizes"] = pattern_data
        return pattern_data

    def analyze_region_patterns(self, region_map: SpriteRegionMap) -> dict[str, Any]:
        """
        Analyze ROM region organization patterns.

        Args:
            region_map: Sprite location data

        Returns:
            Dictionary with region pattern analysis
        """
        sprites = list(region_map)
        if not sprites:
            return {"region_patterns": {}, "confidence": 0.0}

        # Group sprites by ROM regions (64KB chunks)
        region_size = 0x10000  # 64KB regions
        region_groups = defaultdict(list)

        for sprite in sprites:
            region_id = sprite.offset // region_size
            region_groups[region_id].append(sprite)

        # Analyze each region
        region_analysis = {}
        for region_id, region_sprites in region_groups.items():
            if len(region_sprites) < 2:
                continue

            region_start = region_id * region_size
            region_end = region_start + region_size

            # Calculate region density
            total_sprite_size = sum(s.compressed_size for s in region_sprites)
            density = total_sprite_size / region_size

            # Analyze sprite types in region
            region_types = Counter(s.region_type for s in region_sprites)

            region_analysis[region_id] = {
                "start_offset": region_start,
                "end_offset": region_end,
                "sprite_count": len(region_sprites),
                "density": density,
                "region_types": dict(region_types),
                "avg_sprite_size": statistics.mean([s.compressed_size for s in region_sprites])
            }

        # Find high-density regions
        high_density_regions = [
            region_id for region_id, data in region_analysis.items()
            if data["density"] > 0.1  # More than 10% filled
        ]

        pattern_data = {
            "region_analysis": region_analysis,
            "high_density_regions": high_density_regions,
            "total_regions_with_sprites": len(region_groups),
            "confidence": self._calculate_region_confidence(region_analysis)
        }

        self.patterns["regions"] = pattern_data
        return pattern_data

    def get_comprehensive_analysis(self, region_map: SpriteRegionMap) -> dict[str, Any]:
        """
        Perform comprehensive pattern analysis.

        Args:
            region_map: Sprite location data

        Returns:
            Complete pattern analysis results
        """
        return {
            "spacing": self.analyze_spacing_patterns(region_map),
            "sizes": self.analyze_size_patterns(region_map),
            "regions": self.analyze_region_patterns(region_map),
            "overall_confidence": self._calculate_overall_confidence()
        }

    def _detect_alignment_patterns(self, offsets: list[int]) -> dict[str, Any]:
        """Detect common alignment patterns in sprite offsets."""
        alignments = {}

        # Check for common alignments (powers of 2)
        for alignment in [0x10, 0x20, 0x40, 0x80, 0x100, 0x200, 0x400, 0x800, 0x1000]:
            aligned_count = sum(1 for offset in offsets if offset % alignment == 0)
            if aligned_count > len(offsets) * 0.3:  # More than 30% aligned
                alignments[f"0x{alignment:X}"] = {
                    "alignment": alignment,
                    "aligned_count": aligned_count,
                    "percentage": (aligned_count / len(offsets)) * 100
                }

        return alignments

    def _categorize_sizes(self, sizes: list[int]) -> dict[str, Any]:
        """Categorize sprite sizes into small, medium, large."""
        if not sizes:
            return {}

        # Define thresholds based on data distribution
        q25 = statistics.quantiles(sizes, n=4)[0] if len(sizes) > 3 else min(sizes)
        q75 = statistics.quantiles(sizes, n=4)[2] if len(sizes) > 3 else max(sizes)

        small_sprites = [s for s in sizes if s <= q25]
        medium_sprites = [s for s in sizes if q25 < s <= q75]
        large_sprites = [s for s in sizes if s > q75]

        return {
            "small": {"count": len(small_sprites), "threshold": q25},
            "medium": {"count": len(medium_sprites), "range": [q25, q75]},
            "large": {"count": len(large_sprites), "threshold": q75}
        }

    def _calculate_spacing_confidence(self, distances: list[int]) -> float:
        """Calculate confidence in spacing pattern analysis."""
        if len(distances) < 3:
            return 0.0

        # Higher confidence for more consistent spacing
        stdev = statistics.stdev(distances)
        mean = statistics.mean(distances)

        if mean == 0:
            return 0.0

        coefficient_of_variation = stdev / mean
        confidence = max(0.0, 1.0 - coefficient_of_variation)

        return min(confidence, 1.0)

    def _calculate_size_confidence(self, sizes: list[int]) -> float:
        """Calculate confidence in size pattern analysis."""
        if len(sizes) < 3:
            return 0.0

        # Higher confidence for distinct size clusters
        size_counter = Counter(sizes)
        most_common_count = size_counter.most_common(1)[0][1]
        confidence = most_common_count / len(sizes)

        return min(confidence, 1.0)

    def _calculate_region_confidence(self, region_analysis: dict[str, Any]) -> float:
        """Calculate confidence in region pattern analysis."""
        if not region_analysis:
            return 0.0

        # Higher confidence for consistent region organization
        densities = [data["density"] for data in region_analysis.values()]
        if len(densities) < 2:
            return 0.5

        mean_density = statistics.mean(densities)
        stdev_density = statistics.stdev(densities)

        if mean_density == 0:
            return 0.0

        consistency = max(0.0, 1.0 - (stdev_density / mean_density))
        return min(consistency, 1.0)

    def _calculate_overall_confidence(self) -> float:
        """Calculate overall pattern analysis confidence."""
        confidences = []

        for pattern_type in ["spacing", "sizes", "regions"]:
            if pattern_type in self.patterns:
                confidences.append(self.patterns[pattern_type].get("confidence", 0.0))

        if not confidences:
            return 0.0

        return statistics.mean(confidences)

class OffsetPredictor:
    """
    ML-inspired predictor for next sprite locations.

    Uses pattern analysis to predict likely sprite locations based on
    learned patterns and current context.
    """

    def __init__(self) -> None:
        self.model_weights: dict[str, float] = {
            "spacing_pattern": 0.3,
            "size_pattern": 0.2,
            "region_pattern": 0.25,
            "alignment_pattern": 0.15,
            "similarity_pattern": 0.1
        }
        self._prediction_cache: dict[str, list[NavigationHint]] = {}

    def predict_next_locations(
        self,
        current_offset: int,
        region_map: SpriteRegionMap,
        pattern_analysis: dict[str, Any],
        max_predictions: int = 10
    ) -> list[NavigationHint]:
        """
        Predict next sprite locations based on patterns.

        Args:
            current_offset: Current position in ROM
            region_map: Known sprite locations
            pattern_analysis: Results from PatternAnalyzer
            max_predictions: Maximum number of predictions

        Returns:
            List of navigation hints with predictions
        """
        predictions = []

        # Spacing-based predictions
        spacing_predictions = self._predict_by_spacing(
            current_offset, pattern_analysis.get("spacing", {})
        )
        predictions.extend(spacing_predictions)

        # Region-based predictions
        region_predictions = self._predict_by_regions(
            current_offset, pattern_analysis.get("regions", {}), region_map
        )
        predictions.extend(region_predictions)

        # Alignment-based predictions
        alignment_predictions = self._predict_by_alignment(
            current_offset, pattern_analysis.get("spacing", {}).get("alignment_patterns", {})
        )
        predictions.extend(alignment_predictions)

        # Size-based predictions (gaps that could fit common sprite sizes)
        size_predictions = self._predict_by_size_gaps(
            current_offset, region_map, pattern_analysis.get("sizes", {})
        )
        predictions.extend(size_predictions)

        # Remove duplicates and sort by confidence
        unique_predictions = self._deduplicate_predictions(predictions)
        sorted_predictions = sorted(unique_predictions, key=lambda p: p.confidence, reverse=True)

        return sorted_predictions[:max_predictions]

    def _predict_by_spacing(self, current_offset: int, spacing_data: dict[str, Any]) -> list[NavigationHint]:
        """Predict locations based on spacing patterns."""
        if not spacing_data or "common_distances" not in spacing_data:
            return []

        predictions = []
        common_distances = spacing_data["common_distances"]
        base_confidence = spacing_data.get("confidence", 0.5)

        for distance, frequency in common_distances[:5]:  # Top 5 most common distances
            predicted_offset = current_offset + distance

            # Calculate confidence based on frequency and pattern strength
            frequency_weight = frequency / sum(freq for _, freq in common_distances)
            confidence = base_confidence * frequency_weight * self.model_weights["spacing_pattern"]

            hint = NavigationHint(
                target_offset=predicted_offset,
                confidence=confidence,
                reasoning=f"Spacing pattern: {distance} bytes (frequency: {frequency})",
                strategy_used=NavigationStrategy.PREDICTIVE,
                expected_region_type=RegionType.UNKNOWN,
                estimated_size=spacing_data.get("mean_compressed_size"),
                pattern_strength=frequency_weight
            )

            predictions.append(hint)

        return predictions

    def _predict_by_regions(
        self,
        current_offset: int,
        region_data: dict[str, Any],
        region_map: SpriteRegionMap
    ) -> list[NavigationHint]:
        """Predict locations based on region patterns."""
        if not region_data or "high_density_regions" not in region_data:
            return []

        predictions = []
        region_analysis = region_data.get("region_analysis", {})
        high_density_regions = region_data["high_density_regions"]
        base_confidence = region_data.get("confidence", 0.5)

        region_size = 0x10000  # 64KB regions
        current_region = current_offset // region_size

        # Predict in nearby high-density regions
        for region_id in high_density_regions:
            if abs(region_id - current_region) > 3:  # Skip distant regions
                continue

            region_info = region_analysis.get(region_id, {})
            if not region_info:
                continue

            # Find gaps in this region
            region_sprites = region_map.get_sprites_in_range(
                region_info["start_offset"],
                region_info["end_offset"]
            )

            gaps = self._find_gaps_in_sprites(region_sprites)

            for gap_start, gap_end in gaps:
                if gap_end - gap_start < 100:  # Skip small gaps
                    continue

                # Predict in middle of gap
                predicted_offset = gap_start + (gap_end - gap_start) // 2

                distance_factor = max(0.1, 1.0 - abs(region_id - current_region) * 0.2)
                density_factor = region_info.get("density", 0.1)
                confidence = base_confidence * distance_factor * density_factor * self.model_weights["region_pattern"]

                hint = NavigationHint(
                    target_offset=predicted_offset,
                    confidence=confidence,
                    reasoning=f"High-density region {region_id} gap (density: {density_factor:.3f})",
                    strategy_used=NavigationStrategy.PREDICTIVE,
                    expected_region_type=RegionType.HIGH_DENSITY,
                    estimated_size=region_info.get("avg_sprite_size")
                )

                predictions.append(hint)

        return predictions

    def _predict_by_alignment(self, current_offset: int, alignment_patterns: dict[str, Any]) -> list[NavigationHint]:
        """Predict locations based on alignment patterns."""
        if not alignment_patterns:
            return []

        predictions = []

        for alignment_name, alignment_data in alignment_patterns.items():
            alignment = alignment_data["alignment"]
            percentage = alignment_data["percentage"]

            # Find next aligned offset
            next_aligned = ((current_offset // alignment) + 1) * alignment

            # Calculate confidence based on alignment strength
            confidence = (percentage / 100.0) * self.model_weights["alignment_pattern"]

            hint = NavigationHint(
                target_offset=next_aligned,
                confidence=confidence,
                reasoning=f"Alignment pattern: {alignment_name} ({percentage:.1f}% aligned)",
                strategy_used=NavigationStrategy.PREDICTIVE,
                expected_region_type=RegionType.UNKNOWN,
                pattern_strength=percentage / 100.0
            )

            predictions.append(hint)

        return predictions

    def _predict_by_size_gaps(
        self,
        current_offset: int,
        region_map: SpriteRegionMap,
        size_data: dict[str, Any]
    ) -> list[NavigationHint]:
        """Predict locations in gaps that could fit common sprite sizes."""
        if not size_data or "common_compressed_sizes" not in size_data:
            return []

        predictions = []
        common_sizes = size_data["common_compressed_sizes"]

        # Find gaps near current offset
        search_range = 0x10000  # Search within 64KB
        nearby_sprites = region_map.get_sprites_in_range(
            max(0, current_offset - search_range),
            current_offset + search_range
        )

        gaps = self._find_gaps_in_sprites(nearby_sprites)

        for gap_start, gap_end in gaps:
            gap_size = gap_end - gap_start

            # Check if gap could fit common sprite sizes
            for size, frequency in common_sizes[:3]:  # Top 3 common sizes
                if gap_size >= size * 1.2:  # Gap is large enough with margin
                    predicted_offset = gap_start

                    # Calculate confidence based on size frequency and gap fit
                    total_frequency = sum(freq for _, freq in common_sizes)
                    size_weight = frequency / total_frequency
                    fit_weight = min(1.0, gap_size / (size * 2))  # Better fit for larger gaps

                    confidence = size_weight * fit_weight * self.model_weights["size_pattern"]

                    hint = NavigationHint(
                        target_offset=predicted_offset,
                        confidence=confidence,
                        reasoning=f"Gap fits common size {size} bytes (freq: {frequency})",
                        strategy_used=NavigationStrategy.PREDICTIVE,
                        expected_region_type=RegionType.UNKNOWN,
                        estimated_size=size
                    )

                    predictions.append(hint)
                    break  # Only one prediction per gap

        return predictions

    def _find_gaps_in_sprites(self, sprites: list[SpriteLocation]) -> list[tuple[int, int]]:
        """Find gaps between sprites."""
        if len(sprites) < 2:
            return []

        gaps = []
        for i in range(len(sprites) - 1):
            gap_start = sprites[i].end_offset
            gap_end = sprites[i + 1].offset

            if gap_end > gap_start:
                gaps.append((gap_start, gap_end))

        return gaps

    def _deduplicate_predictions(self, predictions: list[NavigationHint]) -> list[NavigationHint]:
        """Remove duplicate predictions, keeping highest confidence."""
        offset_map = {}

        for prediction in predictions:
            offset = prediction.target_offset
            if offset not in offset_map or prediction.confidence > offset_map[offset].confidence:
                offset_map[offset] = prediction

        return list(offset_map.values())

class SimilarityEngine:
    """
    Content-based similarity analysis for sprites.

    Provides fast similarity comparison using fingerprints and
    structural analysis.
    """

    def __init__(self) -> None:
        self.similarity_threshold = 0.7
        self._fingerprint_cache: dict[int, bytes] = {}

    def calculate_similarity(self, sprite1: SpriteLocation, sprite2: SpriteLocation) -> float:
        """
        Calculate similarity between two sprites.

        Args:
            sprite1: First sprite for comparison
            sprite2: Second sprite for comparison

        Returns:
            Similarity score (0.0 = different, 1.0 = identical)
        """
        # Quick structural similarity checks
        size_similarity = self._calculate_size_similarity(sprite1, sprite2)

        # Fingerprint similarity (if available)
        fingerprint_similarity = self._calculate_fingerprint_similarity(sprite1, sprite2)

        # Metadata similarity
        metadata_similarity = self._calculate_metadata_similarity(sprite1, sprite2)

        # Weighted combination
        weights = {"size": 0.3, "fingerprint": 0.5, "metadata": 0.2}

        total_similarity = (
            size_similarity * weights["size"] +
            fingerprint_similarity * weights["fingerprint"] +
            metadata_similarity * weights["metadata"]
        )

        return min(total_similarity, 1.0)

    def find_similar_sprites(
        self,
        target_sprite: SpriteLocation,
        region_map: SpriteRegionMap,
        min_similarity: float = 0.6
    ) -> list[tuple[SpriteLocation, float]]:
        """
        Find sprites similar to target sprite.

        Args:
            target_sprite: Sprite to find similarities for
            region_map: Known sprite locations
            min_similarity: Minimum similarity threshold

        Returns:
            List of (sprite, similarity_score) tuples
        """
        similarities = []

        for sprite in region_map:
            if sprite.offset == target_sprite.offset:
                continue

            similarity = self.calculate_similarity(target_sprite, sprite)
            if similarity >= min_similarity:
                similarities.append((sprite, similarity))

        # Sort by similarity score
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities

    def _calculate_size_similarity(self, sprite1: SpriteLocation, sprite2: SpriteLocation) -> float:
        """Calculate similarity based on size characteristics."""
        # Tile count similarity
        tile_diff = abs(sprite1.tile_count - sprite2.tile_count)
        max_tiles = max(sprite1.tile_count, sprite2.tile_count)
        tile_similarity = 1.0 - (tile_diff / max_tiles) if max_tiles > 0 else 0.0

        # Compression ratio similarity
        ratio_diff = abs(sprite1.density_ratio - sprite2.density_ratio)
        ratio_similarity = max(0.0, 1.0 - ratio_diff)

        return (tile_similarity + ratio_similarity) / 2.0

    def _calculate_fingerprint_similarity(self, sprite1: SpriteLocation, sprite2: SpriteLocation) -> float:
        """Calculate similarity based on content fingerprints."""
        fp1 = sprite1.similarity_fingerprint
        fp2 = sprite2.similarity_fingerprint

        if not fp1 or not fp2 or len(fp1) != len(fp2):
            return 0.5  # Unknown similarity

        # Hamming distance for fingerprint comparison
        differences = sum(b1 != b2 for b1, b2 in zip(fp1, fp2, strict=False))
        return 1.0 - (differences / len(fp1))

    def _calculate_metadata_similarity(self, sprite1: SpriteLocation, sprite2: SpriteLocation) -> float:
        """Calculate similarity based on metadata and context."""
        # Region type similarity
        region_similarity = 1.0 if sprite1.region_type == sprite2.region_type else 0.3

        # Visual complexity similarity
        complexity_diff = abs(sprite1.visual_complexity - sprite2.visual_complexity)
        complexity_similarity = max(0.0, 1.0 - complexity_diff)

        # Discovery strategy similarity (sprites found by same method might be similar)
        strategy_similarity = 1.0 if sprite1.discovery_strategy == sprite2.discovery_strategy else 0.5

        return (region_similarity + complexity_similarity + strategy_similarity) / 3.0

class RegionClassifier:
    """
    Classifies ROM regions by sprite likelihood and content type.

    Uses heuristics and learned patterns to categorize different
    areas of the ROM file.
    """

    def __init__(self) -> None:
        self.classification_rules: dict[str, Any] = {}
        self._classification_cache: dict[str, RegionType] = {}

    def classify_region(
        self,
        start_offset: int,
        end_offset: int,
        region_map: SpriteRegionMap
    ) -> RegionType:
        """
        Classify a ROM region based on its characteristics.

        Args:
            start_offset: Start of region
            end_offset: End of region
            region_map: Known sprite locations

        Returns:
            Classified region type
        """
        region_key = f"{start_offset:08X}_{end_offset:08X}"

        if region_key in self._classification_cache:
            return self._classification_cache[region_key]

        # Get sprites in region
        sprites_in_region = region_map.get_sprites_in_range(start_offset, end_offset)

        if not sprites_in_region:
            classification = RegionType.UNKNOWN
        else:
            classification = self._classify_by_characteristics(
                start_offset, end_offset, sprites_in_region
            )

        self._classification_cache[region_key] = classification
        return classification

    def _classify_by_characteristics(
        self,
        start_offset: int,
        end_offset: int,
        sprites: list[SpriteLocation]
    ) -> RegionType:
        """Classify region based on sprite characteristics."""
        if not sprites:
            return RegionType.UNKNOWN

        region_size = end_offset - start_offset

        # Calculate sprite density
        total_sprite_size = sum(s.compressed_size for s in sprites)
        density = total_sprite_size / region_size

        # Analyze sprite characteristics
        statistics.mean([s.confidence for s in sprites])
        avg_tile_count = statistics.mean([s.tile_count for s in sprites])
        avg_compression = statistics.mean([s.density_ratio for s in sprites])

        # Use helper method to determine classification
        return self._determine_region_type(density, avg_compression, avg_tile_count)

    def _determine_region_type(self, density: float, avg_compression: float, avg_tile_count: float) -> RegionType:
        """Determine region type based on metrics."""
        # Classification logic ordered by priority
        if density > 0.3:  # High density region
            return RegionType.HIGH_DENSITY
        if density < 0.05:  # Very sparse
            return RegionType.SPARSE
        if avg_compression > 5.0:  # Highly compressed
            return RegionType.COMPRESSED
        if avg_compression < 1.5:  # Barely compressed
            return RegionType.UNCOMPRESSED
        if avg_tile_count < 32:  # Small sprites, might be palettes
            return RegionType.PALETTE_DATA
        return RegionType.UNKNOWN

    def get_region_recommendations(self, region_type: RegionType) -> dict[str, Any]:
        """
        Get navigation recommendations for a region type.

        Args:
            region_type: Type of region

        Returns:
            Dictionary with navigation recommendations
        """
        recommendations = {
            RegionType.HIGH_DENSITY: {
                "scan_step": 0x10,  # Small steps
                "confidence_threshold": 0.7,
                "priority": 0.9
            },
            RegionType.SPARSE: {
                "scan_step": 0x100,  # Larger steps
                "confidence_threshold": 0.5,
                "priority": 0.3
            },
            RegionType.COMPRESSED: {
                "scan_step": 0x20,
                "confidence_threshold": 0.6,
                "priority": 0.8
            },
            RegionType.PALETTE_DATA: {
                "scan_step": 0x20,
                "confidence_threshold": 0.4,
                "priority": 0.5
            }
        }

        return recommendations.get(region_type, {
            "scan_step": 0x40,
            "confidence_threshold": 0.6,
            "priority": 0.5
        })
